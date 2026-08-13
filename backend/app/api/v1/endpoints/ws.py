"""WebSocket live run streaming (T28).

Mounted at ``/ws/simulations/{id}`` (NOT under /api/v1). Auth via
``?token=<access_token>`` because browsers can't set headers on WebSocket.
"""

from __future__ import annotations

import json
import uuid

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from sqlalchemy import select

from app.core.security import decode_token
from app.db.session import async_session_factory
from app.models.simulation import SimulationEvent, SimulationRun, TickLog
from app.models.workspace import Membership
from app.schemas.simulation import SimulationRunResponse
from app.services.simulation_service import STREAM_CHANNEL

router = APIRouter()


async def _authorize(token: str) -> uuid.UUID | None:
    """Return the user id for a valid access token, else None."""
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        return uuid.UUID(sub)
    except (ValueError, TypeError):
        return None


def _run_response(run: SimulationRun) -> dict[str, object]:
    return SimulationRunResponse.model_validate(run).model_dump(mode="json")


@router.websocket("/ws/simulations/{run_id}")
async def simulation_ws(websocket: WebSocket, run_id: str) -> None:
    token = websocket.query_params.get("token", "")
    user_id = await _authorize(token)
    # Accept first, then close with an app-level code: closing before accept()
    # makes Starlette reject the handshake with HTTP 403, so the client would
    # never observe the 4401/4403 close code the API contract promises.
    await websocket.accept()
    if user_id is None:
        await websocket.close(code=4401)
        return

    # Verify the caller is a member of the run's workspace.
    async with async_session_factory() as session:
        run = await session.get(SimulationRun, run_id)
        if run is None:
            await websocket.close(code=4403)
            return
        membership = await session.scalar(
            select(Membership).where(
                Membership.user_id == user_id,
                Membership.workspace_id == uuid.UUID(str(run.workspace_id)),
            )
        )
        if membership is None:
            await websocket.close(code=4403)
            return

        # Snapshot envelope first.
        await websocket.send_text(
            json.dumps({"type": "snapshot", "data": _run_response(run)})
        )

        # Replay the last 50 persisted ticks, oldest first.
        ticks = (
            await session.scalars(
                select(TickLog)
                .where(TickLog.run_id == run_id)
                .order_by(TickLog.month.desc())
                .limit(50)
            )
        ).all()
        for tick_row in reversed(list(ticks)):
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "tick",
                        "data": {"month": tick_row.month, "kpis": tick_row.kpis},
                    }
                )
            )

        # Replay hurdle events so a refresh still shows the War Room decision
        # modal (T26) and ghost spectators see resolved decisions (T43).
        # Pending first, then resolved — the client treats the final pending
        # event as the one awaiting a decision.
        events = (
            await session.scalars(
                select(SimulationEvent)
                .where(SimulationEvent.run_id == run_id)
                .order_by(SimulationEvent.created_at.asc())
            )
        ).all()
        for event_row in events:
            await websocket.send_text(
                json.dumps(
                    {"type": "event", "data": dict(event_row.payload)}
                )
            )

    # Live forward from the run's pub/sub channel.
    redis: Redis | None = None
    try:
        from app.api.deps import get_redis

        redis = get_redis()
    except Exception:  # noqa: BLE001 - no Redis -> replay-only socket
        redis = None

    pubsub = None
    if redis is not None:
        try:
            pubsub = redis.pubsub()
            await pubsub.subscribe(STREAM_CHANNEL.format(run_id=run_id))
        except Exception:  # noqa: BLE001
            pubsub = None

    try:
        if pubsub is not None:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is None:
                    continue
                if message.get("type") == "message":
                    await websocket.send_text(str(message["data"]))
    except WebSocketDisconnect:
        pass
    finally:
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(STREAM_CHANNEL.format(run_id=run_id))
                await pubsub.close()
            except Exception:  # noqa: BLE001
                pass

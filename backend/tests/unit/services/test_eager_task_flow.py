"""Verify the Celery eager-mode task path delivers via the console backend.

Regression test for the `asyncio.run`-inside-a-running-loop failure: under
pytest's `task_always_eager` config the email task must run on the current
event loop instead of raising and leaking a coroutine.
"""

import asyncio
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("FORGE_CHEAP_HASH", "1")

import pytest
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import async_engine, async_session_factory
from app.models.user import User
from app.workers.celery_app import celery_app
from app.workers.email_tasks import send_verification_email_task

celery_app.conf.task_always_eager = True
celery_app.conf.task_eager_propagates = False


@pytest.mark.asyncio
async def test_eager_verification_task_sends_via_console(capsys) -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        user = User(
            email="eager@b.co", name="Eager", pw_hash=hash_password("password123")
        )
        session.add(user)
        await session.commit()
        user_id = str(user.id)

    # Eager mode executes the task body synchronously on this event loop.
    result = send_verification_email_task.delay(user_id)
    # Give the scheduled coroutine a chance to finish.
    await asyncio.sleep(0.05)

    assert result is not None
    captured = capsys.readouterr()
    assert "eager@b.co" in captured.out
    assert "Verify your email" in captured.out

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

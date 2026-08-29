# Day 30 — F-09: Slack Alerts + Outbound Webhooks + CSV Export

## Feature
F-09: Integrations & Distribution

## Goal
Implement Slack incoming webhook dispatcher, HMAC-signed outbound webhooks, and CSV export endpoints for ticks/KPIs/MC distributions.

---

## Step 1 — Slack Notifier

`backend/app/services/integrations/slack_notifier.py`:
```python
from __future__ import annotations
import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_slack_message(webhook_url: str, message: str, blocks: list | None = None):
    """Send a message to a Slack incoming webhook URL."""
    payload = {"text": message}
    if blocks:
        payload["blocks"] = blocks
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(webhook_url, json=payload, timeout=5.0)
            resp.raise_for_status()
            logger.info(f"[slack] Message sent to webhook (status {resp.status_code})")
        except Exception as e:
            logger.warning(f"[slack] Failed to send message: {e}")


async def notify_run_complete(webhook_url: str, run_id: str, survival_rate: float, score: float):
    message = f"✅ *Simulation Complete* — Run `{run_id}`\nSurvival Rate: {survival_rate:.0%} | Resilience Score: {score:.1f}"
    await send_slack_message(webhook_url, message)


async def notify_drift_alert(webhook_url: str, blueprint_id: str, score_delta: float):
    message = f"📉 *Drift Alert* — Blueprint `{blueprint_id}`\nResilience score dropped {abs(score_delta):.1f} points after latest actuals import."
    await send_slack_message(webhook_url, message)
```

---

## Step 2 — Outbound Webhook Service

`backend/app/services/integrations/webhook_service.py`:
```python
from __future__ import annotations
import hmac
import hashlib
import json
import logging
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings

logger = logging.getLogger(__name__)


def _sign_payload(payload: dict, secret: str) -> str:
    """Create HMAC-SHA256 signature for webhook payload."""
    body = json.dumps(payload, sort_keys=True)
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


async def fire_webhook(
    target_url: str,
    event: str,
    payload: dict,
    secret: str,
):
    """Send a signed webhook POST to target_url."""
    signature = _sign_payload(payload, secret)
    headers = {
        "Content-Type": "application/json",
        "X-Forge-Event": event,
        "X-Forge-Signature": f"sha256={signature}",
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(target_url, json=payload, headers=headers, timeout=5.0)
            logger.info(f"[webhook] {event} → {target_url} ({resp.status_code})")
        except Exception as e:
            logger.warning(f"[webhook] Failed to deliver {event}: {e}")


async def dispatch_run_completed(run_id: str, workspace_id: str, payload: dict, db: AsyncSession):
    """Dispatch run.completed webhook to all registered endpoints for this workspace."""
    from app.models.api_key import WebhookRegistration  # model to add
    result = await db.execute(
        select(WebhookRegistration).where(
            WebhookRegistration.workspace_id == workspace_id,
            WebhookRegistration.active == True,
        )
    )
    webhooks = result.scalars().all()
    for wh in webhooks:
        await fire_webhook(wh.target_url, "run.completed", payload, wh.secret)
```

---

## Step 3 — CSV Exporter

`backend/app/services/integrations/csv_exporter.py`:
```python
from __future__ import annotations
import csv
import io
import json


def ticks_to_csv(tick_logs: list[dict]) -> str:
    if not tick_logs:
        return "month\n"
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(tick_logs[0].keys()))
    writer.writeheader()
    writer.writerows(tick_logs)
    return buf.getvalue()


def mc_to_csv(mc_aggregates: dict) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["metric", "value"])
    for key, value in mc_aggregates.items():
        if not isinstance(value, (list, dict)):
            writer.writerow([key, value])
    if "kill_vectors" in mc_aggregates:
        writer.writerow([])
        writer.writerow(["kill_vector_type", "frequency"])
        for kv in mc_aggregates["kill_vectors"]:
            writer.writerow([kv.get("type", ""), kv.get("frequency", "")])
    return buf.getvalue()
```

---

## Step 4 — Export API endpoints

`backend/app/api/v1/endpoints/export.py`:
```python
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, get_current_workspace
from app.services.integrations.csv_exporter import ticks_to_csv, mc_to_csv
from app.services.deep_report.data_pack import _fetch_tick_logs, _fetch_run, _extract_mc_aggregates

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/runs/{run_id}/ticks.csv")
async def export_ticks(run_id: str, db: AsyncSession = Depends(get_db),
                       current_user=Depends(get_current_user)):
    ticks = await _fetch_tick_logs(run_id, db)
    csv_content = ticks_to_csv(ticks)
    return Response(content=csv_content, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=ticks_{run_id}.csv"})


@router.get("/runs/{run_id}/mc.csv")
async def export_mc(run_id: str, db: AsyncSession = Depends(get_db),
                    current_user=Depends(get_current_user)):
    run = await _fetch_run(run_id, db)
    mc = _extract_mc_aggregates(run) or {}
    csv_content = mc_to_csv(mc)
    return Response(content=csv_content, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=mc_{run_id}.csv"})
```

---

## Step 5 — Settings UI

`frontend/src/features/settings/IntegrationsPage.tsx`:
```typescript
// Slack URL input + webhook registration list
// Simple form: label, URL, events (checkboxes: run.completed, report.ready, score.dropped)
// Save → POST /api/v1/integrations/webhooks
// Listed webhooks with Delete button
```

---

## Step 6 — Tests

`backend/tests/unit/integrations/test_csv_exporter.py`:
```python
import pytest
from app.services.integrations.csv_exporter import ticks_to_csv, mc_to_csv

TICKS = [{"month": 1, "revenue": 12000, "cash": 86000}, {"month": 2, "revenue": 15000, "cash": 87000}]
MC = {"survival_rate": 0.68, "median_lifespan": 18, "kill_vectors": [{"type": "cash_out", "frequency": 0.4}]}

def test_ticks_to_csv_has_header():
    csv = ticks_to_csv(TICKS)
    assert "month" in csv
    assert "revenue" in csv
    assert "12000" in csv

def test_ticks_to_csv_row_count():
    csv = ticks_to_csv(TICKS)
    lines = [l for l in csv.strip().split("\n") if l]
    assert len(lines) == 3  # header + 2 rows

def test_mc_to_csv_has_survival_rate():
    csv = mc_to_csv(MC)
    assert "survival_rate" in csv
    assert "0.68" in csv

def test_mc_to_csv_includes_kill_vectors():
    csv = mc_to_csv(MC)
    assert "cash_out" in csv

def test_sign_payload_deterministic():
    from app.services.integrations.webhook_service import _sign_payload
    sig1 = _sign_payload({"event": "run.completed", "run_id": "x"}, "secret123")
    sig2 = _sign_payload({"event": "run.completed", "run_id": "x"}, "secret123")
    assert sig1 == sig2

def test_sign_payload_different_secret():
    from app.services.integrations.webhook_service import _sign_payload
    sig1 = _sign_payload({"event": "test"}, "secret1")
    sig2 = _sign_payload({"event": "test"}, "secret2")
    assert sig1 != sig2
```

---

## Verification Commands
```bash
cd backend && pytest tests/unit/integrations/ -v
cd backend && ruff check app/services/integrations/ app/api/v1/endpoints/export.py
cd frontend && npm run build
```

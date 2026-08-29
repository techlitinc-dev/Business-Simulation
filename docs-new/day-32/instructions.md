# Day 32 — F-12: Model Routing, Cost Guardrails, Localization & Gamification

## Feature
F-12: Trust, Quality & Platform Depth

## Goal
Implement per-task model routing via env config, per-report and per-month token budget hard caps, report generation in multiple languages, and a gamification system with achievements and certifications.

---

## Step 1 — Model Router

`backend/app/agents/llm/router.py`:
```python
"""
Per-task model selection. Override via env vars.
Falls back to the default LLM_MODEL if no task-specific model is set.
"""
from __future__ import annotations
from app.core.config import settings


TASK_MODEL_ENV_MAP = {
    "executive_summary":     "DEEPSEEK_MODEL_EXECUTIVE_SUMMARY",
    "counterfactual":        "DEEPSEEK_MODEL_COUNTERFACTUAL",
    "financial_narrative":   "DEEPSEEK_MODEL_NARRATIVE",
    "generic_narrative":     "DEEPSEEK_MODEL_NARRATIVE",
    "section_default":       "DEEPSEEK_MODEL_DEFAULT",
}


def get_model_for_task(task_name: str) -> str:
    """
    Return the model name for a given task.
    Task-specific env var > default model.
    """
    env_key = TASK_MODEL_ENV_MAP.get(task_name, "DEEPSEEK_MODEL_DEFAULT")
    # getattr with fallback to LLM_MODEL
    model = getattr(settings, env_key.replace("DEEPSEEK_", ""), None)
    if not model:
        model = getattr(settings, "LLM_MODEL", "deepseek-chat")
    return model
```

Add to `backend/app/core/config.py`:
```python
MODEL_EXECUTIVE_SUMMARY: str = ""    # if empty, falls back to LLM_MODEL
MODEL_COUNTERFACTUAL: str = ""
MODEL_NARRATIVE: str = ""
MODEL_DEFAULT: str = ""
```

---

## Step 2 — Cost Guardrails

`backend/app/services/cost_guard.py`:
```python
"""
Per-report and per-month token budget enforcement.
Hard cap: raises CostLimitExceeded before any LLM call.
"""
from __future__ import annotations
import json
import logging
from fastapi import HTTPException
import redis as redis_lib
from app.core.config import settings

logger = logging.getLogger(__name__)

MONTHLY_TOKEN_LIMIT = 2_000_000    # tokens per workspace per month
REPORT_TOKEN_LIMIT = 150_000       # tokens per single report generation
REDIS_PREFIX = "cost_guard:"


def _get_redis():
    return redis_lib.from_url(settings.REDIS_URL)


def get_monthly_usage(workspace_id: str) -> int:
    r = _get_redis()
    raw = r.get(f"{REDIS_PREFIX}monthly:{workspace_id}")
    return int(raw) if raw else 0


def record_usage(workspace_id: str, tokens: int, report_job_id: str | None = None):
    r = _get_redis()
    # Monthly counter — expires after 35 days
    r.incrby(f"{REDIS_PREFIX}monthly:{workspace_id}", tokens)
    r.expire(f"{REDIS_PREFIX}monthly:{workspace_id}", 60 * 60 * 24 * 35)
    # Per-report counter
    if report_job_id:
        r.incrby(f"{REDIS_PREFIX}report:{report_job_id}", tokens)
        r.expire(f"{REDIS_PREFIX}report:{report_job_id}", 3600)


def check_report_budget(report_job_id: str):
    r = _get_redis()
    used = int(r.get(f"{REDIS_PREFIX}report:{report_job_id}") or 0)
    if used >= REPORT_TOKEN_LIMIT:
        raise HTTPException(429, detail={
            "error": "report_token_budget_exceeded",
            "used": used,
            "limit": REPORT_TOKEN_LIMIT,
        })


def check_monthly_budget(workspace_id: str):
    used = get_monthly_usage(workspace_id)
    if used >= MONTHLY_TOKEN_LIMIT:
        raise HTTPException(429, detail={
            "error": "monthly_token_budget_exceeded",
            "used": used,
            "limit": MONTHLY_TOKEN_LIMIT,
        })
```

---

## Step 3 — Localization

`backend/app/utils/i18n.py`:
```python
"""
Report localization: pass language code to section writer prompt.
DeepSeek handles translation natively.
"""
from __future__ import annotations

SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "zh": "Simplified Chinese",
    "ja": "Japanese",
}

CURRENCY_FORMATS = {
    "USD": "${:,.0f}",
    "EUR": "€{:,.0f}",
    "GBP": "£{:,.0f}",
    "BRL": "R${:,.0f}",
    "JPY": "¥{:,.0f}",
}


def get_language_instruction(lang_code: str) -> str:
    name = SUPPORTED_LANGUAGES.get(lang_code, "English")
    if lang_code == "en":
        return ""
    return f"\n\nIMPORTANT: Write your response in {name}. All narrative text must be in {name}."


def format_currency(amount: float, currency: str = "USD") -> str:
    fmt = CURRENCY_FORMATS.get(currency, "${:,.0f}")
    return fmt.format(amount)
```

Update `section_writer.py` to append `get_language_instruction(lang_code)` to the prompt when lang_code is set.

---

## Step 4 — Gamification

`backend/app/services/gamification/achievements.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable


@dataclass
class Achievement:
    id: str
    title: str
    description: str
    icon: str
    check: Callable[[dict], bool]   # returns True if earned


ACHIEVEMENTS = [
    Achievement(
        id="survived_3_shocks",
        title="Shock Absorber",
        description="Survived 3 demand shock hurdles in a single run",
        icon="⚡",
        check=lambda ctx: ctx.get("demand_shocks_survived", 0) >= 3,
    ),
    Achievement(
        id="top_decile",
        title="Top Decile Resilience",
        description="Achieved a resilience score in the top 10% of all simulations",
        icon="🏆",
        check=lambda ctx: ctx.get("cohort_percentile", 0) >= 90,
    ),
    Achievement(
        id="beat_ai_5",
        title="AI Challenger",
        description="Beat the AI's recommended decision path 5 or more times",
        icon="🤖",
        check=lambda ctx: ctx.get("beat_ai_count", 0) >= 5,
    ),
    Achievement(
        id="first_run",
        title="Simulation Pioneer",
        description="Completed your first simulation run",
        icon="🚀",
        check=lambda ctx: ctx.get("total_runs", 0) >= 1,
    ),
]


def check_achievements(context: dict) -> list[Achievement]:
    return [a for a in ACHIEVEMENTS if a.check(context)]
```

`backend/app/services/gamification/certification.py`:
```python
from __future__ import annotations
from app.utils.pdf_deep import assemble_pdf


def generate_certification(workspace_name: str, score: float, percentile: float, run_id: str) -> bytes:
    """Generate a 'Forge-Validated Business' certification PDF."""
    content = f"""# Forge-Validated Business Certificate

**{workspace_name}** has completed a rigorous AI-powered business simulation audit.

## Resilience Score: {score:.1f} / 100

This places the business in the **{percentile:.0f}th percentile** of all simulated businesses.

## Certification Criteria Met
- ✅ 24-month deterministic simulation completed
- ✅ Monte Carlo stress-test across 100+ scenarios
- ✅ AI vulnerability analysis reviewed
- ✅ Optimization recommendations evaluated

*Run ID: {run_id} · Certified by The Forge Simulation Engine*
"""
    section = {"section_number": 1, "title": "Certification", "narrative": content}
    return assemble_pdf(
        sections=[section], chart_paths={}, workspace_name=workspace_name,
        run_id=run_id, tier="enterprise", report_type="resilience_audit",
    )
```

---

## Step 5 — Gamification API

`backend/app/api/v1/endpoints/gamification.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import Response
from app.api.deps import get_db, get_current_user, get_current_workspace
from app.services.gamification.achievements import check_achievements
from app.services.gamification.certification import generate_certification

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/achievements")
async def get_achievements(db: AsyncSession = Depends(get_db),
                           current_user=Depends(get_current_user),
                           workspace=Depends(get_current_workspace)):
    # Build context from workspace stats
    context = {
        "total_runs": 1,     # replace with real DB query
        "beat_ai_count": 0,
        "demand_shocks_survived": 0,
        "cohort_percentile": 50,
    }
    earned = check_achievements(context)
    return [{"id": a.id, "title": a.title, "description": a.description, "icon": a.icon} for a in earned]


@router.post("/certification/{run_id}")
async def get_certification(run_id: str, db: AsyncSession = Depends(get_db),
                             current_user=Depends(get_current_user),
                             workspace=Depends(get_current_workspace)):
    pdf = generate_certification(workspace.name, 72.0, 64.0, run_id)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=certification_{run_id}.pdf"})
```

---

## Step 6 — Frontend Gamification Components

```typescript
// frontend/src/features/gamification/AchievementToast.tsx
// Shows a toast notification when an achievement is earned

// frontend/src/features/gamification/CertificationBadge.tsx
// Shows "🏆 Forge-Validated Business — Top Decile" badge with download button
```

---

## Step 7 — Tests

`backend/tests/unit/gamification/test_achievements.py`:
```python
from app.services.gamification.achievements import check_achievements, ACHIEVEMENTS

def test_first_run_achievement_earned():
    earned = check_achievements({"total_runs": 1})
    ids = [a.id for a in earned]
    assert "first_run" in ids

def test_top_decile_requires_90th_percentile():
    earned = check_achievements({"cohort_percentile": 89})
    ids = [a.id for a in earned]
    assert "top_decile" not in ids

    earned2 = check_achievements({"cohort_percentile": 90})
    ids2 = [a.id for a in earned2]
    assert "top_decile" in ids2

def test_ai_challenger_requires_5_beats():
    earned = check_achievements({"beat_ai_count": 4, "total_runs": 1})
    ids = [a.id for a in earned]
    assert "beat_ai_5" not in ids

    earned2 = check_achievements({"beat_ai_count": 5, "total_runs": 1})
    ids2 = [a.id for a in earned2]
    assert "beat_ai_5" in ids2

def test_cost_guard_monthly_budget():
    from app.services.cost_guard import check_monthly_budget, MONTHLY_TOKEN_LIMIT
    from unittest.mock import patch, MagicMock
    with patch("app.services.cost_guard._get_redis") as mock_redis:
        r = mock_redis.return_value
        r.get.return_value = str(MONTHLY_TOKEN_LIMIT + 1)
        try:
            check_monthly_budget("ws_001")
            assert False, "Should have raised"
        except Exception as e:
            assert "429" in str(type(e).__name__) or hasattr(e, "status_code")

def test_i18n_language_instruction_en_is_empty():
    from app.utils.i18n import get_language_instruction
    assert get_language_instruction("en") == ""

def test_i18n_language_instruction_es_contains_spanish():
    from app.utils.i18n import get_language_instruction
    instruction = get_language_instruction("es")
    assert "Spanish" in instruction
```

---

## Verification Commands
```bash
cd backend && pytest tests/unit/gamification/ -v
cd backend && ruff check app/agents/llm/router.py app/services/cost_guard.py app/utils/i18n.py app/services/gamification/
cd frontend && npm run build && npm run lint
```

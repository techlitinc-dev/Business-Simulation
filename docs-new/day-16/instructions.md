# Day 16 — F-02: Advisory Board Persona Agents

## Feature
F-02: AI Advisory Board & Copilot

## Goal
Implement 4 advisory board persona agents (CFO, CMO, Risk Auditor, Operator) and an orchestrator that runs all 4 in parallel, collects structured reviews, and synthesizes a BoardSummary with agreements and conflicts.

## Prerequisites
- Existing `bridge.py`, `factory.py`, `forge.py` as patterns to follow
- Existing blueprint and run data available

---

## Step 1 — Create persona prompt files

`backend/app/agents/prompts/cfo_persona.md`:
```markdown
You are a skeptical CFO reviewing a business simulation. You focus on:
- Cash burn rate and runway adequacy
- Unit economics (LTV/CAC ratio, payback period)
- Fixed vs variable cost structure
- Funding requirements and capital efficiency

DATA:
{{ data_json }}

Provide a structured JSON review as a PersonaReview.
Be direct, skeptical, and numbers-focused. Flag any financial vulnerability you see.
```

`backend/app/agents/prompts/cmo_persona.md`:
```markdown
You are a growth-obsessed CMO reviewing a business simulation. You focus on:
- Customer acquisition strategy and CAC trends
- Churn rate and retention mechanics
- Revenue growth trajectory and MRR expansion
- Market positioning and demand curve

DATA:
{{ data_json }}

Provide a structured JSON review as a PersonaReview.
Be optimistic about growth opportunities but honest about acquisition challenges.
```

`backend/app/agents/prompts/risk_auditor_persona.md`:
```markdown
You are a risk auditor reviewing a business simulation. You focus on:
- Concentration risks (customer, revenue, market)
- Kill vectors and failure probability
- Worst-case scenario analysis
- Regulatory and compliance exposure

DATA:
{{ data_json }}

Provide a structured JSON review as a PersonaReview.
Be conservative and systematic. List risks by severity.
```

`backend/app/agents/prompts/operator_persona.md`:
```markdown
You are a seasoned operator reviewing a business simulation. You focus on:
- Team capacity and headcount planning
- Operational scalability
- Process efficiency and cost structure
- Execution risk and milestone achievability

DATA:
{{ data_json }}

Provide a structured JSON review as a PersonaReview.
Draw on operational experience. Flag execution risks clearly.
```

---

## Step 2 — Create `backend/app/schemas/advisory.py`

```python
from pydantic import BaseModel, Field
from typing import Literal


class PersonaReview(BaseModel):
    persona: Literal["CFO", "CMO", "RiskAuditor", "Operator"]
    verdict: str = Field(..., description="One-sentence verdict")
    top_concerns: list[str] = Field(..., min_length=1, max_length=5)
    opportunities: list[str] = Field(..., min_length=0, max_length=3)
    questions_for_founder: list[str] = Field(..., min_length=1, max_length=3)
    confidence_level: Literal["LOW", "MEDIUM", "HIGH"]


class BoardSummary(BaseModel):
    consensus_verdict: str
    points_of_agreement: list[str] = Field(..., min_length=1)
    points_of_conflict: list[str]
    top_priority_action: str
    overall_risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
```

---

## Step 3 — Create `backend/app/agents/advisory_board.py`

```python
from __future__ import annotations
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from app.agents.bridge import generate_structured
from app.agents.llm.factory import get_provider
from app.schemas.advisory import PersonaReview, BoardSummary

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"

PERSONA_CONFIG = [
    ("CFO", "cfo_persona.md"),
    ("CMO", "cmo_persona.md"),
    ("RiskAuditor", "risk_auditor_persona.md"),
    ("Operator", "operator_persona.md"),
]


def _load_persona_prompt(template_name: str, data: dict) -> str:
    path = PROMPTS_DIR / template_name
    template = path.read_text(encoding="utf-8")
    return template.replace("{{ data_json }}", json.dumps(data, default=str, indent=2))


async def _get_persona_review(persona: str, template: str, data: dict) -> PersonaReview:
    provider = get_provider()
    prompt = _load_persona_prompt(template, data)
    result = await generate_structured(
        provider=provider,
        system_prompt=prompt,
        user_message=f"Provide your {persona} review of this business simulation.",
        response_schema=PersonaReview,
    )
    # Override persona field to match config (MockProvider may return wrong value)
    result_dict = result.model_dump()
    result_dict["persona"] = persona
    return PersonaReview(**result_dict)


async def _synthesize_board(reviews: list[PersonaReview], data: dict) -> BoardSummary:
    provider = get_provider()
    reviews_json = json.dumps([r.model_dump() for r in reviews], indent=2)
    prompt = f"""You are synthesizing 4 advisory board reviews into a unified BoardSummary.

INDIVIDUAL REVIEWS:
{reviews_json}

BUSINESS DATA SUMMARY:
{json.dumps({k: v for k, v in data.items() if k in ["survival_rate", "resilience_score", "top_vulnerabilities"]}, indent=2)}

Identify: consensus_verdict, points_of_agreement (issues all/most agree on),
points_of_conflict (issues where personas disagree), top_priority_action, overall_risk_level.
"""
    return await generate_structured(
        provider=provider,
        system_prompt=prompt,
        user_message="Synthesize the board reviews.",
        response_schema=BoardSummary,
    )


async def run_advisory_board(
    blueprint_payload: dict[str, Any],
    run_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Run 4 persona reviews in parallel, then synthesize a BoardSummary.
    Returns {"reviews": [...], "summary": {...}}.
    """
    data = {**blueprint_payload, **run_summary}

    reviews = await asyncio.gather(*[
        _get_persona_review(persona, template, data)
        for persona, template in PERSONA_CONFIG
    ])
    reviews = list(reviews)

    summary = await _synthesize_board(reviews, run_summary)

    logger.info(f"[advisory_board] Board review complete: risk_level={summary.overall_risk_level}")
    return {
        "reviews": [r.model_dump() for r in reviews],
        "summary": summary.model_dump(),
    }
```

---

## Step 4 — Tests

`backend/tests/unit/agents/test_advisory_board.py`:

```python
import pytest
import asyncio
import os
from app.agents.advisory_board import run_advisory_board


MOCK_BLUEPRINT = {
    "monthly_churn": 0.05, "price": 99, "cac": 450,
    "starting_capital": 100000, "fixed_monthly_costs": 15000,
}
MOCK_RUN_SUMMARY = {
    "survival_rate": 0.58, "resilience_score": 54.0,
    "median_lifespan": 14, "top_vulnerabilities": ["High CAC", "Low runway"],
}


def test_advisory_board_returns_four_reviews():
    os.environ.setdefault("LLM_PROVIDER", "mock")
    result = asyncio.get_event_loop().run_until_complete(
        run_advisory_board(MOCK_BLUEPRINT, MOCK_RUN_SUMMARY)
    )
    assert len(result["reviews"]) == 4


def test_advisory_board_persona_names_correct():
    os.environ.setdefault("LLM_PROVIDER", "mock")
    result = asyncio.get_event_loop().run_until_complete(
        run_advisory_board(MOCK_BLUEPRINT, MOCK_RUN_SUMMARY)
    )
    personas = {r["persona"] for r in result["reviews"]}
    assert personas == {"CFO", "CMO", "RiskAuditor", "Operator"}


def test_advisory_board_summary_has_required_fields():
    os.environ.setdefault("LLM_PROVIDER", "mock")
    result = asyncio.get_event_loop().run_until_complete(
        run_advisory_board(MOCK_BLUEPRINT, MOCK_RUN_SUMMARY)
    )
    summary = result["summary"]
    assert "consensus_verdict" in summary
    assert "points_of_agreement" in summary
    assert len(summary["points_of_agreement"]) >= 1
    assert summary["overall_risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_advisory_board_result_serializable():
    import json
    os.environ.setdefault("LLM_PROVIDER", "mock")
    result = asyncio.get_event_loop().run_until_complete(
        run_advisory_board(MOCK_BLUEPRINT, MOCK_RUN_SUMMARY)
    )
    json.dumps(result)  # must not raise
```

---

## Verification Commands
```bash
cd backend && pytest tests/unit/agents/test_advisory_board.py -v
cd backend && ruff check app/agents/advisory_board.py app/schemas/advisory.py
```

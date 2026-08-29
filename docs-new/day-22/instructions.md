# Day 22 — F-03: Investment Teaser + Pitch Deck Outline Generator

## Feature
F-03: Investor & Lender Toolkit

## Goal
Implement `investor_tools.py` agent that generates a 1-page investment teaser and a 10–12 slide pitch deck outline, both grounded in simulation data. Export as PDF.

---

## Step 1 — Prompt templates

`backend/app/agents/prompts/investment_teaser.md`:
```markdown
You are writing a 1-page investment teaser for a business based on its simulation results.

SIMULATION DATA:
{{ data_json }}

OUTPUT STRUCTURE (InvestmentTeaser schema):
- problem: 1-2 sentences describing the market problem
- solution: 1-2 sentences describing the product/solution
- simulated_survival: cite the exact survival_rate from data
- key_metrics: 3-4 bullet strings using exact numbers from data (MRR, CAC, LTV/CAC, runway)
- ask: 1 sentence describing the funding ask (derive from starting_capital and burn rate)
- risks: top 2 risks from architectural_weaknesses

RULES:
- Every number must come from the simulation data. Never fabricate.
- Tone: confident but realistic.
```

`backend/app/agents/prompts/pitch_deck_outline.md`:
```markdown
You are creating a 10-12 slide pitch deck outline grounded in business simulation data.

SIMULATION DATA:
{{ data_json }}

OUTPUT STRUCTURE (PitchDeckOutline schema):
- slides: list of 10-12 slides, each: {slide_number, title, talking_points: list[str]}
- Each talking_point must reference a real number or finding from the simulation data.

Standard slide order: Problem, Solution, Market, Product, Business Model, Traction/Simulation,
Financial Projections, Unit Economics, Competition, Team (placeholder), Ask, Use of Funds.
```

---

## Step 2 — Schemas

`backend/app/schemas/investor.py`:
```python
from pydantic import BaseModel, Field


class InvestmentTeaser(BaseModel):
    problem: str
    solution: str
    simulated_survival: str         # e.g. "68% 24-month survival across 100 simulated runs"
    key_metrics: list[str] = Field(..., min_length=3, max_length=5)
    ask: str
    risks: list[str] = Field(..., min_length=1, max_length=3)


class PitchSlide(BaseModel):
    slide_number: int
    title: str
    talking_points: list[str] = Field(..., min_length=1, max_length=5)


class PitchDeckOutline(BaseModel):
    slides: list[PitchSlide] = Field(..., min_length=10, max_length=12)
```

---

## Step 3 — Agent

`backend/app/agents/investor_tools.py`:
```python
from __future__ import annotations
import json
import logging
from pathlib import Path
from app.agents.bridge import generate_structured
from app.agents.llm.factory import get_provider
from app.schemas.investor import InvestmentTeaser, PitchDeckOutline
from app.utils.pdf_deep import assemble_pdf

logger = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(template: str, data: dict) -> str:
    path = PROMPTS_DIR / template
    return path.read_text(encoding="utf-8").replace("{{ data_json }}", json.dumps(data, default=str, indent=2))


async def generate_teaser(data: dict) -> InvestmentTeaser:
    provider = get_provider()
    prompt = _load_prompt("investment_teaser.md", data)
    result = await generate_structured(
        provider=provider,
        system_prompt=prompt,
        user_message="Generate the investment teaser.",
        response_schema=InvestmentTeaser,
    )
    logger.info("[investor_tools] Investment teaser generated")
    return result


async def generate_pitch_outline(data: dict) -> PitchDeckOutline:
    provider = get_provider()
    prompt = _load_prompt("pitch_deck_outline.md", data)
    result = await generate_structured(
        provider=provider,
        system_prompt=prompt,
        user_message="Generate the pitch deck outline.",
        response_schema=PitchDeckOutline,
    )
    logger.info(f"[investor_tools] Pitch deck outline generated: {len(result.slides)} slides")
    return result


def teaser_to_pdf(teaser: InvestmentTeaser, workspace_name: str, run_id: str) -> bytes:
    """Convert InvestmentTeaser to a PDF page."""
    content = f"""# Investment Teaser — {workspace_name}

## The Problem
{teaser.problem}

## Our Solution
{teaser.solution}

## Simulation Validation
{teaser.simulated_survival}

## Key Metrics
{chr(10).join(f'- {m}' for m in teaser.key_metrics)}

## The Ask
{teaser.ask}

## Key Risks
{chr(10).join(f'- {r}' for r in teaser.risks)}
"""
    section = {"section_number": 1, "title": "Investment Teaser", "narrative": content}
    return assemble_pdf(
        sections=[section],
        chart_paths={},
        workspace_name=workspace_name,
        run_id=run_id,
        tier="pro",
        report_type="investor_report",
    )


def pitch_outline_to_pdf(outline: PitchDeckOutline, workspace_name: str, run_id: str) -> bytes:
    slides_md = ""
    for slide in outline.slides:
        slides_md += f"\n## Slide {slide.slide_number}: {slide.title}\n"
        for pt in slide.talking_points:
            slides_md += f"- {pt}\n"
    section = {"section_number": 1, "title": "Pitch Deck Outline", "narrative": slides_md}
    return assemble_pdf(
        sections=[section], chart_paths={},
        workspace_name=workspace_name, run_id=run_id, tier="pro", report_type="investor_report",
    )
```

---

## Step 4 — API endpoint

`backend/app/api/v1/endpoints/investor.py`:
```python
import os, tempfile
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, get_current_workspace
from app.agents.investor_tools import generate_teaser, generate_pitch_outline, teaser_to_pdf, pitch_outline_to_pdf
from app.services.deep_report.data_pack import build_data_pack
from app.services.deep_report.manifest import SectionDef, DataInputKey

router = APIRouter(prefix="/investor", tags=["investor"])


async def _build_investor_data(run_id: str, db) -> dict:
    section = SectionDef(section_number=1, title="Investor Data", page_budget=3,
        data_inputs=[DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES,
                     DataInputKey.FORGE_VULNERABILITIES, DataInputKey.BLUEPRINT,
                     DataInputKey.RUN_METADATA],
        prompt_template="investment_teaser.md")
    return await build_data_pack(section, run_id, db)


@router.post("/runs/{run_id}/teaser")
async def generate_teaser_endpoint(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    data = await _build_investor_data(run_id, db)
    teaser = await generate_teaser(data)
    pdf_bytes = teaser_to_pdf(teaser, workspace.name, run_id)
    path = tempfile.mktemp(suffix=".pdf", prefix=f"teaser_{run_id}_")
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return FileResponse(path, media_type="application/pdf", filename=f"teaser_{run_id}.pdf")


@router.post("/runs/{run_id}/pitch-deck")
async def generate_pitch_endpoint(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    data = await _build_investor_data(run_id, db)
    outline = await generate_pitch_outline(data)
    pdf_bytes = pitch_outline_to_pdf(outline, workspace.name, run_id)
    path = tempfile.mktemp(suffix=".pdf", prefix=f"pitch_{run_id}_")
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return FileResponse(path, media_type="application/pdf", filename=f"pitch_outline_{run_id}.pdf")
```

---

## Step 5 — Tests

`backend/tests/unit/agents/test_investor_tools.py`:
```python
import pytest, asyncio, os
from app.agents.investor_tools import generate_teaser, generate_pitch_outline

MOCK_DATA = {
    "mc_aggregates": {"survival_rate": 0.68, "median_lifespan": 18},
    "tick_logs": [{"month": 1, "revenue": 12000, "cash": 86000}],
    "forge_vulnerabilities": [{"title": "High CAC", "severity": "HIGH"}],
}

def test_generate_teaser_returns_teaser():
    os.environ.setdefault("LLM_PROVIDER", "mock")
    result = asyncio.get_event_loop().run_until_complete(generate_teaser(MOCK_DATA))
    assert result.problem
    assert result.simulated_survival
    assert len(result.key_metrics) >= 3

def test_generate_pitch_outline_has_10_plus_slides():
    os.environ.setdefault("LLM_PROVIDER", "mock")
    result = asyncio.get_event_loop().run_until_complete(generate_pitch_outline(MOCK_DATA))
    assert len(result.slides) >= 10

def test_teaser_to_pdf_returns_bytes():
    from app.schemas.investor import InvestmentTeaser
    from app.agents.investor_tools import teaser_to_pdf
    teaser = InvestmentTeaser(
        problem="Test problem.", solution="Test solution.",
        simulated_survival="68% survival", key_metrics=["MRR: $12k", "CAC: $450", "Runway: 18mo"],
        ask="Raising $500K", risks=["High churn"]
    )
    pdf = teaser_to_pdf(teaser, "TestCo", "run_001")
    assert isinstance(pdf, bytes)
    assert len(pdf) > 100
```

---

## Verification Commands
```bash
cd backend && pytest tests/unit/agents/test_investor_tools.py -v
cd backend && ruff check app/agents/investor_tools.py app/api/v1/endpoints/investor.py
```

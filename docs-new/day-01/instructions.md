# Day 01 — F-01: Report Manifest Schema + Celery Job Skeleton

## Feature
F-01: Deep-Dive Report Engine

## Goal
Define the manifest system that drives the entire 70-page report pipeline. Build the Celery job skeleton that walks the manifest and publishes section-progress to Redis — without calling DeepSeek yet.

## Prerequisites
- Phases 0–9 complete (all infra live)
- `app/services/report_service.py` exists
- `app/workers/` directory exists (Monte Carlo worker pattern to follow)
- Redis running, Celery configured
- `app/agents/bridge.py` exists

---

## Step 1 — Create the `deep_report` service package

```
backend/app/services/deep_report/__init__.py
backend/app/services/deep_report/manifest.py
backend/app/services/deep_report/section_schemas.py
backend/app/services/deep_report/data_pack.py          (stub only today)
```

### `backend/app/services/deep_report/__init__.py`
```python
"""Deep-Dive Report Engine service package."""
```

### `backend/app/services/deep_report/manifest.py`

Define `SectionDef` and `ReportManifest` Pydantic models:

```python
from __future__ import annotations
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class ReportTier(str, Enum):
    FREE = "free"         # 5-page summary: sections 2, 9, 11
    PRO = "pro"           # 25-page standard: sections 1–13
    ENTERPRISE = "enterprise"  # full 70-page: all 21 sections


class DataInputKey(str, Enum):
    """Keys that the data_pack builder knows how to populate."""
    BLUEPRINT = "blueprint"
    TICK_LOGS = "tick_logs"
    MC_AGGREGATES = "mc_aggregates"
    FORGE_VULNERABILITIES = "forge_vulnerabilities"
    OPTIMIZATION_ENTRIES = "optimization_entries"
    CHRONICLE = "chronicle"
    COMPARISON_DELTAS = "comparison_deltas"
    RUN_METADATA = "run_metadata"
    ENGINE_CONFIG = "engine_config"
    EVENTS_DECISIONS = "events_decisions"


class SectionDef(BaseModel):
    """Definition of a single report section."""
    section_number: int = Field(..., ge=1, le=21)
    title: str = Field(..., min_length=3)
    page_budget: int = Field(..., ge=1, le=10)
    data_inputs: list[DataInputKey]
    prompt_template: str   # filename under agents/prompts/sections/
    ai_generated: bool = True   # False = deterministic template only
    tier_minimum: ReportTier = ReportTier.FREE
    fallback_data_only: bool = True  # always True — report never fails


class ReportManifest(BaseModel):
    """Complete definition of a report type."""
    name: str
    report_type: Literal["resilience_audit", "investor_report", "lender_report", "strategy_review"]
    tier: ReportTier
    sections: list[SectionDef]
    total_page_budget: int = Field(0)

    @model_validator(mode="after")
    def compute_total(self) -> "ReportManifest":
        self.total_page_budget = sum(s.page_budget for s in self.sections)
        return self

    def sections_for_tier(self, tier: ReportTier) -> list[SectionDef]:
        """Return only sections available for the given tier."""
        tier_order = [ReportTier.FREE, ReportTier.PRO, ReportTier.ENTERPRISE]
        tier_index = tier_order.index(tier)
        return [
            s for s in self.sections
            if tier_order.index(s.tier_minimum) <= tier_index
        ]
```

### `backend/app/services/deep_report/section_schemas.py`

Structured output schemas for each AI-generated section (bridge validates against these):

```python
from pydantic import BaseModel, Field


class ExecutiveSummarySection(BaseModel):
    verdict: str = Field(..., description="One-sentence pass/fail verdict")
    headline_metrics: list[str] = Field(..., min_length=3, max_length=5)
    narrative: str = Field(..., min_length=100)
    risk_level: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")


class FinancialNarrativeSection(BaseModel):
    month_stories: list[str] = Field(..., min_length=1, max_length=24,
        description="One narrative sentence per simulated month")
    key_inflection_months: list[int]
    overall_narrative: str = Field(..., min_length=200)


class WeaknessRegisterSection(BaseModel):
    weaknesses: list[dict] = Field(..., description="Each: {title, severity, description, mitigation}")
    summary: str


class ActionPlanSection(BaseModel):
    actions: list[dict] = Field(..., min_length=3, max_length=10,
        description="Each: {priority, action, owner, timeline, expected_impact}")
    narrative: str


class GenericNarrativeSection(BaseModel):
    """Fallback schema for sections that only need narrative text."""
    narrative: str = Field(..., min_length=50)
    key_points: list[str] = Field(..., min_length=1)
```

### `backend/app/services/deep_report/data_pack.py` (stub)

```python
from __future__ import annotations
from typing import Any
from app.services.deep_report.manifest import SectionDef, DataInputKey


async def build_data_pack(section: SectionDef, run_id: str, db) -> dict[str, Any]:
    """
    Assemble the deterministic data pack for a single section.
    Stub: returns empty keyed dict. Fleshed out on Day 02.
    """
    return {key.value: None for key in section.data_inputs}
```

---

## Step 2 — Build the manifest registry

Create `backend/app/services/deep_report/registry.py`:

```python
from app.services.deep_report.manifest import (
    ReportManifest, SectionDef, ReportTier, DataInputKey
)

# Full 21-section Enterprise manifest
FULL_MANIFEST = ReportManifest(
    name="Investor-Grade Resilience Audit",
    report_type="resilience_audit",
    tier=ReportTier.ENTERPRISE,
    sections=[
        SectionDef(section_number=1,  title="Cover, Disclaimer, Table of Contents",
                   page_budget=3,  data_inputs=[DataInputKey.RUN_METADATA],
                   prompt_template="cover.md", ai_generated=False,
                   tier_minimum=ReportTier.PRO),
        SectionDef(section_number=2,  title="Executive Summary",
                   page_budget=2,  data_inputs=[DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES,
                                                DataInputKey.FORGE_VULNERABILITIES],
                   prompt_template="executive_summary.md", tier_minimum=ReportTier.FREE),
        SectionDef(section_number=3,  title="Business Blueprint Overview",
                   page_budget=3,  data_inputs=[DataInputKey.BLUEPRINT, DataInputKey.FORGE_VULNERABILITIES],
                   prompt_template="blueprint_overview.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=4,  title="Methodology & Simulation Assumptions",
                   page_budget=2,  data_inputs=[DataInputKey.ENGINE_CONFIG, DataInputKey.RUN_METADATA],
                   prompt_template="methodology.md", ai_generated=False, tier_minimum=ReportTier.PRO),
        SectionDef(section_number=5,  title="Market & Demand Dynamics Analysis",
                   page_budget=4,  data_inputs=[DataInputKey.TICK_LOGS, DataInputKey.ENGINE_CONFIG],
                   prompt_template="market_dynamics.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=6,  title="24-Month Financial Narrative",
                   page_budget=6,  data_inputs=[DataInputKey.TICK_LOGS],
                   prompt_template="financial_narrative.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=7,  title="Unit Economics Deep Dive",
                   page_budget=4,  data_inputs=[DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES],
                   prompt_template="unit_economics.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=8,  title="Cash Flow & Runway Forensics",
                   page_budget=3,  data_inputs=[DataInputKey.TICK_LOGS],
                   prompt_template="cashflow_forensics.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=9,  title="Monte Carlo Results & Distribution Analysis",
                   page_budget=5,  data_inputs=[DataInputKey.MC_AGGREGATES],
                   prompt_template="monte_carlo.md", tier_minimum=ReportTier.FREE),
        SectionDef(section_number=10, title="Kill-Vector Autopsy",
                   page_budget=4,  data_inputs=[DataInputKey.MC_AGGREGATES, DataInputKey.TICK_LOGS],
                   prompt_template="kill_vector_autopsy.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=11, title="Architectural Weaknesses Register",
                   page_budget=3,  data_inputs=[DataInputKey.FORGE_VULNERABILITIES],
                   prompt_template="weaknesses_register.md", tier_minimum=ReportTier.FREE),
        SectionDef(section_number=12, title="Stress-Test Timeline & Decision Review",
                   page_budget=4,  data_inputs=[DataInputKey.EVENTS_DECISIONS, DataInputKey.CHRONICLE],
                   prompt_template="stress_test_review.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=13, title="Counter-Factual Analysis",
                   page_budget=3,  data_inputs=[DataInputKey.OPTIMIZATION_ENTRIES],
                   prompt_template="counterfactual.md", tier_minimum=ReportTier.PRO),
        SectionDef(section_number=14, title="Sensitivity Analysis & Tornado Chart",
                   page_budget=3,  data_inputs=[DataInputKey.MC_AGGREGATES, DataInputKey.ENGINE_CONFIG],
                   prompt_template="sensitivity.md", tier_minimum=ReportTier.ENTERPRISE),
        SectionDef(section_number=15, title="Cohort Benchmark",
                   page_budget=3,  data_inputs=[DataInputKey.MC_AGGREGATES],
                   prompt_template="cohort_benchmark.md", tier_minimum=ReportTier.ENTERPRISE),
        SectionDef(section_number=16, title="Risk Register & Mitigation Matrix",
                   page_budget=3,  data_inputs=[DataInputKey.FORGE_VULNERABILITIES, DataInputKey.MC_AGGREGATES],
                   prompt_template="risk_register.md", tier_minimum=ReportTier.ENTERPRISE),
        SectionDef(section_number=17, title="Prescriptive Optimization Plan",
                   page_budget=3,  data_inputs=[DataInputKey.OPTIMIZATION_ENTRIES],
                   prompt_template="optimization_plan.md", tier_minimum=ReportTier.ENTERPRISE),
        SectionDef(section_number=18, title="90-Day Action Plan",
                   page_budget=2,  data_inputs=[DataInputKey.FORGE_VULNERABILITIES, DataInputKey.OPTIMIZATION_ENTRIES],
                   prompt_template="action_plan.md", tier_minimum=ReportTier.ENTERPRISE),
        SectionDef(section_number=19, title="Scenario Comparison Appendix",
                   page_budget=3,  data_inputs=[DataInputKey.COMPARISON_DELTAS],
                   prompt_template="scenario_comparison.md", tier_minimum=ReportTier.ENTERPRISE),
        SectionDef(section_number=20, title="Full KPI Appendix",
                   page_budget=5,  data_inputs=[DataInputKey.TICK_LOGS],
                   prompt_template="kpi_appendix.md", ai_generated=False, tier_minimum=ReportTier.ENTERPRISE),
        SectionDef(section_number=21, title="Glossary, Data Dictionary & Reproducibility",
                   page_budget=2,  data_inputs=[DataInputKey.RUN_METADATA, DataInputKey.ENGINE_CONFIG],
                   prompt_template="glossary.md", ai_generated=False, tier_minimum=ReportTier.ENTERPRISE),
    ]
)

MANIFEST_REGISTRY: dict[str, ReportManifest] = {
    "resilience_audit": FULL_MANIFEST,
}

def get_manifest(report_type: str) -> ReportManifest:
    if report_type not in MANIFEST_REGISTRY:
        raise KeyError(f"Unknown report type: {report_type}")
    return MANIFEST_REGISTRY[report_type]
```

---

## Step 3 — Create the Celery report job skeleton

Create `backend/app/workers/report_job.py`:

```python
"""
Celery task: walk a report manifest section-by-section,
publish progress to Redis, and log each step.
DeepSeek section generation is stubbed — added Day 03.
"""
from __future__ import annotations
import logging
import json
from celery import shared_task
from app.db.session import AsyncSessionLocal
from app.services.deep_report.manifest import ReportTier
from app.services.deep_report.registry import get_manifest
from app.services.deep_report.data_pack import build_data_pack
from app.core.config import settings

logger = logging.getLogger(__name__)

REDIS_PROGRESS_KEY = "deep_report:progress:{job_id}"


def _publish_progress(redis_client, job_id: str, section: int, total: int, status: str, title: str) -> None:
    """Publish section progress to Redis for WebSocket forwarding."""
    payload = {
        "job_id": job_id,
        "section": section,
        "total": total,
        "status": status,      # "writing" | "linting" | "done" | "error"
        "section_title": title,
    }
    redis_client.publish(f"deep_report:{job_id}", json.dumps(payload))
    redis_client.set(
        REDIS_PROGRESS_KEY.format(job_id=job_id),
        json.dumps(payload),
        ex=3600
    )


@shared_task(bind=True, name="workers.report_job.generate_deep_report")
def generate_deep_report(
    self,
    job_id: str,
    run_id: str,
    report_type: str,
    tier: str,
) -> dict:
    """
    Walk the manifest for the given report_type and tier.
    For each section:
      1. Build the deterministic data pack
      2. [Day 03] Call section writer (DeepSeek)
      3. [Day 03] Run section linter
      4. [Day 05] Assemble into PDF
    Today: logs + publishes progress only.
    """
    import asyncio
    import redis

    redis_client = redis.from_url(settings.REDIS_URL)
    manifest = get_manifest(report_type)
    tier_enum = ReportTier(tier)
    sections = manifest.sections_for_tier(tier_enum)
    total = len(sections)

    logger.info(f"[report_job] Starting job={job_id} run={run_id} type={report_type} tier={tier} sections={total}")

    results: list[dict] = []

    for idx, section in enumerate(sections, start=1):
        _publish_progress(redis_client, job_id, idx, total, "writing", section.title)
        logger.info(f"[report_job] job={job_id} section={idx}/{total} '{section.title}'")

        # Data pack (stub returns empty keys today; fleshed out Day 02)
        async def _get_pack():
            async with AsyncSessionLocal() as db:
                return await build_data_pack(section, run_id, db)

        data_pack = asyncio.get_event_loop().run_until_complete(_get_pack())

        # Placeholder: section content will be generated Day 03
        section_result = {
            "section_number": section.section_number,
            "title": section.title,
            "status": "stub",
            "content": f"# {section.title}\n\n_Content will be generated by DeepSeek (Day 03)._",
            "data_pack_keys": list(data_pack.keys()),
        }
        results.append(section_result)

        _publish_progress(redis_client, job_id, idx, total, "done", section.title)

    logger.info(f"[report_job] Completed job={job_id} total_sections={len(results)}")
    return {"job_id": job_id, "run_id": run_id, "sections_completed": len(results), "status": "stub_complete"}
```

---

## Step 4 — Create unit test file

Create `backend/tests/unit/deep_report/test_manifest.py`:

```python
import pytest
from app.services.deep_report.manifest import (
    ReportManifest, SectionDef, ReportTier, DataInputKey
)
from app.services.deep_report.registry import get_manifest, FULL_MANIFEST


def test_full_manifest_section_count():
    assert len(FULL_MANIFEST.sections) == 21


def test_full_manifest_total_pages():
    assert FULL_MANIFEST.total_page_budget == 70


def test_free_tier_sections():
    sections = FULL_MANIFEST.sections_for_tier(ReportTier.FREE)
    numbers = [s.section_number for s in sections]
    assert 2 in numbers  # executive summary
    assert 9 in numbers  # monte carlo
    assert 11 in numbers  # weaknesses
    assert len(sections) == 3


def test_pro_tier_sections():
    sections = FULL_MANIFEST.sections_for_tier(ReportTier.PRO)
    numbers = [s.section_number for s in sections]
    assert 1 in numbers
    assert 13 in numbers
    assert 14 not in numbers  # enterprise only


def test_enterprise_tier_all_sections():
    sections = FULL_MANIFEST.sections_for_tier(ReportTier.ENTERPRISE)
    assert len(sections) == 21


def test_section_def_validation():
    with pytest.raises(Exception):
        SectionDef(
            section_number=0,   # invalid: ge=1
            title="x",
            page_budget=2,
            data_inputs=[],
            prompt_template="x.md"
        )


def test_get_manifest_unknown_raises():
    with pytest.raises(KeyError):
        get_manifest("nonexistent_type")


def test_manifest_page_budget_computed():
    manifest = ReportManifest(
        name="Test",
        report_type="resilience_audit",
        tier=ReportTier.FREE,
        sections=[
            SectionDef(section_number=1, title="Sec One", page_budget=3,
                       data_inputs=[DataInputKey.RUN_METADATA],
                       prompt_template="x.md"),
            SectionDef(section_number=2, title="Sec Two", page_budget=5,
                       data_inputs=[DataInputKey.BLUEPRINT],
                       prompt_template="y.md"),
        ]
    )
    assert manifest.total_page_budget == 8
```

---

## Step 5 — Register the Celery task

In `backend/app/workers/__init__.py` (or wherever Celery autodiscovers tasks), ensure `report_job` is included:

```python
# add to existing autodiscover list
app.autodiscover_tasks(["app.workers.report_job"])
```

## Step 6 — Install no new dependencies

All dependencies (Celery, Redis, Pydantic) are already in `requirements.txt`. No new installs needed today.

---

## Verification Commands

```bash
# Backend tests
cd backend && pytest tests/unit/deep_report/test_manifest.py -v

# Lint + type check
cd backend && ruff check app/services/deep_report app/workers/report_job.py
cd backend && mypy app/services/deep_report app/workers/report_job.py

# Confirm Celery can import the task (no runtime error)
cd backend && python -c "from app.workers.report_job import generate_deep_report; print('Task registered:', generate_deep_report.name)"
```

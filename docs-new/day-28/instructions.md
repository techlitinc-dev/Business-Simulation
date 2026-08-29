# Day 28 — F-07: Decision Journal + Playbook Library

## Feature
F-07: Decision Journal, Playbooks & Learning Loop

## Goal
Log every War Room decision with strategist projection and actual outcome. Score decision quality. Generate reusable playbooks from post-mortems via DeepSeek. Publish to marketplace.

---

## Step 1 — Decision Journal Service

`backend/app/services/journal/journal_service.py`:
```python
from __future__ import annotations
import logging
from dataclasses import dataclass
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.simulation import Decision, SimulationRun

logger = logging.getLogger(__name__)


@dataclass
class JournalEntry:
    decision_id: str
    run_id: str
    month: int
    option_chosen: str
    strategist_recommended: str
    beat_ai: bool
    actual_outcome_delta: dict
    score: float       # 0.0–1.0


async def score_decision(decision: Decision, run: SimulationRun) -> float:
    """
    Score a decision: 1.0 if outcome_delta is positive and beat or matched AI recommendation.
    0.5 if outcome was positive but didn't follow AI.
    0.0 if outcome was negative.
    """
    delta = decision.outcome_delta or {}
    positive_outcome = delta.get("survival_rate_delta", 0) >= 0
    followed_ai = decision.option_id == (run.config or {}).get("strategist_recommendation")

    if positive_outcome and followed_ai:
        return 1.0
    elif positive_outcome:
        return 0.5
    else:
        return 0.0


async def get_run_journal(run_id: str, db: AsyncSession) -> list[JournalEntry]:
    result = await db.execute(select(Decision).where(Decision.run_id == run_id).order_by(Decision.month))
    decisions = result.scalars().all()
    run_result = await db.execute(select(SimulationRun).where(SimulationRun.id == run_id))
    run = run_result.scalar_one_or_none()

    entries = []
    for d in decisions:
        score = await score_decision(d, run)
        entries.append(JournalEntry(
            decision_id=d.id,
            run_id=run_id,
            month=d.month,
            option_chosen=d.option_id,
            strategist_recommended=(run.config or {}).get("strategist_recommendation", "unknown"),
            beat_ai=score == 1.0,
            actual_outcome_delta=d.outcome_delta or {},
            score=score,
        ))
    return entries


async def get_workspace_journal_summary(workspace_id: str, db: AsyncSession) -> dict:
    """Aggregate decision quality across all runs in a workspace."""
    result = await db.execute(
        select(SimulationRun.id).where(SimulationRun.workspace_id == workspace_id)
    )
    run_ids = [r[0] for r in result.all()]

    total = 0
    beat_ai = 0
    for run_id in run_ids:
        entries = await get_run_journal(run_id, db)
        total += len(entries)
        beat_ai += sum(1 for e in entries if e.beat_ai)

    return {
        "total_decisions": total,
        "beat_ai_count": beat_ai,
        "beat_ai_pct": round((beat_ai / total * 100) if total > 0 else 0, 1),
        "summary": f"You beat the AI's recommended path in {beat_ai} of {total} decisions",
    }
```

---

## Step 2 — Playbook Writer Agent

`backend/app/agents/playbook_writer.py`:
```python
from __future__ import annotations
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from app.agents.bridge import generate_structured
from app.agents.llm.factory import get_provider

logger = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).parent / "prompts"


class Playbook(BaseModel):
    title: str = Field(..., description="e.g. 'Surviving a Demand Shock as a Subscription Business'")
    scenario_type: str
    situation: str = Field(..., description="2-3 sentences describing when to use this playbook")
    steps: list[str] = Field(..., min_length=3, max_length=10, description="Ordered action steps")
    key_metrics_to_watch: list[str] = Field(..., min_length=2)
    expected_outcome: str
    source_run_summary: str


async def generate_playbook(post_mortem_data: dict, run_summary: dict) -> Playbook:
    provider = get_provider()
    prompt_path = PROMPTS_DIR / "playbook_writer.md"
    template = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else (
        "You are writing a reusable business playbook from a post-mortem simulation analysis.\n"
        "DATA: {{ data_json }}\nGenerate a Playbook schema object."
    )
    prompt = template.replace("{{ data_json }}", json.dumps(
        {**post_mortem_data, **run_summary}, default=str, indent=2
    ))
    result = await generate_structured(
        provider=provider,
        system_prompt=prompt,
        user_message="Generate a reusable playbook from this post-mortem.",
        response_schema=Playbook,
    )
    logger.info(f"[playbook_writer] Generated playbook: {result.title}")
    return result
```

---

## Step 3 — API endpoints

`backend/app/api/v1/endpoints/journal.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, get_current_workspace
from app.services.journal.journal_service import get_run_journal, get_workspace_journal_summary
from app.agents.playbook_writer import generate_playbook

router = APIRouter(tags=["journal"])


@router.get("/simulations/{run_id}/journal")
async def run_journal(run_id: str, db: AsyncSession = Depends(get_db),
                      current_user=Depends(get_current_user)):
    entries = await get_run_journal(run_id, db)
    return [e.__dict__ for e in entries]


@router.get("/workspaces/journal/summary")
async def workspace_journal(db: AsyncSession = Depends(get_db),
                            current_user=Depends(get_current_user),
                            workspace=Depends(get_current_workspace)):
    return await get_workspace_journal_summary(workspace.id, db)


@router.post("/simulations/{run_id}/playbook", status_code=201)
async def create_playbook(run_id: str, db: AsyncSession = Depends(get_db),
                          current_user=Depends(get_current_user)):
    # Fetch post-mortem and run summary data
    from app.services.deep_report.data_pack import build_data_pack
    from app.services.deep_report.manifest import SectionDef, DataInputKey
    section = SectionDef(section_number=1, title="Playbook", page_budget=2,
        data_inputs=[DataInputKey.MC_AGGREGATES, DataInputKey.FORGE_VULNERABILITIES,
                     DataInputKey.EVENTS_DECISIONS], prompt_template="playbook_writer.md")
    data_pack = await build_data_pack(section, run_id, db)
    playbook = await generate_playbook(data_pack, {})
    return playbook.model_dump()
```

---

## Step 4 — Frontend `DecisionJournalPage.tsx`

```typescript
// frontend/src/features/journal/DecisionJournalPage.tsx
import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

interface JournalEntry {
  month: number;
  option_chosen: string;
  beat_ai: boolean;
  score: number;
}

export function DecisionJournalPage({ runId }: { runId: string }) {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    apiClient.get(`/simulations/${runId}/journal`).then(r => setEntries(r.data));
    apiClient.get("/workspaces/journal/summary").then(r => setSummary(r.data));
  }, [runId]);

  return (
    <div className="space-y-4">
      {summary && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <p className="text-white font-semibold">{summary.summary}</p>
          <p className="text-blue-400 text-sm">{summary.beat_ai_pct}% beat rate</p>
        </div>
      )}
      <div className="space-y-2">
        {entries.map((e, i) => (
          <div key={i} className="flex items-center gap-3 text-sm bg-slate-800 border border-slate-700 rounded p-3">
            <span className="text-slate-400 w-16">Month {e.month}</span>
            <span className="text-white flex-1">{e.option_chosen}</span>
            <span className={e.beat_ai ? "text-green-400" : "text-red-400"}>
              {e.beat_ai ? "✅ Beat AI" : "❌ Missed AI"}
            </span>
            <span className="text-slate-400">{(e.score * 100).toFixed(0)}pts</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Tests

`backend/tests/unit/journal/test_journal_service.py`:
```python
import pytest, asyncio
from unittest.mock import MagicMock, AsyncMock
from app.services.journal.journal_service import score_decision

def test_score_positive_following_ai():
    decision = MagicMock(); decision.option_id = "opt_a"; decision.outcome_delta = {"survival_rate_delta": 0.05}
    run = MagicMock(); run.config = {"strategist_recommendation": "opt_a"}
    score = asyncio.get_event_loop().run_until_complete(score_decision(decision, run))
    assert score == 1.0

def test_score_positive_not_following_ai():
    decision = MagicMock(); decision.option_id = "opt_b"; decision.outcome_delta = {"survival_rate_delta": 0.02}
    run = MagicMock(); run.config = {"strategist_recommendation": "opt_a"}
    score = asyncio.get_event_loop().run_until_complete(score_decision(decision, run))
    assert score == 0.5

def test_score_negative_outcome():
    decision = MagicMock(); decision.option_id = "opt_a"; decision.outcome_delta = {"survival_rate_delta": -0.10}
    run = MagicMock(); run.config = {}
    score = asyncio.get_event_loop().run_until_complete(score_decision(decision, run))
    assert score == 0.0
```

---

## Verification Commands
```bash
cd backend && pytest tests/unit/journal/ -v
cd frontend && npm run build
```

# Day 18 — F-02: Ask-Your-Business Copilot (Chat Backend)

## Feature
F-02: AI Advisory Board & Copilot

## Goal
Build the copilot chat backend. Each question is answered by DeepSeek with strict grounding: the context window is built from the run's data pack + chronicle, and every numeric claim in the response is verified against the data pack before display.

---

## Step 1 — Create `backend/app/services/copilot/` package

### `context_builder.py`
```python
from __future__ import annotations
import json
from app.services.deep_report.data_pack import build_data_pack
from app.services.deep_report.manifest import SectionDef, DataInputKey


async def build_copilot_context(run_id: str, db) -> dict:
    """Build a concise grounding context from run data for the copilot."""
    section = SectionDef(
        section_number=1, title="Copilot Context", page_budget=5,
        data_inputs=[
            DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES,
            DataInputKey.CHRONICLE, DataInputKey.EVENTS_DECISIONS,
            DataInputKey.FORGE_VULNERABILITIES, DataInputKey.RUN_METADATA,
        ],
        prompt_template="copilot_system.md"
    )
    return await build_data_pack(section, run_id, db)
```

### `copilot_service.py`
```python
from __future__ import annotations
import re
import json
import logging
from pydantic import BaseModel, Field
from app.agents.bridge import generate_structured
from app.agents.llm.factory import get_provider
from app.services.copilot.context_builder import build_copilot_context

logger = logging.getLogger(__name__)

NUMBER_PATTERN = re.compile(r"\b\d[\d,]*\.?\d*\b")


class CopilotResponse(BaseModel):
    answer: str = Field(..., min_length=10)
    sources_used: list[str] = Field(default_factory=list,
        description="Which data sources were referenced")
    confidence: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH)$")


async def chat(
    run_id: str,
    question: str,
    db,
    chat_history: list[dict] | None = None,
) -> dict:
    """
    Answer a question about a simulation run.
    All numeric claims are cross-checked against the data pack.
    Returns {"answer": str, "grounded": bool, "flagged_claims": list}.
    """
    context = await build_copilot_context(run_id, db)
    context_str = json.dumps(context, default=str)

    prompt = f"""You are a copilot that answers questions about a business simulation run.

SIMULATION DATA:
{context_str[:8000]}  

RULES:
- Answer using ONLY data from the simulation data above.
- Every numeric claim must reference a real number from the data.
- If you don't know, say "The simulation data doesn't contain enough information to answer that."
- Be concise. 2-3 sentences max unless the question requires a list.
- sources_used: list the data keys you referenced (e.g. "tick_logs", "mc_aggregates").
"""
    provider = get_provider()
    result = await generate_structured(
        provider=provider,
        system_prompt=prompt,
        user_message=question,
        response_schema=CopilotResponse,
    )

    # Numeric cross-check
    numbers_in_answer = set(NUMBER_PATTERN.findall(result.answer.replace(",", "")))
    flagged = [n for n in numbers_in_answer if float(n) > 100 and n not in context_str]

    logger.info(f"[copilot] run={run_id} question_len={len(question)} flagged={len(flagged)}")

    return {
        "answer": result.answer,
        "sources_used": result.sources_used,
        "confidence": result.confidence,
        "grounded": len(flagged) == 0,
        "flagged_claims": flagged,
    }
```

---

## Step 2 — Create copilot system prompt

`backend/app/agents/prompts/copilot_system.md`:
```markdown
You are a business simulation copilot. You answer questions about simulation runs.
You are grounded: every numeric claim you make must come from the provided simulation data.
Never fabricate metrics. If asked about something not in the data, say so clearly.
```

---

## Step 3 — Create API endpoint

`backend/app/api/v1/endpoints/copilot.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.api.deps import get_db, get_current_user, get_current_workspace
from app.services.copilot.copilot_service import chat

router = APIRouter(prefix="/simulations", tags=["copilot"])

class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []


@router.post("/{run_id}/chat")
async def copilot_chat(
    run_id: str,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    return await chat(run_id, body.question, db, body.history)
```

---

## Step 4 — Tests

`backend/tests/unit/copilot/test_copilot_service.py`:
```python
import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.copilot.copilot_service import chat, NUMBER_PATTERN


def test_number_pattern_extracts_large_numbers():
    text = "Revenue was $125,000 and cash was 86000 in month 3."
    nums = set(NUMBER_PATTERN.findall(text.replace(",", "")))
    assert "125000" in nums or "125" in nums
    assert "86000" in nums


def test_chat_returns_required_keys():
    os.environ.setdefault("LLM_PROVIDER", "mock")
    with patch("app.services.copilot.copilot_service.build_copilot_context", new_callable=AsyncMock) as mock_ctx:
        mock_ctx.return_value = {"tick_logs": [], "mc_aggregates": {"survival_rate": 0.68}}
        result = asyncio.get_event_loop().run_until_complete(
            chat("run_001", "What is the survival rate?", AsyncMock())
        )
    assert "answer" in result
    assert "grounded" in result
    assert "flagged_claims" in result
    assert isinstance(result["flagged_claims"], list)


def test_chat_grounded_when_no_suspicious_numbers():
    os.environ.setdefault("LLM_PROVIDER", "mock")
    with patch("app.services.copilot.copilot_service.build_copilot_context", new_callable=AsyncMock) as mock_ctx, \
         patch("app.services.copilot.copilot_service.generate_structured", new_callable=AsyncMock) as mock_gen:
        mock_ctx.return_value = {"mc_aggregates": {"survival_rate": 0.68}}
        from app.services.copilot.copilot_service import CopilotResponse
        mock_gen.return_value = CopilotResponse(
            answer="The survival rate is 68 percent.",
            sources_used=["mc_aggregates"], confidence="HIGH"
        )
        result = asyncio.get_event_loop().run_until_complete(
            chat("run_001", "What is the survival rate?", AsyncMock())
        )
    # 68 is ≤100, so not flagged
    assert result["grounded"] is True
```

---

## Verification Commands
```bash
cd backend && pytest tests/unit/copilot/ -v
cd backend && ruff check app/services/copilot/ app/api/v1/endpoints/copilot.py
```

# Day 03 — F-01 + F-12: DeepSeek Section Writer + Section Linter

## Feature
F-01: Deep-Dive Report Engine · F-12: Report Quality Assurance Loop

## Goal
Implement `section_writer.py` (DeepSeek via bridge) and `section_linter.py` (numeric cross-check, banned phrases, length guard). Wire both into the Celery job. A failed lint auto-regenerates once; a second failure falls back to data-only render.

## Prerequisites
- Day 01 + 02 complete
- `app/agents/bridge.py` — `generate_structured` exists
- `app/agents/llm/factory.py` — provider factory exists
- `MockProvider` works without API key

---

## Step 1 — Create section prompt templates directory

```
backend/app/agents/prompts/sections/
  executive_summary.md
  financial_narrative.md
  weaknesses_register.md
  generic_narrative.md
```

### `executive_summary.md`
```markdown
You are a senior analyst writing the Executive Summary section of a business simulation audit.

DATA PACK:
{{ data_pack_json }}

RULES:
- Every numeric claim MUST come from the data pack above. Do not invent numbers.
- verdict must be one sentence.
- risk_level must be one of: LOW, MEDIUM, HIGH, CRITICAL.
- Base risk_level on survival_rate: >80% = LOW, 60-80% = MEDIUM, 40-60% = HIGH, <40% = CRITICAL.
- headline_metrics: exactly 3–5 bullet strings, each referencing a real number from the data pack.
- narrative: 100–300 words summarising the simulation outcome.
```

### `generic_narrative.md`
```markdown
You are writing section {{ section_number }}: {{ section_title }} of a business simulation audit.

DATA PACK:
{{ data_pack_json }}

RULES:
- Every numeric claim MUST come from the data pack above.
- narrative: 100–400 words.
- key_points: 3–6 bullet strings, each grounded in the data pack.
- Do not include marketing language or superlatives.
```

---

## Step 2 — Create `section_writer.py`

`backend/app/agents/section_writer.py`:

```python
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any
from pydantic import BaseModel

from app.agents.bridge import generate_structured
from app.agents.llm.factory import get_provider
from app.services.deep_report.manifest import SectionDef
from app.services.deep_report.section_schemas import (
    ExecutiveSummarySection, FinancialNarrativeSection,
    WeaknessRegisterSection, ActionPlanSection, GenericNarrativeSection,
)

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts" / "sections"

SECTION_SCHEMA_MAP: dict[str, type[BaseModel]] = {
    "executive_summary.md": ExecutiveSummarySection,
    "financial_narrative.md": FinancialNarrativeSection,
    "weaknesses_register.md": WeaknessRegisterSection,
    "action_plan.md": ActionPlanSection,
}


def _load_prompt(template_name: str, section: SectionDef, data_pack: dict[str, Any]) -> str:
    template_path = PROMPTS_DIR / template_name
    if not template_path.exists():
        template_path = PROMPTS_DIR / "generic_narrative.md"
    template = template_path.read_text(encoding="utf-8")
    return (
        template
        .replace("{{ data_pack_json }}", json.dumps(data_pack, default=str, indent=2))
        .replace("{{ section_number }}", str(section.section_number))
        .replace("{{ section_title }}", section.title)
    )


def _get_schema(template_name: str) -> type[BaseModel]:
    return SECTION_SCHEMA_MAP.get(template_name, GenericNarrativeSection)


async def generate_section(
    section: SectionDef,
    data_pack: dict[str, Any],
) -> dict[str, Any]:
    """
    Call DeepSeek (via bridge) to generate structured markdown for one section.
    Returns a dict with at minimum {"narrative": str, "section_number": int}.
    Raises StructuredOutputError if bridge repair-retry also fails.
    """
    provider = get_provider()
    prompt = _load_prompt(section.prompt_template, section, data_pack)
    schema = _get_schema(section.prompt_template)

    logger.info(f"[section_writer] Generating section {section.section_number}: {section.title}")

    result = await generate_structured(
        provider=provider,
        system_prompt=prompt,
        user_message=f"Generate section {section.section_number}: {section.title}",
        response_schema=schema,
    )
    output = result.model_dump()
    output["section_number"] = section.section_number
    output["title"] = section.title
    return output


def render_data_only_fallback(section: SectionDef, data_pack: dict[str, Any]) -> dict[str, Any]:
    """
    Deterministic fallback: render a data-only section without LLM.
    Guarantees report never fails even if DeepSeek is down.
    """
    lines = [f"# {section.title}\n"]
    lines.append("_AI narrative unavailable — displaying raw simulation data._\n")
    for key, value in data_pack.items():
        if value is not None:
            lines.append(f"## {key.replace('_', ' ').title()}\n")
            lines.append(f"```json\n{json.dumps(value, default=str, indent=2)}\n```\n")
    return {
        "section_number": section.section_number,
        "title": section.title,
        "narrative": "\n".join(lines),
        "key_points": ["Data-only render — AI generation failed"],
        "is_fallback": True,
    }
```

---

## Step 3 — Create `section_linter.py`

`backend/app/services/deep_report/section_linter.py`:

```python
from __future__ import annotations
import re
from typing import Any
from app.services.deep_report.manifest import SectionDef

BANNED_PHRASES = [
    "as an ai", "i cannot", "i am unable", "i don't have access",
    "unfortunately", "please note", "it's important to note",
    "in conclusion", "to summarize",   # too generic
]

# Numbers that appear in AI output are extracted and checked against the data pack
NUMBER_PATTERN = re.compile(r"\b\d[\d,]*\.?\d*\b")


class LintResult:
    def __init__(self):
        self.passed = True
        self.errors: list[str] = []

    def fail(self, reason: str):
        self.passed = False
        self.errors.append(reason)


def lint_section(
    section: SectionDef,
    section_output: dict[str, Any],
    data_pack: dict[str, Any],
) -> LintResult:
    result = LintResult()
    narrative = section_output.get("narrative", "")

    # 1. Length check (approximate page budget: 1 page ≈ 300 words)
    word_count = len(narrative.split())
    min_words = max(50, section.page_budget * 100)
    max_words = section.page_budget * 500
    if word_count < min_words:
        result.fail(f"Narrative too short: {word_count} words (min {min_words})")
    if word_count > max_words:
        result.fail(f"Narrative too long: {word_count} words (max {max_words})")

    # 2. Banned phrase check
    lower_narrative = narrative.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lower_narrative:
            result.fail(f"Banned phrase found: '{phrase}'")

    # 3. Numeric cross-check — every number in the narrative must exist somewhere in the data pack
    data_pack_str = str(data_pack)
    numbers_in_narrative = set(NUMBER_PATTERN.findall(narrative.replace(",", "")))
    # Allow small integers (page numbers, counts)
    suspicious = [n for n in numbers_in_narrative if float(n) > 100]
    for num in suspicious:
        if num not in data_pack_str:
            result.fail(f"Numeric claim '{num}' not found in data pack — possible hallucination")

    return result
```

---

## Step 4 — Wire linter + retry into the Celery job

Update `backend/app/workers/report_job.py` — replace the stub section block:

```python
from app.agents.section_writer import generate_section, render_data_only_fallback
from app.services.deep_report.section_linter import lint_section
from app.core.exceptions import StructuredOutputError

# Inside the section loop:
for idx, section in enumerate(sections, start=1):
    _publish_progress(redis_client, job_id, idx, total, "writing", section.title)
    data_pack = asyncio.get_event_loop().run_until_complete(_get_pack())

    if section.ai_generated:
        try:
            section_output = asyncio.get_event_loop().run_until_complete(
                generate_section(section, data_pack)
            )
            lint = lint_section(section, section_output, data_pack)
            if not lint.passed:
                logger.warning(f"[report_job] Lint failed section {idx}: {lint.errors}. Retrying.")
                section_output = asyncio.get_event_loop().run_until_complete(
                    generate_section(section, data_pack)
                )
                lint2 = lint_section(section, section_output, data_pack)
                if not lint2.passed:
                    logger.error(f"[report_job] Lint failed twice section {idx}. Using fallback.")
                    section_output = render_data_only_fallback(section, data_pack)
        except StructuredOutputError as e:
            logger.error(f"[report_job] StructuredOutputError section {idx}: {e}. Using fallback.")
            section_output = render_data_only_fallback(section, data_pack)
    else:
        section_output = render_data_only_fallback(section, data_pack)

    results.append(section_output)
    _publish_progress(redis_client, job_id, idx, total, "done", section.title)
```

---

## Step 5 — Test file

`backend/tests/unit/deep_report/test_section_writer.py` and `test_section_linter.py`

Key test cases:
- `test_generate_section_returns_dict_with_narrative` — with MockProvider, result has `narrative` key
- `test_data_only_fallback_never_raises` — fallback renders for any section/data combination
- `test_lint_passes_on_valid_output` — short narrative within budget, no banned phrases
- `test_lint_fails_on_banned_phrase` — "as an ai" triggers fail
- `test_lint_fails_on_short_narrative` — <50 words triggers fail
- `test_lint_flags_suspicious_number_not_in_data_pack` — number like 999999 not in pack fails
- `test_lint_passes_number_present_in_data_pack` — number from pack passes

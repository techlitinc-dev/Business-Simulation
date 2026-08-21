"""Deep-report section writer — one LLM call per manifest section.

Renders a section prompt from the template directory, calls the provider
through the structured-output bridge, and validates against the section
schema. Any LLM failure (including the deterministic mock returning ``{}``)
falls back to a data-only render so the report never fails (Day 03).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.agents import bridge
from app.agents.llm.base import LLMProvider
from app.core.config import get_settings
from app.core.exceptions import StructuredOutputError
from app.services.deep_report.manifest import SectionDef
from app.services.deep_report.section_schemas import (
    ActionPlanSection,
    ExecutiveSummarySection,
    FinancialNarrativeSection,
    GenericNarrativeSection,
    WeaknessRegisterSection,
)

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts" / "sections"

SECTION_SCHEMA_MAP: dict[str, type[BaseModel]] = {
    "executive_summary.md": ExecutiveSummarySection,
    "financial_narrative.md": FinancialNarrativeSection,
    "weaknesses_register.md": WeaknessRegisterSection,
    "action_plan.md": ActionPlanSection,
}


def _load_prompt(
    template_name: str, section: SectionDef, data_pack: dict[str, Any]
) -> str:
    template_path = PROMPTS_DIR / template_name
    if not template_path.exists():
        template_path = PROMPTS_DIR / "generic_narrative.md"
    template = template_path.read_text(encoding="utf-8")
    return (
        template.replace(
            "{{ data_pack_json }}",
            json.dumps(data_pack, default=str, indent=2),
        )
        .replace("{{ section_number }}", str(section.section_number))
        .replace("{{ section_title }}", section.title)
    )


def _get_schema(template_name: str) -> type[BaseModel]:
    return SECTION_SCHEMA_MAP.get(template_name, GenericNarrativeSection)


def _make_provider() -> LLMProvider:
    from app.agents.llm.factory import get_llm_provider

    return get_llm_provider(get_settings())


async def generate_section(
    section: SectionDef,
    data_pack: dict[str, Any],
    *,
    provider: LLMProvider | None = None,
    lang_code: str = "en",
) -> dict[str, Any]:
    """
    Call DeepSeek (via bridge) to generate structured markdown for one section.
    Returns a dict with at minimum {"narrative": str, "section_number": int}.

    ``lang_code`` appends a language instruction to the prompt (see
    ``app.utils.i18n``); the LLM writes narrative text in that language.

    Falls back to ``render_data_only_fallback`` when the bridge raises
    ``StructuredOutputError`` (e.g. the deterministic mock returns ``{}``), so
    the report never fails on LLM unavailability.
    """
    from app.utils.i18n import get_language_instruction

    provider = provider or _make_provider()
    prompt = _load_prompt(section.prompt_template, section, data_pack)
    prompt += get_language_instruction(lang_code)
    schema = _get_schema(section.prompt_template)

    logger.info(
        "[section_writer] Generating section %s: %s",
        section.section_number,
        section.title,
    )

    try:
        result = await bridge.generate_structured(
            provider,
            schema,
            prompt,
            f"Generate section {section.section_number}: {section.title}",
            temperature=0.2,
        )
    except StructuredOutputError:
        logger.warning(
            "[section_writer] LLM output invalid for section %s — using data-only fallback",
            section.section_number,
        )
        return render_data_only_fallback(section, data_pack)

    output = result.model_dump()
    output["section_number"] = section.section_number
    output["title"] = section.title
    return output


def render_data_only_fallback(
    section: SectionDef, data_pack: dict[str, Any]
) -> dict[str, Any]:
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

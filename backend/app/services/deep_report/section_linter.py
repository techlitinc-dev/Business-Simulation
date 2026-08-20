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
    def __init__(self) -> None:
        self.passed = True
        self.errors: list[str] = []

    def fail(self, reason: str) -> None:
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

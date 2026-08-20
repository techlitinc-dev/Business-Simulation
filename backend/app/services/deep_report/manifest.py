from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ReportTier(StrEnum):
    FREE = "free"         # 5-page summary: sections 2, 9, 11
    PRO = "pro"           # 25-page standard: sections 1–13
    ENTERPRISE = "enterprise"  # full 70-page: all 21 sections


class DataInputKey(StrEnum):
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
    def compute_total(self) -> ReportManifest:
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

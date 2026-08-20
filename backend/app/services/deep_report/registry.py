from app.services.deep_report.manifest import (
    DataInputKey,
    ReportManifest,
    ReportTier,
    SectionDef,
)
from app.services.deep_report.manifests.lender_manifest import LENDER_MANIFEST

# (section_number, title, page_budget, data_inputs, prompt_template, ai_generated, tier_minimum)
_SECTIONS: list[tuple[int, str, int, list[DataInputKey], str, bool, ReportTier]] = [
    (1, "Cover, Disclaimer, Table of Contents", 3,
     [DataInputKey.RUN_METADATA], "cover.md", False, ReportTier.PRO),
    (2, "Executive Summary", 2,
     [DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES, DataInputKey.FORGE_VULNERABILITIES],
     "executive_summary.md", True, ReportTier.FREE),
    (3, "Business Blueprint Overview", 3,
     [DataInputKey.BLUEPRINT, DataInputKey.FORGE_VULNERABILITIES],
     "blueprint_overview.md", True, ReportTier.PRO),
    (4, "Methodology & Simulation Assumptions", 2,
     [DataInputKey.ENGINE_CONFIG, DataInputKey.RUN_METADATA],
     "methodology.md", False, ReportTier.PRO),
    (5, "Market & Demand Dynamics Analysis", 4,
     [DataInputKey.TICK_LOGS, DataInputKey.ENGINE_CONFIG],
     "market_dynamics.md", True, ReportTier.PRO),
    (6, "24-Month Financial Narrative", 6,
     [DataInputKey.TICK_LOGS], "financial_narrative.md", True, ReportTier.PRO),
    (7, "Unit Economics Deep Dive", 4,
     [DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES],
     "unit_economics.md", True, ReportTier.PRO),
    (8, "Cash Flow & Runway Forensics", 3,
     [DataInputKey.TICK_LOGS], "cashflow_forensics.md", True, ReportTier.PRO),
    (9, "Monte Carlo Results & Distribution Analysis", 5,
     [DataInputKey.MC_AGGREGATES], "monte_carlo.md", True, ReportTier.FREE),
    (10, "Kill-Vector Autopsy", 4,
     [DataInputKey.MC_AGGREGATES, DataInputKey.TICK_LOGS],
     "kill_vector_autopsy.md", True, ReportTier.PRO),
    (11, "Architectural Weaknesses Register", 3,
     [DataInputKey.FORGE_VULNERABILITIES],
     "weaknesses_register.md", True, ReportTier.FREE),
    (12, "Stress-Test Timeline & Decision Review", 4,
     [DataInputKey.EVENTS_DECISIONS, DataInputKey.CHRONICLE],
     "stress_test_review.md", True, ReportTier.PRO),
    (13, "Counter-Factual Analysis", 3,
     [DataInputKey.OPTIMIZATION_ENTRIES], "counterfactual.md", True, ReportTier.PRO),
    (14, "Sensitivity Analysis & Tornado Chart", 3,
     [DataInputKey.MC_AGGREGATES, DataInputKey.ENGINE_CONFIG],
     "sensitivity.md", True, ReportTier.ENTERPRISE),
    (15, "Cohort Benchmark", 3,
     [DataInputKey.MC_AGGREGATES], "cohort_benchmark.md", True, ReportTier.ENTERPRISE),
    (16, "Risk Register & Mitigation Matrix", 3,
     [DataInputKey.FORGE_VULNERABILITIES, DataInputKey.MC_AGGREGATES],
     "risk_register.md", True, ReportTier.ENTERPRISE),
    (17, "Prescriptive Optimization Plan", 3,
     [DataInputKey.OPTIMIZATION_ENTRIES], "optimization_plan.md", True, ReportTier.ENTERPRISE),
    (18, "90-Day Action Plan", 2,
     [DataInputKey.FORGE_VULNERABILITIES, DataInputKey.OPTIMIZATION_ENTRIES],
     "action_plan.md", True, ReportTier.ENTERPRISE),
    (19, "Scenario Comparison Appendix", 3,
     [DataInputKey.COMPARISON_DELTAS], "scenario_comparison.md", True, ReportTier.ENTERPRISE),
    (20, "Full KPI Appendix", 5,
     [DataInputKey.TICK_LOGS], "kpi_appendix.md", False, ReportTier.ENTERPRISE),
    (21, "Glossary, Data Dictionary & Reproducibility", 2,
     [DataInputKey.RUN_METADATA, DataInputKey.ENGINE_CONFIG],
     "glossary.md", False, ReportTier.ENTERPRISE),
]

# Full 21-section Enterprise manifest
FULL_MANIFEST = ReportManifest(
    name="Investor-Grade Resilience Audit",
    report_type="resilience_audit",
    tier=ReportTier.ENTERPRISE,
    sections=[
        SectionDef(
            section_number=num,
            title=title,
            page_budget=pages,
            data_inputs=inputs,
            prompt_template=template,
            ai_generated=ai_generated,
            tier_minimum=tier_minimum,
        )
        for (num, title, pages, inputs, template, ai_generated, tier_minimum) in _SECTIONS
    ],
)

MANIFEST_REGISTRY: dict[str, ReportManifest] = {
    "resilience_audit": FULL_MANIFEST,
    "lender_report": LENDER_MANIFEST,
}


def get_manifest(report_type: str) -> ReportManifest:
    if report_type not in MANIFEST_REGISTRY:
        raise KeyError(f"Unknown report type: {report_type}")
    return MANIFEST_REGISTRY[report_type]

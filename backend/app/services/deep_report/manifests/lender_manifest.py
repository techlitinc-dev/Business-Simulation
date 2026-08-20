from app.services.deep_report.manifest import (
    DataInputKey,
    ReportManifest,
    ReportTier,
    SectionDef,
)

# (section_number, title, page_budget, data_inputs, prompt_template, ai_generated, tier_minimum)
_SECTIONS: list[tuple[int, str, int, list[DataInputKey], str, bool, ReportTier]] = [
    (1, "Cover & Executive Summary", 3,
     [DataInputKey.RUN_METADATA, DataInputKey.MC_AGGREGATES],
     "lender_cover.md", False, ReportTier.PRO),
    (2, "Cash Flow Stability Analysis", 5,
     [DataInputKey.TICK_LOGS], "lender_cashflow.md", True, ReportTier.PRO),
    (3, "Debt Service Coverage Assessment", 4,
     [DataInputKey.TICK_LOGS, DataInputKey.ENGINE_CONFIG],
     "lender_dscr.md", True, ReportTier.PRO),
    (4, "Downside Protection & Stress Scenarios", 5,
     [DataInputKey.MC_AGGREGATES, DataInputKey.TICK_LOGS],
     "lender_downside.md", True, ReportTier.PRO),
    (5, "Collateral & Business Asset Summary", 3,
     [DataInputKey.BLUEPRINT], "lender_collateral.md", True, ReportTier.PRO),
    (6, "Repayment Capacity Analysis", 4,
     [DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES],
     "lender_repayment.md", True, ReportTier.PRO),
    (7, "Risk Register & Covenants", 3,
     [DataInputKey.FORGE_VULNERABILITIES], "lender_risk.md", True, ReportTier.PRO),
    (8, "Conclusion & Lender Recommendation", 2,
     [DataInputKey.MC_AGGREGATES, DataInputKey.RUN_METADATA],
     "lender_conclusion.md", True, ReportTier.PRO),
]

LENDER_MANIFEST = ReportManifest(
    name="Loan Readiness Assessment",
    report_type="lender_report",
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

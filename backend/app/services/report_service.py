"""Resilience audit generation + run comparison (T30/T33).

Deterministic Format C sections (SURVIVAL METRICS, ARCHITECTURAL WEAKNESSES)
are computed here from the Monte Carlo aggregation persisted by T27. T31 fills
the AI sections; compare_runs (T33) reuses the same helpers.
"""

from __future__ import annotations

import statistics
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError
from app.models.blueprint import BlueprintVersion
from app.models.report import Report
from app.models.simulation import SimulationRun
from app.schemas.report import (
    ComparisonDeltas,
    ComparisonResponse,
    CounterFactualInsight,
    KillVector,
    KillVectorChange,
    OptimizationEntry,
    ReportContent,
    ReportResponse,
    RunSummary,
    SurvivalMetrics,
    Weakness,
)

#: Severity ordering for ranked weaknesses (spec §10).
SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

REPORT_TYPE = "resilience_audit"

_KILL_VECTOR_LABELS: dict[str, str] = {
    "market": "Market pressure death",
    "operational": "Operational failure death",
    "financial": "Cash flow death",
    "black_swan": "Black-swan event death",
    "internal": "Internal dysfunction death",
    "natural_causes": "Cash flow death without a triggering hurdle",
}


def _normalise_kill_vector(cause: str) -> str:
    if cause in _KILL_VECTOR_LABELS:
        return cause
    if cause in ("financial", "natural_causes"):
        return cause
    return cause


def survival_metrics_from_result(result: dict[str, Any]) -> SurvivalMetrics:
    """Deterministic survival metrics from the T27 MonteCarloResult JSON."""
    n_runs = int(result.get("n_runs", 0))
    runs_summary = result.get("runs_summary", [])
    runs_survived = sum(1 for r in runs_summary if r.get("survived"))
    lifespans = [int(r.get("lifespan_months", 0)) for r in runs_summary]
    kill_vectors = result.get("kill_vectors", {}) or {}

    total_failures = max(1, n_runs - runs_survived)
    vectors = [
        KillVector(
            cause=_normalise_kill_vector(cause),
            count=int(count),
            pct=round(int(count) / total_failures * 100, 1),
        )
        for cause, count in sorted(
            kill_vectors.items(), key=lambda kv: (-kv[1], kv[0])
        )
    ]

    return SurvivalMetrics(
        survival_rate=round(runs_survived / n_runs, 4) if n_runs else 0.0,
        runs_total=n_runs,
        runs_survived=runs_survived,
        median_lifespan_months=int(statistics.median(lifespans)) if lifespans else 0,
        kill_vectors=vectors,
    )


def survival_metrics_from_baseline_result(result: dict[str, Any]) -> SurvivalMetrics:
    """Survival metrics for a single baseline/stress run outcome.

    Dead (bankrupt) runs persist a compact ``build_baseline_result`` payload
    rather than a Monte Carlo aggregation, so synthesise one-run metrics from
    it so the resilience audit still renders (T30).
    """
    survived = bool(result.get("survived", False))
    months = int(result.get("months_survived", 0))
    return SurvivalMetrics(
        survival_rate=1.0 if survived else 0.0,
        runs_total=1,
        runs_survived=1 if survived else 0,
        median_lifespan_months=months,
        kill_vectors=[
            KillVector(
                cause="financial" if not survived else "natural_causes",
                count=0 if survived else 1,
                pct=100.0 if not survived else 0.0,
            )
        ]
        if not survived
        else [],
    )


def _weaknesses_from_vectors(
    metrics: SurvivalMetrics, vulnerabilities: list[dict[str, Any]]
) -> list[Weakness]:
    """Rank weaknesses: engine kill vectors + Format A vulnerabilities."""
    weaknesses: list[Weakness] = []
    failures = max(1, metrics.runs_total - metrics.runs_survived)

    for kv in metrics.kill_vectors:
        label = _KILL_VECTOR_LABELS.get(kv.cause, kv.cause)
        if kv.pct >= 40.0:
            severity = "CRITICAL"
        elif kv.pct >= 20.0:
            severity = "HIGH"
        elif kv.pct >= 5.0:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        weaknesses.append(
            Weakness(
                severity=severity,
                title=f"{label} ({kv.cause})",
                detail=(
                    f"Caused {kv.count} of {failures} failures "
                    f"({kv.pct}% of failures)."
                ),
            )
        )

    for vuln in vulnerabilities:
        sev = str(vuln.get("severity", "medium")).upper()
        weaknesses.append(
            Weakness(
                severity=sev if sev in SEVERITY_RANK else "MEDIUM",
                title=str(vuln.get("description", "Vulnerability")),
                detail=str(vuln.get("mitigation_suggestion", "")),
            )
        )

    weaknesses.sort(key=lambda w: SEVERITY_RANK.get(w.severity, 9))
    return weaknesses


def render_survival_markdown(metrics: SurvivalMetrics) -> str:
    """Render the deterministic SURVIVAL METRICS section (Format C)."""
    pct = round(metrics.survival_rate * 100)
    failed = metrics.runs_total - metrics.runs_survived
    primary = metrics.kill_vectors[0] if metrics.kill_vectors else None
    primary_line = (
        f"- **Primary Kill Vector:** {_KILL_VECTOR_LABELS.get(primary.cause, primary.cause)} "
        f"({primary.pct}% of failures)"
        if primary
        else "- **Primary Kill Vector:** none — no failures recorded"
    )
    return (
        "### SURVIVAL METRICS\n"
        f"- **Survival Rate:** {pct}% (Failed in {failed} of "
        f"{metrics.runs_total} Monte Carlo runs)\n"
        f"- **Median Lifespan:** {metrics.median_lifespan_months} months\n"
        f"{primary_line}\n"
    )


def render_weakness_markdown(weaknesses: list[Weakness]) -> str:
    lines = ["### ARCHITECTURAL WEAKNESSES"]
    for i, w in enumerate(weaknesses, start=1):
        lines.append(f"{i}. **{w.severity}:** {w.title} — {w.detail}")
    return "\n".join(lines) + "\n"


def build_report_content(
    metrics: SurvivalMetrics,
    vulnerabilities: list[dict[str, Any]],
    *,
    blueprint_version: int = 1,
    resilience_score: int = 0,
    optimizations: list[Any] | None = None,
    counter_factual_insight: str = "",
    tweak_deltas: list[Any] | None = None,
) -> ReportContent:
    """Assemble the full ReportContent JSON (T30 core + T31 enrichment)."""
    weaknesses = _weaknesses_from_vectors(metrics, vulnerabilities)
    content = ReportContent(
        survival=metrics,
        weaknesses=weaknesses,
        blueprint_version=blueprint_version,
        resilience_score=resilience_score,
        counter_factual={"text": counter_factual_insight, "deltas": []},
    )
    if optimizations is not None:
        content.optimizations = optimizations
    if tweak_deltas:
        content.counter_factual.deltas = [d.model_dump() for d in tweak_deltas]
    return content


def render_full_markdown(
    content: ReportContent,
    *,
    ai_optimizations_md: str = "",
    counter_factual_md: str = "",
) -> str:
    """Render all Format C sections to markdown."""
    sections = [
        render_survival_markdown(content.survival),
        render_weakness_markdown(content.weaknesses),
    ]
    if content.optimizations and ai_optimizations_md:
        sections.append(ai_optimizations_md)
    if content.counter_factual.text and counter_factual_md:
        sections.append(counter_factual_md)
    return "\n".join(sections)


async def get_run_report(
    db: AsyncSession, *, workspace_id: Any, run_id: str
) -> Report | None:
    """Return the stored report for a run (None if not generated yet)."""
    row = await db.scalar(
        select(Report)
        .join(SimulationRun, SimulationRun.id == Report.run_id)
        .where(
            Report.run_id == run_id,
            SimulationRun.workspace_id == workspace_id,
        )
    )
    return row


async def _require_report(
    db: AsyncSession, *, workspace_id: Any, run_id: str
) -> Report:
    report = await get_run_report(db, workspace_id=workspace_id, run_id=run_id)
    if report is None:
        raise DomainError(status_code=404, detail="Report not found")
    return report


async def generate_resilience_audit(
    db: AsyncSession, *, workspace_id: Any, run_id: str
) -> Report:
    """Generate + persist the resilience audit on first call (idempotent)."""
    existing = await get_run_report(db, workspace_id=workspace_id, run_id=run_id)
    if existing is not None:
        return existing

    run = await db.scalar(
        select(SimulationRun).where(
            SimulationRun.id == run_id,
            SimulationRun.workspace_id == workspace_id,
        )
    )
    if run is None:
        raise DomainError(status_code=404, detail="Simulation run not found")
    # A dead (bankrupt) run has a terminal outcome worth auditing too; it
    # persists a baseline-shaped result with resilience data (T25/T30).
    if run.status not in ("completed", "dead"):
        raise DomainError(
            status_code=409, detail="Report requires a completed run"
        )
    if run.mode not in ("monte_carlo", "stress"):
        raise DomainError(
            status_code=409, detail="Report requires a monte_carlo or stress run"
        )

    result = run.result or {}
    if "n_runs" in result or "runs_summary" in result:
        metrics = survival_metrics_from_result(result)
    else:
        metrics = survival_metrics_from_baseline_result(result)

    version = await db.get(BlueprintVersion, run.blueprint_version_id)
    vulnerabilities = list(version.vulnerabilities or []) if version else []
    blueprint_version = version.version if version else 1
    resilience_score = int(result.get("resilience_score", 0))
    if not resilience_score and metrics.runs_total:
        resilience_score = int(round(metrics.survival_rate * 100))

    content = build_report_content(
        metrics,
        vulnerabilities,
        blueprint_version=blueprint_version,
        resilience_score=resilience_score,
    )
    report = Report(
        run_id=run.id,
        type=REPORT_TYPE,
        content_md=render_full_markdown(content),
        content_json=content.model_dump(mode="json"),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # T31: enrich with counter-factual deltas + AI post-mortem (best-effort;
    # never fails the report when the LLM is unavailable).
    try:
        await _enrich_with_optimizations(
            db, report, run, version, metrics, content
        )
    except Exception:  # noqa: BLE001 - enrichment is additive
        await db.refresh(report)
    return report


async def _enrich_with_optimizations(
    db: AsyncSession,
    report: Report,
    run: SimulationRun,
    version: BlueprintVersion | None,
    metrics: SurvivalMetrics,
    content: ReportContent,
) -> None:
    """Run the counter-factual engine deltas + AI post-mortem, persist them."""
    from app.agents.llm.factory import get_llm_provider
    from app.agents.post_mortem import PostMortemAgent
    from app.core.config import get_settings
    from app.services import optimization_service

    payload = dict(version.payload) if version else {}
    if not payload:
        return
    deltas = optimization_service.measure_all_tweaks(
        payload, n_runs=20, seed=run.seed or 42
    )

    provider = get_llm_provider(get_settings())
    agent = PostMortemAgent(provider)
    output = await agent.generate(metrics, deltas, payload)

    optimizations: list[OptimizationEntry] = []
    for item in output.optimizations:
        tweak_key = str(item.get("tweak_key", ""))
        delta = next((d for d in deltas if d.tweak_key == tweak_key), None)
        optimizations.append(
            OptimizationEntry(
                tweak_key=tweak_key,
                recommendation=str(item.get("recommendation", "")),
                implementation_cost=str(item.get("implementation_cost", "Medium")),
                impact_on_survival_rate=delta.delta_pp if delta else 0.0,
                trade_off=str(item.get("trade_off", "")),
            )
        )

    content.optimizations = optimizations
    content.counter_factual = CounterFactualInsight(
        text=output.counter_factual_insight,
        deltas=[d.model_dump() for d in deltas],
    )
    report.content_json = content.model_dump(mode="json")
    report.content_md = render_full_markdown(
        content,
        ai_optimizations_md=_render_optimizations_md(optimizations),
        counter_factual_md=(
            f"### COUNTER-FACTUAL INSIGHT\n{output.counter_factual_insight}\n"
            if output.counter_factual_insight
            else ""
        ),
    )
    await db.commit()
    await db.refresh(report)


async def enrich_report(
    db: AsyncSession,
    *,
    workspace_id: Any,
    run_id: str,
    optimizations: list[Any],
    tweak_deltas: list[Any],
    counter_factual_insight: str,
) -> Report:
    """Enrich an existing report with T31 sections (404 if none yet)."""
    report = await _require_report(db, workspace_id=workspace_id, run_id=run_id)
    content = ReportContent.model_validate(report.content_json)
    content.optimizations = optimizations
    content.counter_factual = CounterFactualInsight(
        text=counter_factual_insight,
        deltas=[d.model_dump() for d in tweak_deltas],
    )
    report.content_json = content.model_dump(mode="json")
    report.content_md = render_full_markdown(
        content,
        ai_optimizations_md=_render_optimizations_md(content.optimizations),
        counter_factual_md=(
            f"### COUNTER-FACTUAL INSIGHT\n{counter_factual_insight}\n"
            if counter_factual_insight
            else ""
        ),
    )
    await db.commit()
    await db.refresh(report)
    return report


def _render_optimizations_md(
    optimizations: list[Any],
) -> str:
    """Render the Format C optimization table (engine-measured impact)."""
    lines = [
        "### AI-GENERATED OPTIMIZATIONS",
        "",
        "| Recommendation | Implementation Cost | Impact on Survival Rate | Trade-off |",
        "| --- | --- | --- | --- |",
    ]
    for opt in optimizations:
        if isinstance(opt, dict):
            impact = float(opt.get("impact_on_survival_rate", 0.0))
            recommendation = str(opt.get("recommendation", ""))
            cost = str(opt.get("implementation_cost", ""))
            trade_off = str(opt.get("trade_off", ""))
        else:
            impact = float(opt.impact_on_survival_rate)
            recommendation = str(opt.recommendation)
            cost = str(opt.implementation_cost)
            trade_off = str(opt.trade_off)
        impact_str = f"{impact:+.1f}pp"
        lines.append(
            f"| {recommendation} | {cost} | {impact_str} | {trade_off} |"
        )
    return "\n".join(lines) + "\n"


def report_response(report: Report) -> ReportResponse:
    return ReportResponse.model_validate(report)


# ---------------------------------------------------------------------------
# T33 — run comparison
# ---------------------------------------------------------------------------


def _run_summary(
    run: SimulationRun,
    metrics: SurvivalMetrics,
    blueprint_version: int,
    resilience_score: int,
) -> RunSummary:
    top = metrics.kill_vectors[0] if metrics.kill_vectors else None
    return RunSummary(
        run_id=run.id,
        blueprint_version_id=run.blueprint_version_id,
        blueprint_version=blueprint_version,
        survival_rate=metrics.survival_rate,
        median_lifespan_months=metrics.median_lifespan_months,
        resilience_score=resilience_score,
        top_kill_vector=top.cause if top else "none",
    )


async def compare_runs(
    db: AsyncSession, *, workspace_id: Any, run_a_id: str, run_b_id: str
) -> ComparisonResponse:
    """Compare two completed runs: deltas + verdict + kill-vector changes."""
    runs: list[SimulationRun] = []
    for run_id in (run_a_id, run_b_id):
        run = await db.scalar(
            select(SimulationRun).where(
                SimulationRun.id == run_id,
                SimulationRun.workspace_id == workspace_id,
            )
        )
        if run is None:
            raise DomainError(status_code=404, detail="Simulation run not found")
        # Dead (bankrupt) runs are terminal and comparable, like reports.
        if run.status not in ("completed", "dead"):
            raise DomainError(
                status_code=409, detail="Comparison requires completed runs"
            )
        runs.append(run)

    run_a, run_b = runs
    summaries: list[RunSummary] = []
    vectors_by_run: list[dict[str, float]] = []

    for run in runs:
        result = run.result or {}
        if "n_runs" in result or "runs_summary" in result:
            metrics = survival_metrics_from_result(result)
        else:
            metrics = survival_metrics_from_baseline_result(result)
        version = await db.get(BlueprintVersion, run.blueprint_version_id)
        resilience_score = int((run.result or {}).get("resilience_score", 0))
        if not resilience_score and metrics.runs_total:
            resilience_score = int(round(metrics.survival_rate * 100))
        summaries.append(
            _run_summary(
                run, metrics, version.version if version else 1, resilience_score
            )
        )
        vectors_by_run.append({kv.cause: kv.pct for kv in metrics.kill_vectors})

    summary_a, summary_b = summaries
    vectors_a, vectors_b = vectors_by_run

    survival_pp = round((summary_b.survival_rate - summary_a.survival_rate) * 100, 1)
    deltas = ComparisonDeltas(
        survival_rate_pp=survival_pp,
        median_lifespan_months=(
            summary_b.median_lifespan_months - summary_a.median_lifespan_months
        ),
        resilience_score_pp=(
            summary_b.resilience_score - summary_a.resilience_score
        ),
    )

    causes = set(vectors_a) | set(vectors_b)
    changes = [
        KillVectorChange(
            cause=cause,
            pct_a=vectors_a.get(cause, 0.0),
            pct_b=vectors_b.get(cause, 0.0),
            delta_pp=round(vectors_b.get(cause, 0.0) - vectors_a.get(cause, 0.0), 1),
        )
        for cause in causes
    ]
    changes.sort(key=lambda c: abs(c.delta_pp), reverse=True)

    if survival_pp > 1:
        verdict: Literal["improved", "regressed", "unchanged"] = "improved"
    elif survival_pp < -1:
        verdict = "regressed"
    else:
        verdict = "unchanged"

    return ComparisonResponse(
        a=summary_a,
        b=summary_b,
        deltas=deltas,
        kill_vector_changes=changes,
        verdict=verdict,
    )

# Features Roadmap — The Forge: From Simulation Tool to Million-Dollar SaaS

Status of the platform today (per `tasks/plan.md`, `tasks/todo.md`, `tasks/progress.md`): Phases 0–9 are complete. The deterministic engine, AI Cortex (Forge review, Hurdle Generator, Strategist, Post-Mortem, Chronicle, Ghost), Monte Carlo worker, resilience reports with PDF export, marketplace, leaderboards, Stripe billing, usage metering, enterprise API keys, and admin dashboard all exist and are tested.

This document proposes the **next generation of features** that turn The Forge from a simulation tool into a category-defining, seven-figure SaaS. Two hard constraints govern everything below:

1. **No ML training, ever.** Zero fine-tuning, zero custom model weights, zero embedding pipelines. All intelligence comes from the **DeepSeek API key** through the existing OpenAI-compatible provider abstraction (`app/agents/llm/`) and the structured-output bridge (`app/agents/bridge.py`). DeepSeek's pricing makes even report-scale generation economically trivial, and the existing `MockProvider` keeps every feature dev/testable without a key.
2. **The deterministic engine stays the source of truth.** The LLM writes narrative, judgment, and recommendations. Every number in every report, chart, and benchmark comes from `app/engine/` or from data the engine produced. The AI never invents financials.

---

## Feature Pack 1 — Deep-Dive Report Engine (the flagship)

**ID:** F-01 · **Tier gating:** depth scales by plan (see below) · **Builds on:** `report_service.py`, `optimization_service.py`, `post_mortem.py`, `app/utils/pdf.py` (WeasyPrint), Celery workers.

The single most monetizable upgrade. Today's resilience audit is a few pages of survival metrics, weaknesses, and optimizations. The Deep-Dive Report Engine generates **board-grade documents up to ~70 pages**, produced section-by-section so DeepSeek's output limits are never hit and every section is independently validated and retryable.

### How it works

- A **report manifest** (Pydantic schema) defines the sections included, their target page budget, required data inputs, and the prompt template for each. Different report types (Resilience Audit, Investor Report, Lender Report, Internal Strategy Review) reuse the same pipeline with different manifests.
- A Celery job (`workers/report_job.py`) walks the manifest sequentially: for each section it assembles a **deterministic data pack** (engine KPIs, tick logs, Monte Carlo aggregates, comparison deltas, vulnerability lists) and asks DeepSeek for structured markdown for that section only. The bridge validates the section against its schema; invalid output triggers the existing repair-retry loop; a final fallback renders a data-only section so the report never fails.
- Charts are rendered server-side from tick/KPI data (matplotlib or pre-rendered SVG) and embedded as images — deterministic, no LLM involvement.
- Progress is published to Redis and streamed over the existing WebSocket channel, so the UI shows "Writing section 14 of 38…" live.
- Final assembly: markdown → styled PDF via WeasyPrint with cover page, table of contents, page numbers, headers/footers, and workspace branding. DOCX export via `pandoc` or `python-docx` as a follow-up.
- Token usage per section is metered through the existing bridge `on_response` hook — reports are a premium-metered action.

### Reference table of contents (full 70-page Investor-Grade Audit)

| # | Section | Pages | Primary source |
|---|---|---|---|
| 1 | Cover, disclaimer, table of contents | 3 | Template |
| 2 | Executive summary (1-page brief + verdict) | 2 | DeepSeek over full data pack |
| 3 | Business blueprint overview (model, ICP, pricing, GTM) | 3 | Blueprint payload + Forge review |
| 4 | Methodology & simulation assumptions | 2 | Engine config (deterministic) |
| 5 | Market & demand dynamics analysis | 4 | Engine market module + DeepSeek narrative |
| 6 | 24-month financial narrative (month-by-month story) | 6 | Tick logs + DeepSeek |
| 7 | Unit economics deep dive (LTV, CAC, payback, NRR, margins) | 4 | Engine financials |
| 8 | Cash flow & runway forensics | 3 | Tick logs |
| 9 | Monte Carlo results & distribution analysis | 5 | MC aggregates + histograms |
| 10 | Kill-vector autopsy (top failure modes, month-of-death analysis) | 4 | MC result + DeepSeek |
| 11 | Architectural weaknesses register (severity-ranked) | 3 | Forge vulnerabilities |
| 12 | Stress-test timeline & decision review | 4 | Events + decisions + chronicle |
| 13 | Counter-factual analysis ("if you had decided otherwise") | 3 | Optimization service |
| 14 | Sensitivity analysis & tornado chart | 3 | Parameter sweeps (F-06) |
| 15 | Cohort benchmark (percentile vs. anonymized peers) | 3 | Benchmark service (F-05) |
| 16 | Risk register & mitigation matrix | 3 | DeepSeek over weaknesses |
| 17 | Prescriptive optimization plan (ranked, engine-measured impact) | 3 | Optimization service |
| 18 | 90-day action plan | 2 | DeepSeek |
| 19 | Scenario comparison appendix (V1 vs V2) | 3 | Comparison service |
| 20 | Full KPI appendix (all ticks, all charts) | 5 | Tick logs |
| 21 | Glossary, data dictionary, reproducibility (seeds, versions) | 2 | Template + run metadata |

**Total ≈ 70 pages.** Tier mapping: Free = 5-page summary (sections 2, 9, 11), Pro = 25-page standard audit (sections 1–13), Enterprise = full 70-page manifest + custom section insertion + white-label branding.

### Why it sells

A 70-page investor-grade simulation audit is a deliverable founders would pay $200–$500 for *once*; bundling it into Pro/Enterprise subscriptions is the clearest path to $1M ARR. It is also the strongest enterprise/VC-sales artifact: accelerators buy seats so every portfolio company produces one.

---

## Feature Pack 2 — AI Advisory Board & Copilot

**ID:** F-02 · **Tier:** Pro+ · **Builds on:** `app/agents/` (forge, ghost, strategist, chronicle), bridge.

- **Advisory Board personas.** DeepSeek plays a panel of fixed personas — skeptical CFO, growth-obsessed CMO, risk auditor, seasoned operator — each reviewing the blueprint or run from their lens. Personas are prompt templates in `agents/prompts/` (same pattern as `ghost_personality.md`), outputs are bridge-validated and merged into one review with points of agreement/conflict. This is the Forge review, multiplied.
- **Ask-Your-Business copilot.** A chat panel where users ask questions about any run ("why did cash dip in month 9?", "what kills me most often?"). The backend retrieves the run's data pack + chronicle and answers through DeepSeek with strict grounding: every numeric claim is checked against engine data before display (hallucinated numbers are replaced or flagged). Chat is the stickiest retention feature SaaS products have.
- **Decision coach.** In the War Room, a "second opinion" button: DeepSeek critiques the option the user is *about* to pick against the strategist's projections.

---

## Feature Pack 3 — Investor & Lender Toolkit

**ID:** F-03 · **Tier:** Pro (one-pager) / Enterprise (full data room) · **Builds on:** F-01 pipeline, share links (T32/T44).

- **One-page investment teaser** auto-generated from a run: problem, model, simulated survival, key metrics, ask.
- **Pitch-deck outline generator** — 10–12 slide markdown outline grounded in simulation data, exportable.
- **Lender/loan-readiness report** — a manifest variant of F-01 emphasizing cash-flow stability, downside protection, and debt-service coverage from the engine.
- **Investor data room** — a shareable, expiring, view-tracked link bundling the deep-dive PDF, raw KPI exports (CSV), and methodology notes. Extends the existing signed share-token mechanism.

---

## Feature Pack 4 — Living Blueprint & Plan-vs-Actuals

**ID:** F-04 · **Tier:** Pro+ · **Builds on:** blueprint versioning (T17), simulation service.

The feature that converts one-time users into permanent subscribers.

- **Actuals import.** Users upload monthly actuals (CSV) or connect a source later; the service maps them onto blueprint fields (revenue, churn, CAC, headcount, cash).
- **Plan-vs-simulation variance report.** Each month, the engine re-baselines the blueprint from actuals and re-runs the forecast; a DeepSeek narrative explains the variance and what changed in the outlook ("your simulated 24-month survival dropped from 71% to 58% — here's why").
- **Drift alerts.** Scheduled (celery-beat) re-simulation; if resilience score drops past a threshold, the user gets an email/Slack/notification-center alert with a one-click deep-dive.
- **Rolling forecast.** The blueprint becomes a living document — each month appends an actuals version and a new forecast run, giving a continuous audit trail investors love.

---

## Feature Pack 5 — Cohort Benchmarks

**ID:** F-05 · **Tier:** Pro (view) / Enterprise (export) · **Builds on:** existing run data, no LLM needed.

- Anonymized, opt-in aggregation of completed runs: survival-rate percentiles, median runway, typical kill vectors, resilience-score distribution — sliced by industry and stage (data from onboarding, T36).
- Every report (F-01) and the dashboard gauge get a "vs. peers" line: "Your resilience score of 64 puts you in the 58th percentile of B2B SaaS simulations."
- 100% deterministic aggregates — cheap to compute, high perceived value, and a network-effects moat: the more users simulate, the better the benchmarks.

---

## Feature Pack 6 — What-If Lab & Sensitivity Sweeps

**ID:** F-06 · **Tier:** Pro+ · **Builds on:** engine purity (Phase 2), Monte Carlo worker (T27).

- **Interactive parameter sweeps.** User picks a parameter (price, churn, CAC, salary, ad budget) and a range; the engine runs a grid of seeded simulations (still <100ms each) and renders heatmaps and tornado charts. No LLM at all — pure engine, near-free to run.
- **One-click "save as blueprint version"** from any point on the grid.
- **Break-even finder.** Engine binary-searches the parameter value where survival flips — "your model survives only if monthly churn stays below 6.3%." These exact thresholds are the most quotable numbers in every F-01 report.

---

## Feature Pack 7 — Decision Journal, Playbooks & Learning Loop

**ID:** F-07 · **Tier:** all paid tiers · **Builds on:** decisions table, chronicle, post-mortem.

- **Decision journal.** Every War Room decision is logged with the strategist's projection and the actual outcome; the journal scores the user's decision quality over time ("you beat the AI's recommended path in 4 of 7 crises").
- **Playbook library.** Post-mortems distilled into reusable playbooks ("surviving a demand shock as a subscription business") — DeepSeek writes them, engine data anchors them. Playbooks are publishable to the marketplace, extending T42 beyond scenarios.
- **Team learning.** Workspaces get a shared journal — accelerators and consultants use this as their teaching artifact.

---

## Feature Pack 8 — Collaboration & Workflow

**ID:** F-08 · **Tier:** Pro (comments) / Enterprise (approvals, audit) · **Builds on:** workspace RBAC (T08), notifications (T37), audit log (T49).

- **Comments & annotations** on blueprints, runs, hurdles, and report sections, with @mentions and email digests.
- **Review & approval workflow.** A blueprint or report can be submitted for approval; approvers sign off with a recorded verdict — essential for consultants delivering reports to clients.
- **Guest/viewer role.** Read-only seats for investors and clients, so the report isn't shared as a loose PDF but as a controlled, revocable view.
- **Real-time presence** in the Runner and War Room (who's watching this run), riding the existing WebSocket infra.

---

## Feature Pack 9 — Integrations & Distribution

**ID:** F-09 · **Tier:** Enterprise mostly · **Builds on:** enterprise API keys (T45), webhooks.

- **Slack + email alerts** for run completion, drift alerts (F-04), and hurdle events during live runs.
- **Outbound webhooks** (run.completed, report.ready, score.dropped) with HMAC signatures — turns The Forge into infrastructure other tools build on.
- **CSV/Excel export everywhere** (ticks, KPIs, MC distributions, report data packs).
- **Public REST + embed SDK.** The enterprise API (T45) is extended with a report-generation endpoint and an embeddable "resilience badge"/score widget customers put in their own dashboards and data rooms.
- **White-label mode (Enterprise).** Custom logo/colors/domain on reports and shared pages — consultancies resell The Forge as their own "AI business audit."

---

## Feature Pack 10 — Portfolio & Cohort Mode (the B2B2C wedge)

**ID:** F-10 · **Tier:** Enterprise / new "Portfolio" plan · **Builds on:** multi-tenant workspaces, admin aggregates.

Aimed at VCs, accelerators, banks, and universities — the highest-ACV customers.

- **Portfolio dashboard.** One org manages N company workspaces: resilience scores, survival rates, and drift alerts across the whole portfolio on one screen.
- **Cohort comparison.** Rank companies in a batch against each other (anonymized option for classrooms).
- **Standardized audit program.** The portfolio admin mandates a report manifest (F-01) and re-simulation cadence; compliance is tracked automatically.
- **Bulk provisioning.** SSO (SAML/OIDC) and SCIM-lite seat management for enterprise rollouts.

---

## Feature Pack 11 — Vertical Industry Packs

**ID:** F-11 · **Tier:** paid add-on or Pro+ · **Builds on:** marketplace scenarios (T42), engine market module.

- Curated packs per vertical — SaaS, e-commerce/DTC, restaurant, agency/consulting, marketplace, hardware — each shipping: pre-tuned engine market parameters (seasonality curves, elasticity ranges), a blueprint template, 10–20 vertical-specific hurdle libraries, and a report manifest variant with industry KPIs (e.g., table turns for restaurants, GMV take-rate for marketplaces).
- DeepSeek generates the vertical hurdle libraries and report copy; all parameters are validated and clamped by the engine as usual.
- Sold as add-ons or used to justify tier upgrades; also the best SEO/content marketing surface ("simulate your restaurant before you sign the lease").

---

## Feature Pack 12 — Trust, Quality & Platform Depth

**ID:** F-12 · **Tier:** platform-wide · **Builds on:** Phase 9 hardening.

- **Report quality assurance loop.** Every DeepSeek-generated section passes a deterministic linter: numeric claims cross-checked against the data pack, banned-phrase filter, length/page-budget enforcement. Failed sections auto-regenerate. This is what makes 70-page AI output trustworthy enough to sell.
- **Model routing.** Env-configurable per-task model selection (e.g., `deepseek-chat` for bulk narrative, a reasoning model for the executive summary and counter-factuals) — zero code changes thanks to the provider factory; adds only per-call config.
- **Cost guardrails.** Per-report and per-month token budgets per workspace, hard-capped by the existing metering service; cached data packs so re-rendering a report doesn't re-pay for identical sections.
- **Localization.** Report generation in multiple languages (DeepSeek handles this natively) + multi-currency display formatting — pure prompt + formatting work.
- **Gamification.** Achievements ("survived 3 demand shocks"), a certification ("Forge-Validated Business — top decile resilience"), and seasonal leaderboard events to drive organic sharing of public reports.

---

## Monetization map (suggested)

| Plan | Price anchor | Unlocks |
|---|---|---|
| Free | $0 | 3 runs/mo, 5-page summary report, marketplace browse |
| Pro | $49–79/mo | 25-page standard audit, copilot chat, What-If Lab, benchmarks view, decision journal, drift alerts, comments |
| Business | $199–299/mo | 70-page deep dive, advisory board, investor toolkit, plan-vs-actuals, playbooks, priority queue |
| Enterprise / Portfolio | $1k–5k/mo | White-label, data room, portfolio/cohort mode, SSO, API + webhooks, custom manifests, dedicated limits |
| Add-ons | per unit | Extra deep-dive reports ($99 one-off), industry packs ($19–49), extra Monte Carlo volume |

The economics work *because* of the constraints: DeepSeek token costs for a full 70-page report are on the order of cents, the engine is pure Python (free compute), and metering/billing/paywalls already exist from Phase 8.

## Suggested build order

1. **F-01 Deep-Dive Report Engine** (with F-12 QA loop) — the flagship revenue feature; everything else references it.
2. **F-06 What-If Lab** — cheap (no LLM), feeds sections 14/16 of the report, huge demo value.
3. **F-04 Living Blueprint & drift alerts** — converts trials into forever-subscribers.
4. **F-02 Copilot chat** — retention and daily-active usage.
5. **F-05 Benchmarks** — compounds with user growth.
6. **F-03 Investor toolkit** — monetizes the report pipeline further.
7. **F-10 Portfolio mode** — first enterprise/contracts revenue.
8. F-07, F-08, F-09, F-11, remaining F-12 items — depth and expansion revenue.

Every item above stays inside the current architecture: new agents are prompt templates + bridge-validated schemas, new heavy jobs are Celery tasks with Redis progress, new surfaces are feature folders under `frontend/src/features/`, and plan gating rides the existing metering service. Nothing requires training a model — only a DeepSeek API key.

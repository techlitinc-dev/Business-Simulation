# Phase 6 — Reports & Optimization

Turn completed Monte Carlo runs into the Format C Resilience Audit: deterministic survival metrics + AI-ranked weaknesses, counter-factual "what-if" re-runs with optimization recommendations, a report UI with Markdown/PDF export and shareable public links, and a V1-vs-V2 comparison endpoint + diff view.

Conventions for all cards below: backend Python 3.12 + FastAPI + async SQLAlchemy 2.0 + Pydantic v2; tests with pytest + pytest-asyncio + httpx. All LLM calls go through the provider abstraction (`app/agents/llm/`, built via `app/agents/llm/factory.py` from `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` env vars) and the structured-output bridge (`app/agents/bridge.py`, Pydantic validation + repair-retry loop, max 2 retries). With no API key configured the deterministic mock provider must keep every flow working — never hardcode a provider name. Engine code (`app/engine/`) stays pure Python: no I/O, no DB, no network, seeded-deterministic.

## Task T30: Resilience audit generation: survival rate, median lifespan, kill vectors, ranked weaknesses

**Description:** Build the backend that turns a completed Monte Carlo run into a persisted Report matching spec §10 Format C. Create the `Report` SQLAlchemy model in `app/models/report.py` (fields: `id`, `run_id` FK, `type` = `"resilience_audit"`, `content_md` Text, `content_json` JSONB, `pdf_path` nullable String, timestamps) plus an Alembic migration. Create `app/services/report_service.py` with a `generate_resilience_audit(run_id, db) -> Report` function that reads the Monte Carlo aggregation stored by T27 in `SimulationRun.result` (contract: `{"runs_total": int, "runs_survived": int, "lifespans_months": [int], "death_causes": {cause: count}, "final_kpis": {...}}`) and computes deterministically: survival rate (`runs_survived / runs_total`), median lifespan (statistics.median of `lifespans_months`), and ranked kill vectors (death causes sorted by count desc, each with `% of failures`). Weaknesses are ranked by severity CRITICAL > HIGH > MEDIUM, combining the top kill vectors with the blueprint's `identified_vulnerabilities` (Format A) and the engine's `resilience_score` from `app/engine/metrics.py`. Render the deterministic sections of Format C markdown — SURVIVAL METRICS and ARCHITECTURAL WEAKNESSES — with this exact structure from the spec:

```markdown
### SURVIVAL METRICS
- **Survival Rate:** 34% (Failed in 66 of 100 Monte Carlo runs)
- **Median Lifespan:** 11 months
- **Primary Kill Vector:** Cash flow death due to client concentration (47% of failures)

### ARCHITECTURAL WEAKNESSES
1. **CRITICAL:** 62% of MRR from one client. A single churn event is fatal.
```

Placeholder subsections for AI-GENERATED OPTIMIZATIONS and COUNTER-FACTUAL INSIGHT are left empty here (T31 fills them). Create Pydantic v2 schemas in `app/schemas/report.py`: `ReportResponse {id, run_id, type, content_md, content_json, pdf_path, created_at}` and `SurvivalMetrics {survival_rate, runs_total, runs_survived, median_lifespan_months, kill_vectors: [{cause, count, pct}]}`. Expose `GET /api/v1/simulations/{run_id}/report` in `app/api/v1/endpoints/reports.py` (register the router in `app/api/v1/router.py`): returns 200 with `ReportResponse`, generating + persisting the report on first call (idempotent — second call returns the stored row); 404 if the run does not exist or belongs to another workspace; 409 if the run status is not `completed` or the run mode is not `monte_carlo`/`stress`.

**Acceptance criteria:**
- [ ] `GET /api/v1/simulations/{run_id}/report` on a completed Monte Carlo run returns 200 with `content_md` containing the literal headings `### SURVIVAL METRICS` and `### ARCHITECTURAL WEAKNESSES`
- [ ] `content_json.survival.survival_rate` equals `runs_survived / runs_total` from the stored aggregation, and `median_lifespan_months` equals the median of `lifespans_months`
- [ ] Kill vectors in `content_json.survival.kill_vectors` are sorted by count descending and percentages sum to 100 (±0.1)
- [ ] Calling the endpoint twice creates exactly one `Report` row (idempotent)
- [ ] Returns 404 for a run in another workspace and 409 for a non-completed run
- [ ] Same input aggregation always yields byte-identical `content_md` (deterministic, no LLM in this task)

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/services/test_report_service.py tests/integration/api/test_reports.py -v` — create `tests/unit/services/test_report_service.py` (metrics math, markdown rendering, idempotency) and `tests/integration/api/test_reports.py` (200/404/409 cases via httpx)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: create a Monte Carlo run via the API, then `curl -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/simulations/{run_id}/report | jq .content_md` and eyeball the Format C sections

**Dependencies:** T27

**Files likely touched:**
- `backend/app/models/report.py`
- `backend/app/schemas/report.py`
- `backend/app/services/report_service.py`
- `backend/app/api/v1/endpoints/reports.py`
- `backend/app/api/v1/router.py`
- `backend/alembic/versions/<new>_create_reports_table.py`
- `backend/tests/unit/services/test_report_service.py`
- `backend/tests/integration/api/test_reports.py`

**Estimated scope:** M

## Task T31: Counter-factual analysis + optimization recommendation service

**Description:** Build the optimization brain behind Format C's remaining sections. Two halves, both in `app/services/optimization_service.py` and `app/agents/post_mortem.py`. (1) **Deterministic counter-factual re-runs:** implement `estimate_survival_delta(base_payload: dict, tweak: BlueprintTweak, n_runs: int, seed: int) -> float` that clones the blueprint payload (Format A), applies exactly ONE variable change, re-runs the pure engine in-process (no Celery — a 24-month run is <100ms, so 6 tweaks × 20 seeded runs fits in seconds), and returns `tweaked_survival_rate - baseline_survival_rate`. Define a fixed candidate tweak set as an enum/dataclass list in `app/services/optimization_service.py`: `churn -20%`, `cac -20%`, `price +10%`, `fixed_monthly -15%`, `starting_capital +25%`, `client_concentration capped at 25% of revenue` (model the last as equalizing revenue streams in the payload). All runs derive seeds as `seed + tweak_index * 1000 + run_index` so results are reproducible. (2) **AI narrative:** implement `app/agents/post_mortem.py` with `generate_post_mortem(metrics: SurvivalMetrics, deltas: list[TweakResult], blueprint: dict) -> PostMortemOutput`, using the prompt template `app/agents/prompts/post_mortem.md` (create it: instruct the model to act as The Forge, reference the numbers it is given, NEVER invent figures) and the bridge (`app/agents/bridge.py`) validating against a new Pydantic schema `PostMortemOutput {optimizations: [{recommendation, implementation_cost, trade_off, tweak_key}], counter_factual_insight: str, blueprint_v2_suggestions: [str]}`. The AI text is merged with the engine-measured deltas to build the Format C optimization table (`| Recommendation | Implementation Cost | Impact on Survival Rate | Trade-off |`) — the "Impact on Survival Rate" column ALWAYS comes from the engine's `estimate_survival_delta`, never from the LLM. The mock provider (no API key) must return schema-valid canned output derived from the input tweaks so the flow works offline. Extend `report_service.generate_resilience_audit` (or a follow-up `enrich_report_with_optimizations`) so the report's `content_md` gains the AI-GENERATED OPTIMIZATIONS table, a `### COUNTER-FACTUAL INSIGHT` blockquote, and a `### RECOMMENDED BLUEPRINT V2` bullet list, and `content_json` gains `optimizations` and `counter_factual` keys. Trigger enrichment automatically on first report generation; store results so repeat calls stay idempotent.

**Acceptance criteria:**
- [ ] `estimate_survival_delta` with the same `(base_payload, tweak, n_runs, seed)` arguments returns the identical float on repeated calls (seeded-deterministic, pure engine, no I/O)
- [ ] Report `content_md` after enrichment contains `### AI-GENERATED OPTIMIZATIONS`, a markdown table whose `Impact on Survival Rate` values match the engine-measured deltas (±0.5pp), and `### COUNTER-FACTUAL INSIGHT`
- [ ] `POST`-less flow: with `LLM_API_KEY` unset, `GET /api/v1/simulations/{run_id}/report` still returns 200 with a fully populated optimizations table from the mock provider
- [ ] LLM output failing schema validation triggers the bridge repair-retry (max 2) and then falls back to a deterministic table built from tweak deltas alone (never a 500)
- [ ] `content_json.optimizations` entries each carry `recommendation, implementation_cost, impact_on_survival_rate, trade_off`

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/services/test_optimization_service.py tests/unit/agents/test_post_mortem.py tests/integration/api/test_reports.py -v` — create `tests/unit/services/test_optimization_service.py` (delta determinism, tweak application) and `tests/unit/agents/test_post_mortem.py` (schema validation, repair retry, mock fallback)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: fetch a report and confirm the optimization table shows engine-measured deltas like `+12%` that stay identical across two consecutive requests

**Dependencies:** T30, T21

**Files likely touched:**
- `backend/app/services/optimization_service.py`
- `backend/app/agents/post_mortem.py`
- `backend/app/agents/prompts/post_mortem.md`
- `backend/app/schemas/report.py`
- `backend/app/services/report_service.py`
- `backend/tests/unit/services/test_optimization_service.py`
- `backend/tests/unit/agents/test_post_mortem.py`

**Estimated scope:** M

## Task T32: Report UI + Markdown/PDF export + shareable report links

**Description:** Build the user-facing report experience and its export/share plumbing. Backend first: create `app/utils/pdf.py` with `render_report_pdf(markdown: str, title: str) -> bytes` using **WeasyPrint** (add `weasyprint` to `backend/requirements.txt`; pure Python, no headless browser) — convert markdown to HTML (use `markdown` package, add to requirements), wrap in a minimal dark-styled HTML template, render to PDF bytes. Add `POST /api/v1/simulations/{run_id}/report/export` in `app/api/v1/endpoints/reports.py`: 201 → `{pdf_url}` after saving bytes under a configurable storage dir (settings key `REPORT_STORAGE_DIR`, default `./var/reports`, filename `report_{run_id}.pdf`) and updating `Report.pdf_path`; 404/409 as in T30. Add shareable public links using signed tokens via **itsdangerous** (add to requirements): `POST /api/v1/simulations/{run_id}/report/share` → 201 `{share_url, token, expires_at}` where `token = URLSafeTimedSerializer(settings.SECRET_KEY, salt="report-share").dumps({"run_id": ..., "report_id": ...})`; `GET /api/v1/reports/shared/{token}` is PUBLIC (no auth dependency), verifies the signature with `max_age` = 7 days, returns 200 `ReportResponse` or 410 if expired / 404 if bad signature. Frontend: create `frontend/src/features/reports/` with `ReportPage.tsx` rendering `content_md` as formatted markdown (add `react-markdown` to `frontend/package.json`) with styled sections for survival metrics (big stat cards), weaknesses (severity-colored list), and the optimization table; wire it into `frontend/src/router.tsx` at `/simulations/:runId/report` and a public unauthenticated route `/reports/shared/:token`. Use TanStack Query hooks (`useReport`, `useSharedReport`, `useExportPdf`, `useShareReport`) calling `lib/api-client.ts`. Include an "Export PDF" button (POST export, then open `pdf_url`) and a "Copy share link" button with clipboard + toast feedback.

**Acceptance criteria:**
- [ ] `POST /api/v1/simulations/{run_id}/report/export` returns 201 with `pdf_url`, the file exists on disk, starts with `%PDF`, and `Report.pdf_path` is set
- [ ] `POST /api/v1/simulations/{run_id}/report/share` returns 201; `GET /api/v1/reports/shared/{token}` returns 200 WITHOUT an Authorization header
- [ ] Tampering with one character of the token → 404; a token signed with `max_age` exceeded → 410
- [ ] Report page at `/simulations/:runId/report` renders all Format C sections (metrics, weaknesses, optimization table, counter-factual) from live API data
- [ ] Public route `/reports/shared/:token` renders the same report without login

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/utils/test_pdf.py tests/integration/api/test_reports.py -v` — create `tests/unit/utils/test_pdf.py` (PDF bytes start with `%PDF`, non-empty for sample markdown) and extend `tests/integration/api/test_reports.py` (export 201, share round-trip, tampered/expired token cases)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app` and `cd frontend && npm run lint && npm run build`
- [ ] Manual check: open a report in the UI, click "Export PDF" (a PDF downloads/opens), click "Copy share link", open the link in an incognito window — the report renders logged-out

**Dependencies:** T30

**Files likely touched:**
- `backend/app/utils/pdf.py`
- `backend/app/api/v1/endpoints/reports.py`
- `backend/app/core/config.py` (add `REPORT_STORAGE_DIR`)
- `backend/requirements.txt`
- `backend/tests/unit/utils/test_pdf.py`
- `backend/tests/integration/api/test_reports.py`
- `frontend/src/features/reports/ReportPage.tsx`
- `frontend/src/features/reports/SharedReportPage.tsx`
- `frontend/src/features/reports/hooks.ts`
- `frontend/src/router.tsx`
- `frontend/package.json`

**Estimated scope:** M

## Task T33: Run/blueprint comparison endpoint + UI (V1 vs V2)

**Description:** Let users compare two Monte Carlo outcomes — typically Blueprint V1 vs V2 after applying optimizations — per the spec's Resilience Training Loop ("User accepts → Blueprint V2 → Repeat until survival rate >90%"). Backend: add `GET /api/v1/reports/compare?a={run_id}&b={run_id}` to `app/api/v1/endpoints/reports.py`. Both runs must belong to the caller's workspace (404 otherwise) and be completed Monte Carlo/stress runs (409 otherwise). Implement `compare_runs(run_a, run_b) -> ComparisonResult` in `app/services/report_service.py` (reuse each run's stored aggregation; if a Report row exists reuse its `content_json`, else compute survival metrics inline via the same helpers as T30). Response schema `ComparisonResponse` in `app/schemas/report.py`: `200 → {a: RunSummary, b: RunSummary, deltas: {survival_rate_pp, median_lifespan_months, resilience_score_pp}, kill_vector_changes: [{cause, pct_a, pct_b, delta_pp}], verdict: "improved"|"regressed"|"unchanged"}` where `RunSummary = {run_id, blueprint_version_id, blueprint_version, survival_rate, median_lifespan_months, resilience_score, top_kill_vector}` and `verdict` = "improved" if `deltas.survival_rate_pp > 1`, "regressed" if `< -1`, else "unchanged". Frontend: create `frontend/src/features/reports/ComparePage.tsx` at route `/reports/compare?a=&b=` with a run picker (two selects listing the workspace's completed runs, TanStack Query) and a diff view: side-by-side metric cards for both runs with delta badges (green +pp / red −pp), a kill-vector comparison table showing `pct_a → pct_b (Δpp)` per cause sorted by absolute delta, and a verdict banner ("V2 improves survival by +18pp"). Reuse chart primitives from `frontend/src/components/charts/` where useful (e.g. overlaid survival bars); no new chart library.

**Acceptance criteria:**
- [ ] `GET /api/v1/reports/compare?a=<id>&b=<id>` returns 200 with `deltas.survival_rate_pp == round((b.survival_rate - a.survival_rate) * 100, 1)`
- [ ] `verdict` follows the ±1pp rule exactly; comparing a run to itself returns `verdict: "unchanged"` and all-zero deltas
- [ ] 404 when either run is missing/foreign-workspace; 409 when either run is not completed
- [ ] `kill_vector_changes` is sorted by `abs(delta_pp)` descending
- [ ] Compare page renders both runs' metrics and delta badges from the live endpoint; changing a picker refetches and updates the view

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/services/test_report_service.py tests/integration/api/test_reports.py -v` — extend both files with comparison cases (delta math, verdict thresholds, self-compare, 404/409)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app` and `cd frontend && npm run lint && npm run build`
- [ ] Manual check: run Monte Carlo on a blueprint, apply an optimization as V2, run Monte Carlo again, open `/reports/compare?a=<v1run>&b=<v2run>` and confirm the verdict banner and kill-vector deltas render

**Dependencies:** T30

**Files likely touched:**
- `backend/app/services/report_service.py`
- `backend/app/schemas/report.py`
- `backend/app/api/v1/endpoints/reports.py`
- `backend/tests/unit/services/test_report_service.py`
- `backend/tests/integration/api/test_reports.py`
- `frontend/src/features/reports/ComparePage.tsx`
- `frontend/src/features/reports/hooks.ts`
- `frontend/src/router.tsx`

**Estimated scope:** M

## Checkpoint D

- [ ] End-to-end loop works: build blueprint → baseline run → stress test with decisions → Monte Carlo → resilience report → V1/V2 comparison

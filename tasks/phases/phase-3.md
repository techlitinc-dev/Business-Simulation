# Phase 3 — Blueprints

Turn the Format A blueprint contract into a persisted, versioned, workspace-scoped domain: Pydantic schemas + structural validation (T16), CRUD/versioning REST API (T17), guided builder wizard with live validation (T18), and a read-only React Flow model canvas (T19).

The canonical Format A JSON (spec §10) — every card below refers to this exact shape:

```json
{
  "blueprint_version": "1.0",
  "business_profile": {
    "model_type": "SaaS",
    "stage": "Seed",
    "industry": "B2B Productivity Software",
    "geography": "North America"
  },
  "revenue_engine": {
    "streams": [
      {
        "name": "Primary Subscription",
        "pricing_model": "Subscription",
        "price_point": 99,
        "projected_customers_month_12": 500,
        "ltv": 2400,
        "cac": 850,
        "churn_monthly": 0.05
      }
    ]
  },
  "cost_structure": {
    "fixed_monthly": 35000,
    "variable_per_unit": 12,
    "team": [
      {"role": "CEO/Founder", "salary_annual": 80000, "hire_month": 0},
      {"role": "Lead Developer", "salary_annual": 120000, "hire_month": 0},
      {"role": "Sales Rep", "salary_annual": 70000, "hire_month": 3}
    ],
    "burn_rate_month_1": 45000
  },
  "financials": {
    "starting_capital": 500000,
    "funding_rounds": [],
    "target_runway_months": 18
  },
  "identified_vulnerabilities": [
    {
      "type": "liquidity",
      "severity": "high",
      "description": "Burn rate exceeds starting capital runway at current growth assumptions.",
      "mitigation_suggestion": "Reduce fixed costs by 20% or accelerate revenue to Month 4."
    }
  ],
  "simulation_parameters": {
    "time_step": "monthly",
    "monte_carlo_runs": 100,
    "random_seed": null
  }
}
```

---

## Task T16: Blueprint Pydantic schemas (Format A) + structural validation service

**Description:** Create the Pydantic v2 models in `backend/app/schemas/blueprint.py` that mirror Format A from spec §10 (JSON above) **field-for-field**, so the same schema is used by the API (T17), the engine compiler (T11 already consumes this shape), and later the AI bridge. Model names: `BlueprintPayload` (root, with `blueprint_version: str`, `business_profile: BusinessProfile`, `revenue_engine: RevenueEngine`, `cost_structure: CostStructure`, `financials: Financials`, `identified_vulnerabilities: list[Vulnerability]`, `simulation_parameters: SimulationParameters`); nested models `BusinessProfile(model_type, stage, industry, geography)`, `RevenueEngine(streams: list[RevenueStream])`, `RevenueStream(name, pricing_model, price_point: float > 0, projected_customers_month_12: int >= 0, ltv: float >= 0, cac: float >= 0, churn_monthly: float in [0, 1])`, `CostStructure(fixed_monthly: float >= 0, variable_per_unit: float >= 0, team: list[TeamMember], burn_rate_month_1: float >= 0)`, `TeamMember(role, salary_annual: float >= 0, hire_month: int >= 0)`, `Financials(starting_capital: float >= 0, funding_rounds: list[FundingRound], target_runway_months: int >= 1)`, `FundingRound(month: int >= 0, amount: float > 0)`, `Vulnerability(type: Literal["liquidity","market","operational","competitive","regulatory"], severity: Literal["low","medium","high"], description, mitigation_suggestion)`, `SimulationParameters(time_step: Literal["monthly"] = "monthly", monte_carlo_runs: int = 100, random_seed: int | None = None)`. Use `ConfigDict(extra="forbid")` on every model so malformed payloads fail loudly. Then add the structural validation service in `backend/app/services/blueprint_service.py`: a pure, sync function `validate_blueprint(payload: BlueprintPayload) -> ValidationReport` plus the DTOs `ValidationIssue(code: str, severity: Literal["error","warning"], field: str, message: str)` and `ValidationReport(is_valid: bool, errors: list[ValidationIssue], warnings: list[ValidationIssue])` (also in `schemas/blueprint.py`). Checks, using spec §5 formulas — LTV = (ARPU × Gross Margin) / Monthly Churn, Runway = Cash / Monthly Burn:

1. **LTV:CAC ratio** (warning): per stream, if `cac > 0` and `ltv / cac < 3.0` emit warning code `LTV_CAC_RATIO` — spec §9 message style: *"Your LTV:CAC ratio is {r:.1f}:1. This is below the 3:1 survival threshold. Consider raising prices or reducing churn."*
2. **Negative unit economics** (error): any stream with `ltv < cac` → error code `NEGATIVE_UNIT_ECONOMICS`; also any stream with `variable_per_unit >= price_point` → error code `NEGATIVE_CONTRIBUTION_MARGIN`.
3. **Runway check** (warning): `runway_months = starting_capital / burn_rate_month_1` (skip if burn is 0); if `runway_months < target_runway_months` → warning code `INSUFFICIENT_RUNWAY`.
4. **Revenue concentration** (warning): project month-12 revenue per stream as `price_point × projected_customers_month_12`; if total > 0 and the largest stream is > 70% of total → warning code `REVENUE_CONCENTRATION`.
5. **Zero revenue engine** (error): `streams` empty → error code `NO_REVENUE_STREAMS` (also enforce `min_length=1` is NOT used — keep it a service-level error so the API can still store drafts; instead validate in the service only).

`is_valid = (len(errors) == 0)`. Warnings never block. This service is pure Python (no DB, no I/O) so it is trivially unit-testable.

**Acceptance criteria:**
- [ ] `BlueprintPayload.model_validate(<Format A JSON from spec §10>)` succeeds and `model_dump()` round-trips to the same keys; extra/unknown fields raise `ValidationError` (extra="forbid").
- [ ] A fixture blueprint with a stream `ltv=1000, cac=850` produces a `ValidationReport` with one `LTV_CAC_RATIO` warning (ratio 1.2 < 3.0) and `is_valid == True`.
- [ ] A stream with `ltv < cac` produces an error `NEGATIVE_UNIT_ECONOMICS` and `is_valid == False`; `variable_per_unit >= price_point` produces `NEGATIVE_CONTRIBUTION_MARGIN`.
- [ ] `starting_capital=100000, burn_rate_month_1=45000, target_runway_months=18` produces `INSUFFICIENT_RUNWAY` warning (runway ≈ 2.2 months).
- [ ] Two streams where one holds 80% of projected month-12 revenue produces `REVENUE_CONCENTRATION`; an empty `streams` list produces error `NO_REVENUE_STREAMS`.

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/services/test_blueprint_validation.py tests/unit/services/test_blueprint_schemas.py -v` — create `backend/tests/unit/services/test_blueprint_schemas.py` (round-trip + extra-forbid cases) and `backend/tests/unit/services/test_blueprint_validation.py` (one test per rule above, using `backend/tests/fixtures/blueprint_valid.json` — create it from the spec §10 JSON verbatim)
- [ ] Lint passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `python -c "from app.schemas.blueprint import BlueprintPayload; import json; BlueprintPayload.model_validate(json.load(open('tests/fixtures/blueprint_valid.json')))"` exits 0 from `backend/`

**Dependencies:** T04, T11

**Files likely touched:**
- `backend/app/schemas/blueprint.py` (create)
- `backend/app/services/blueprint_service.py` (create)
- `backend/tests/unit/services/test_blueprint_schemas.py` (create)
- `backend/tests/unit/services/test_blueprint_validation.py` (create)
- `backend/tests/fixtures/blueprint_valid.json` (create)

**Estimated scope:** M

---

## Task T17: Blueprint CRUD + versioning API

**Description:** Persist blueprints as versioned documents, workspace-scoped. Create SQLAlchemy 2.0 async models in `backend/app/models/blueprint.py`: `Blueprint` — `id` (string, prefixed `bp_` via `app/utils/ids.py`), `workspace_id` (FK → workspaces, `ondelete="CASCADE"`, indexed), `name: str`, `industry: str`, `stage: str`, `current_version: int = 1`, plus the common timestamp columns from `app/db/base.py`; and `BlueprintVersion` — `id`, `blueprint_id` (FK → blueprints, `ondelete="CASCADE"`, indexed), `version: int`, `payload` (JSONB, stores a `BlueprintPayload` dump), `vulnerabilities` (JSONB, list, default `[]` — populated later by the AI Forge review in T22), `created_at`. Add a `UniqueConstraint(blueprint_id, version)` and generate an Alembic migration in `backend/alembic/versions/`. Add request/response DTOs to `backend/app/schemas/blueprint.py`: `BlueprintCreate(name, industry, stage, payload: BlueprintPayload)`, `BlueprintUpdate(name: str | None = None, industry: str | None = None, stage: str | None = None)`, `BlueprintVersionCreate(payload: BlueprintPayload)`, `BlueprintVersionResponse(id, blueprint_id, version, payload, vulnerabilities, created_at)`, `BlueprintResponse(id, workspace_id, name, industry, stage, current_version, created_at, updated_at)`, `BlueprintDetailResponse(BlueprintResponse + current payload)`. Implement the router `backend/app/api/v1/endpoints/blueprints.py` (prefix `/blueprints`, tag `blueprints`) and register it in `backend/app/api/v1/router.py`. Every endpoint takes the workspace guard dependency from T08 in `app/api/deps.py` (current workspace from header/path per T08's convention) and must scope all queries by `workspace_id` — cross-workspace ids return 404, never 403. Endpoints:

- `POST /api/v1/blueprints` — body `BlueprintCreate`; runs `validate_blueprint(payload)` and rejects with **422** `{detail: ValidationReport}` if `is_valid` is False; on success creates Blueprint + BlueprintVersion(version=1) and returns **201** `BlueprintDetailResponse`.
- `GET /api/v1/blueprints` — returns **200** `list[BlueprintResponse]` for the workspace, ordered by `updated_at desc`.
- `GET /api/v1/blueprints/{blueprint_id}` — **200** `BlueprintDetailResponse` (includes payload of `current_version`); **404** if not found in workspace.
- `PATCH /api/v1/blueprints/{blueprint_id}` — body `BlueprintUpdate`; metadata only, never touches versions; **200** `BlueprintResponse`.
- `DELETE /api/v1/blueprints/{blueprint_id}` — **204**, cascades to versions.
- `POST /api/v1/blueprints/{blueprint_id}/versions` — body `BlueprintVersionCreate`; validates payload (same 422 behavior), inserts `BlueprintVersion(version = current_version + 1)` and updates `current_version`; **201** `BlueprintVersionResponse`.
- `GET /api/v1/blueprints/{blueprint_id}/versions` — **200** `list[BlueprintVersionResponse]`, newest first.
- `GET /api/v1/blueprints/{blueprint_id}/validate` — runs `validate_blueprint` on the current version's payload (optional query param `?version=N` to validate an older version, 404 if that version doesn't exist) and returns **200** `ValidationReport` — this endpoint never fails on bad blueprints; it reports.

**Acceptance criteria:**
- [ ] `POST /api/v1/blueprints` with the valid fixture payload returns 201 and the response body contains `id` starting with `bp_`, `current_version: 1`, and the echoed payload; an invalid payload (e.g. `ltv < cac`) returns 422 with a `ValidationReport` body.
- [ ] `GET /api/v1/blueprints` returns only the requesting workspace's blueprints; `GET`/`PATCH`/`DELETE` with another workspace's blueprint id returns 404.
- [ ] Two sequential `POST .../versions` calls produce versions 2 and 3 and bump `current_version` to 3; `GET .../versions` returns 3 entries newest-first.
- [ ] `GET /api/v1/blueprints/{id}/validate` returns 200 with `is_valid: true` and zero errors for the fixture blueprint, and returns warnings (not HTTP errors) for a blueprint with LTV:CAC < 3:1; `?version=99` returns 404.
- [ ] `DELETE` removes the blueprint and `GET .../versions` afterwards returns 404.
- [ ] Alembic migration applies and reverts cleanly: `cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/integration/api/test_blueprints.py -v` — create `backend/tests/integration/api/test_blueprints.py` covering: create 201 + 422, workspace isolation 404, list scoping, versioning (2 creates → versions 2,3), validate endpoint (valid/warning/missing-version), delete cascade. Reuse the async httpx client + auth/workspace fixtures from the T08/T06 test setup in `tests/conftest.py`
- [ ] Lint passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: with the stack up, `curl -X POST localhost:8000/api/v1/blueprints -H "Authorization: Bearer <token>" -d @backend/tests/fixtures/blueprint_valid.json`-style request returns 201, and the row is visible via `psql` in tables `blueprints` and `blueprint_versions`

**Dependencies:** T16, T08

**Files likely touched:**
- `backend/app/models/blueprint.py` (create)
- `backend/app/schemas/blueprint.py` (modify — add CRUD DTOs)
- `backend/app/services/blueprint_service.py` (modify — add async DB helpers `create_blueprint`, `add_version`, `get_blueprint_detail`)
- `backend/app/api/v1/endpoints/blueprints.py` (create)
- `backend/app/api/v1/router.py` (modify — include router)
- `backend/alembic/versions/<rev>_blueprints.py` (create via `alembic revision --autogenerate`)
- `backend/tests/integration/api/test_blueprints.py` (create)

**Estimated scope:** M

---

## Task T18: Blueprint Builder UI: guided multi-step wizard + live validation panel

**Description:** Build the guided blueprint builder (spec §9 Phase 2) as a multi-step wizard under `frontend/src/features/blueprint/`. Five steps: **1 Profile** (model_type, stage, industry, geography — select inputs with the spec's options: model_type SaaS/D2C/Retail/Restaurant/Fintech/Other, stage Idea/MVP/Pre-Seed/Seed/Series A+), **2 Revenue Streams** (dynamic list of stream editors with add/remove; fields: name, pricing_model, price_point, projected_customers_month_12, ltv, cac, churn_monthly as a percentage input converted to 0–1), **3 Costs & Team** (fixed_monthly, variable_per_unit, burn_rate_month_1, dynamic team list: role, salary_annual, hire_month), **4 Financials** (starting_capital, target_runway_months, funding_rounds dynamic list), **5 Review** (read-only summary + submit). Hold the draft in a new Zustand store `frontend/src/stores/blueprint.ts` (`useBlueprintDraftStore`: `draft` object matching the Format A shape, `setStep`, `updateSection(section, value)`, `reset()`), so step navigation never loses state. Live validation works against the real API (T17), not a local reimplementation: on completing step 1, `POST /api/v1/blueprints` to create the draft blueprint and keep its `id` in the store; on every later step change (debounced ~800ms), `POST /api/v1/blueprints/{id}/versions` with the current draft, then invalidate the TanStack Query keyed `["blueprint", id, "validate"]` that calls `GET /api/v1/blueprints/{id}/validate`. The `ValidationPanel` component (right sidebar, visible on all steps) renders that query's `ValidationReport`: errors in red, warnings in amber, each with the `field` and `message` (e.g. the LTV:CAC 3:1 warning from spec §9), and a green "All checks passed" state when `is_valid && warnings.length === 0`. Use TanStack Query (`useMutation` for create/version, `useQuery` for validate), shadcn/ui primitives (`Card`, `Input`, `Select`, `Button`, `Badge`, `Separator`) and the existing `lib/api-client.ts` wrapper from T07. Add routes in `frontend/src/router.tsx`: `/blueprints/new` → `BuilderWizard`, `/blueprints/:id/edit` → `BuilderWizard` (loads current version payload into the store via `GET /blueprints/:id` on mount), `/blueprints/:id` → `BlueprintDetailPage` (simple read-only page linking to edit + canvas). All API calls go through `api-client.ts`; field names sent to the backend must match Format A exactly (snake_case — do not camelCase the payload).

**Acceptance criteria:**
- [ ] Navigating to `/blueprints/new` renders step 1; the user can fill all five steps, go Back/Next without losing entered values, and Finish lands on `/blueprints/:id` with the blueprint persisted server-side.
- [ ] Editing any field that changes the draft triggers (after debounce) a `POST /versions` followed by a refetch of `GET /blueprints/{id}/validate`, and the panel updates without a page reload.
- [ ] Entering a stream with `ltv=1000, cac=850` shows an amber warning containing "3:1 survival threshold" in the panel; entering `ltv < cac` shows a red error and disables the Finish button.
- [ ] `/blueprints/:id/edit` pre-fills every step from the current version payload fetched from the API.
- [ ] Validation panel shows loading and error (API unreachable) states instead of crashing.

**Verification:**
- [ ] Tests pass: if frontend test infra exists from T03 (`vitest`), add `frontend/src/features/blueprint/__tests__/blueprint-store.test.ts` covering store `updateSection`/`reset` and payload shape (snake_case keys, churn as 0–1 fraction) and run `cd frontend && npm test`; if no test runner was scaffolded in T03, note it and skip (build+lint are the gate)
- [ ] Build/lint pass: `cd frontend && npm run build && npm run lint`
- [ ] Manual check: with backend running, create a blueprint in the wizard; `GET /api/v1/blueprints` (e.g. via curl or Swagger UI at `/docs`) shows it with multiple versions, and the validation panel changes live as you type a low LTV

**Dependencies:** T17, T07

**Files likely touched:**
- `frontend/src/features/blueprint/BuilderWizard.tsx` (create)
- `frontend/src/features/blueprint/steps/ProfileStep.tsx` (create)
- `frontend/src/features/blueprint/steps/RevenueStep.tsx` (create)
- `frontend/src/features/blueprint/steps/CostsTeamStep.tsx` (create)
- `frontend/src/features/blueprint/steps/FinancialsStep.tsx` (create)
- `frontend/src/features/blueprint/ValidationPanel.tsx` (create)
- `frontend/src/features/blueprint/BlueprintDetailPage.tsx` (create)
- `frontend/src/features/blueprint/api.ts` (create — TanStack Query hooks: `useCreateBlueprint`, `useAddVersion`, `useBlueprint`, `useBlueprintValidation`)
- `frontend/src/stores/blueprint.ts` (create)
- `frontend/src/router.tsx` (modify — add routes)

**Estimated scope:** L

---

## Task T19: Blueprint canvas view (React Flow visual model map)

**Description:** Add a read-only visual map of a blueprint's business model (spec §9 Phase 2: "Visual canvas (like Business Model Canvas)") using React Flow (the plan's frontend stack includes it; use the package already in `frontend/package.json` — `@xyflow/react` for React Flow 12, or `reactflow` for v11; if T03 did not install it, add `@xyflow/react@^12`). Create `frontend/src/features/blueprint/CanvasView.tsx` plus `frontend/src/features/blueprint/canvas-layout.ts` (pure function `blueprintToFlow(payload: BlueprintPayload): { nodes: Node[]; edges: Edge[] }`) and custom node components in `frontend/src/features/blueprint/canvas-nodes.tsx`. Node types, all derived from one Format A payload fetched with `useBlueprint(id)` from T18's `api.ts`: one central **BusinessNode** (name, model_type, stage, industry); one **RevenueStreamNode** per stream (name, price_point, projected_customers_month_12, LTV:CAC ratio computed as `ltv/cac`, colored red when < 3:1); one **CostNode** (fixed_monthly + burn_rate_month_1 summary) and one **TeamNode** (headcount + total annual salaries); one **VulnerabilityNode** per entry in `identified_vulnerabilities`, styled by severity (high=red, medium=amber, low=gray). Edges: every revenue stream → business (animated, labeled with projected month-12 revenue `price_point × projected_customers_month_12`), business → cost, business → team, vulnerability → business (dashed red for high severity). Layout is deterministic and hand-computed in `blueprintToFlow` (no auto-layout dependency): business at center (0,0), streams stacked vertically at x=-400, cost/team at x=+400, vulnerabilities at y offsets below the business node. The canvas is strictly read-only: pass `nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}` (v11: same prop names) and render `Background` + `Controls` + a `Panel` legend explaining colors. Keep it a pure visualization — no editing, no validation calls (the panel from T18 owns validation). Register route `/blueprints/:id/canvas` → `CanvasView` in `frontend/src/router.tsx` and link to it from `BlueprintDetailPage`. Handle empty states: blueprint with zero vulnerabilities renders no vulnerability nodes; fetch error shows a shadcn `Alert`.

**Acceptance criteria:**
- [ ] `/blueprints/:id/canvas` renders one node per revenue stream, one cost node, one team node, one business node, and one node per vulnerability in the payload, with edges as specified; node count for the spec §10 fixture = 1 business + 1 stream + 1 cost + 1 team + 1 vulnerability = 5 nodes.
- [ ] A stream with `ltv/cac < 3` renders its node in a red/destructive style; ≥ 3 renders neutral/green.
- [ ] Nodes cannot be dragged or connected (read-only), and no mutation requests fire on any canvas interaction.
- [ ] Blueprint with `identified_vulnerabilities: []` renders without vulnerability nodes and without errors.
- [ ] Fetch failure (e.g. 404) renders an error `Alert`, not a blank canvas or crash.

**Verification:**
- [ ] Tests pass: if `vitest` exists from T03, add `frontend/src/features/blueprint/__tests__/canvas-layout.test.ts` asserting `blueprintToFlow(fixturePayload)` returns the exact node/edge counts and red styling flag for LTV:CAC < 3 (this function is pure — no DOM needed) and run `cd frontend && npm test`; otherwise skip with a note
- [ ] Build/lint pass: `cd frontend && npm run build && npm run lint`
- [ ] Manual check: open `/blueprints/<id>/canvas` for a blueprint created via the T18 wizard; pan/zoom works, all node types visible, and dragging a node does nothing

**Dependencies:** T17

**Files likely touched:**
- `frontend/src/features/blueprint/CanvasView.tsx` (create)
- `frontend/src/features/blueprint/canvas-layout.ts` (create)
- `frontend/src/features/blueprint/canvas-nodes.tsx` (create)
- `frontend/src/features/blueprint/BlueprintDetailPage.tsx` (modify — add link to canvas)
- `frontend/src/router.tsx` (modify — add `/blueprints/:id/canvas` route)
- `frontend/package.json` (modify only if React Flow is missing from T03 scaffold)

**Estimated scope:** M

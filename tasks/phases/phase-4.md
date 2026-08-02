# Phase 4 — AI Cortex

Build the LLM layer that sits on top of the deterministic engine: an env-configured provider abstraction with a deterministic mock, a structured-output bridge with repair-retry, and the Forge / Hurdle Generator / Strategist agents that turn engine state into Format-A/B JSON.

Conventions for the whole phase:
- All LLM access goes through `app/agents/llm/` + `app/agents/bridge.py`. No agent may import `openai` directly.
- Config comes from env via `app/core/config.py` (pydantic-settings): `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES`. Never hardcode a provider name or model.
- Everything must work with **no API key** via the deterministic `MockProvider` (dev/test mode).
- Agents never mutate engine state directly; they emit JSON validated by Pydantic v2 schemas, and mechanical deltas are clamped before use.
- Tests live in `backend/tests/unit/agents/` and `backend/tests/integration/api/`; use `pytest` + `pytest-asyncio` + `httpx`.

---

## Task T20: LLM provider abstraction (OpenAI-compatible, env-configured, retry/timeout, token-cost tracking, mock provider)

**Description:** Create the provider abstraction every agent will call. In `app/agents/llm/base.py` define a `LLMResponse` dataclass (`content: str`, `model: str`, `prompt_tokens: int`, `completion_tokens: int`, `cost_usd: float`, `latency_ms: float`) and a `LLMProvider` typing Protocol with one async method: `complete(system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 2048) -> LLMResponse`. In the same file implement `MockProvider`: deterministic, seeded by `sha256(system + user)` so identical prompts always return identical content; it keeps an ordered registry `(prompt_substring -> canned_response)` via `register(substring: str, response: str)` so tests/dev fixtures can pin exact outputs, returns a registered match when `substring in user` (first match wins), otherwise a stable fallback JSON string `{}`; it fills token/cost fields with deterministic pseudo-values derived from the hash (never random). In `app/agents/llm/openai_compat.py` implement `OpenAICompatibleProvider` using the `openai` Python SDK (`AsyncOpenAI(api_key=..., base_url=settings.llm_base_url)`, `chat.completions.create(model=settings.llm_model, messages=[{"role": "system", ...}, {"role": "user", ...}], temperature=..., max_tokens=..., timeout=settings.llm_timeout_seconds)`). Add `openai>=1.40` to `backend/requirements.txt` if not already present (plan mandates the OpenAI-compatible SDK). Retry on `openai.APITimeoutError`, `openai.RateLimitError`, `openai.APIConnectionError`, and 5xx `openai.APIStatusError` up to `settings.llm_max_retries` (default 3) with exponential backoff (sleep 1s, 2s, 4s, …, capped at 10s) using plain `asyncio.sleep` — no new retry dependency. Re-raise the last exception after retries are exhausted. Compute `cost_usd = prompt_tokens/1000 * settings.llm_cost_per_1k_input_tokens + completion_tokens/1000 * settings.llm_cost_per_1k_output_tokens` (defaults 0.0 → cost 0.0 when prices are unconfigured). Add these fields to `Settings` in `app/core/config.py`: `llm_base_url: str = ""`, `llm_api_key: str = ""`, `llm_model: str = "deepseek-chat"`, `llm_timeout_seconds: float = 60.0`, `llm_max_retries: int = 3`, `llm_cost_per_1k_input_tokens: float = 0.0`, `llm_cost_per_1k_output_tokens: float = 0.0`, `llm_provider: str = "auto"`. In `app/agents/llm/factory.py` implement `get_llm_provider(settings: Settings) -> LLMProvider`: return `MockProvider()` when `settings.llm_provider == "mock"` or (`llm_provider == "auto"` and `llm_api_key` is empty); otherwise return `OpenAICompatibleProvider`. Also add the matching `LLM_*` entries to the repo-root `.env.example`.

**Acceptance criteria:**
- [ ] `get_llm_provider` returns `MockProvider` when `LLM_API_KEY` is unset (auto mode) and `OpenAICompatibleProvider` when a key is set; `LLM_PROVIDER=mock` forces the mock even with a key set.
- [ ] `MockProvider.complete` is deterministic: two calls with identical `(system, user)` return byte-identical `content`.
- [ ] `MockProvider.register("runway", '{"a": 1}')` makes any user prompt containing `"runway"` return exactly `{"a": 1}`.
- [ ] `OpenAICompatibleProvider` retries on timeout/rate-limit/connection errors with exponential backoff and re-raises after `llm_max_retries` attempts (verified by a mocked `AsyncOpenAI` client that fails twice then succeeds).
- [ ] `LLMResponse.cost_usd` equals the per-token formula above when cost settings are non-zero, and `prompt_tokens`/`completion_tokens` come from the SDK's `response.usage`.
- [ ] No module under `app/agents/` other than `openai_compat.py` imports `openai`.

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/agents/test_llm_provider.py -v` (create this file: mock determinism, registry matching, factory selection per env combination, retry-then-succeed and retry-exhausted using a stubbed AsyncOpenAI, cost formula).
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: with no `LLM_API_KEY` in env, run `cd backend && python -c "from app.core.config import get_settings; from app.agents.llm.factory import get_llm_provider; print(type(get_llm_provider(get_settings())).__name__)"` → prints `MockProvider`.

**Dependencies:** T02

**Files likely touched:**
- `backend/app/agents/llm/base.py`
- `backend/app/agents/llm/openai_compat.py`
- `backend/app/agents/llm/factory.py`
- `backend/app/core/config.py`
- `backend/requirements.txt`
- `.env.example`
- `backend/tests/unit/agents/test_llm_provider.py`

**Estimated scope:** M

---

## Task T21: Structured output bridge — Pydantic schema validation + repair-retry loop

**Description:** Create `app/agents/bridge.py`, the single choke point through which all agent LLM calls produce typed objects. Implement one generic coroutine: `async def generate_structured(provider: LLMProvider, schema: type[T], system_prompt: str, user_prompt: str, *, max_repairs: int = 2, temperature: float = 0.2) -> T` where `T` is any Pydantic v2 `BaseModel`. Flow: (1) call `provider.complete(system_prompt, user_prompt, ...)`; (2) extract JSON from the raw content — strip Markdown code fences (``` or ```json) and, if the content has prose around the JSON, slice from the first `{` to the last `}`; (3) validate with `schema.model_validate_json(...)`; (4) on `json.JSONDecodeError` or `pydantic.ValidationError`, if attempts remain, issue a repair call whose user prompt contains the original `user_prompt`, the invalid output, and the validation error message, instructing the model to return corrected JSON only (append the format contract: `schema.model_json_schema()` serialized into the prompt so the model knows the target shape); (5) after `max_repairs` failed repair attempts, raise `app.core.exceptions.StructuredOutputError` (create it there if missing: carries `raw_output` and `validation_error`). Also implement delta clamping used by later tasks: a module-level `MECHANICAL_DELTA_BOUNDS: dict[str, tuple[float, float]]` = `{"_delta_percent": (-90.0, 200.0), "team_morale_delta": (-1.0, 1.0), "probability_success": (0.0, 1.0), "believability_score": (0.0, 1.0)}` and a function `clamp_deltas(data: dict, bounds: dict = MECHANICAL_DELTA_BOUNDS) -> dict` that deep-copies `data` and clamps every numeric field whose name exactly matches a bound key, or ends with a bound key suffix (e.g. `cac_delta_percent` matches `_delta_percent`), into `[lo, hi]`. `generate_structured` accepts an optional `clamp: bool = True` flag: when true, run `clamp_deltas` over the parsed dict *before* validation so out-of-range mechanical numbers from the LLM are tamed instead of rejected. Bridge must be provider-agnostic (works identically with `MockProvider`) and must never swallow exceptions other than the parse/validation errors driving the retry loop.

**Acceptance criteria:**
- [ ] Valid JSON returned on the first attempt is parsed and returned as the schema instance with exactly one provider call.
- [ ] Content wrapped in ```json fences or surrounded by prose is still parsed correctly.
- [ ] A provider that returns invalid JSON once then valid JSON yields a valid schema instance after exactly two calls, and the repair prompt contains the validation error text and the schema JSON.
- [ ] A provider that always returns invalid JSON raises `StructuredOutputError` after `1 + max_repairs` total calls.
- [ ] `clamp_deltas({"cac_delta_percent": 500, "team_morale_delta": -3.0, "nested": {"churn_delta_percent": -200}})` returns `200`, `-1.0`, and `-90` respectively without mutating the input dict.
- [ ] With `clamp=True`, an out-of-range `believability_score: 1.7` is clamped to `1.0` and validates instead of failing.

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/agents/test_bridge.py -v` (create this file; drive it with `MockProvider` instances whose canned responses are swapped between calls — a tiny test-local `StubProvider` implementing the `LLMProvider` protocol with a response queue is fine).
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `cd backend && python -m pytest tests/unit/agents/test_bridge.py -k repair -v` shows the repair-loop tests passing with exactly the expected provider call counts.

**Dependencies:** T20

**Files likely touched:**
- `backend/app/agents/bridge.py`
- `backend/app/core/exceptions.py`
- `backend/tests/unit/agents/test_bridge.py`

**Estimated scope:** M

---

## Task T22: Forge agent — system prompt, blueprint review endpoint (Format A vulnerabilities)

**Description:** Build the Forge agent's blueprint-review capability and expose it via `POST /api/v1/blueprints/{id}/review`. First create `app/agents/prompts/forge_system.md` containing the full system prompt from the product spec `Business_Simulation_System_Plan.md` §13 — copy the entire markdown block (IDENTITY through INITIALIZATION) verbatim into the file. In `app/schemas/blueprint.py` add the review DTOs (Pydantic v2): `VulnerabilityItem` (`type: Literal["liquidity","concentration","unit_economics","market","operational","team","regulatory"]`, `severity: Literal["low","medium","high","critical"]`, `description: str`, `mitigation_suggestion: str`) and `ForgeReviewResponse` (`overall_assessment: str`, `identified_vulnerabilities: list[VulnerabilityItem]`, `reviewed_version: int`, `llm_model: str`, `tokens_used: int`). This mirrors the `identified_vulnerabilities` block of Format A (spec §10). In `app/agents/forge.py` implement `class ForgeAgent` with `__init__(self, provider: LLMProvider)` and `async def review_blueprint(self, blueprint_payload: dict) -> tuple[ForgeReviewResponse, LLMResponse]`: load the system prompt from `app/agents/prompts/forge_system.md` (read via `pathlib.Path(__file__).parent / "prompts" / "forge_system.md"`, cached at module import), build a user prompt containing the blueprint payload as pretty JSON plus an instruction to output ONLY the review JSON matching the `ForgeReviewResponse` schema (fields `overall_assessment` + `identified_vulnerabilities`), and call `bridge.generate_structured(provider, ForgeReviewResponse, system, user)`. Extend `app/api/v1/endpoints/blueprints.py` with `POST /{blueprint_id}/review` (workspace-guarded like the other blueprint routes, using existing deps from `app/api/deps.py`): load the blueprint and its current `BlueprintVersion`, 404 if missing, call the agent with a provider from `get_llm_provider(get_settings())`, persist `identified_vulnerabilities` (as JSON) into `BlueprintVersion.vulnerabilities` (JSONB column from T16/T17), commit, and return 200 with `ForgeReviewResponse`. On `StructuredOutputError` return 502 with `{"detail": "LLM returned invalid output"}`. For dev/test without an API key, register a canned review on the `MockProvider` inside the test (or a fixture in `tests/conftest.py`) so the endpoint returns deterministic data.

**Acceptance criteria:**
- [ ] `app/agents/prompts/forge_system.md` exists and contains the spec §13 prompt (spot-check: includes "NEVER BE GENERIC" and "FORMAT B: DYNAMIC HURDLE GENERATION").
- [ ] `POST /api/v1/blueprints/{id}/review` returns 200 with a body matching `ForgeReviewResponse`, and the blueprint's current `BlueprintVersion.vulnerabilities` column equals the returned `identified_vulnerabilities` after the call.
- [ ] Returns 404 for an unknown blueprint id and 403/forbidden for a blueprint outside the caller's workspace (reuse existing guard).
- [ ] When the provider keeps returning invalid JSON, the endpoint returns 502 (not a 500 traceback).
- [ ] The whole flow works with no `LLM_API_KEY` set (MockProvider path) — the integration test runs without network access.
- [ ] `ForgeAgent` calls the LLM only via `bridge.generate_structured` (grep: no direct `provider.complete` in `forge.py`).

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/agents/test_forge.py tests/integration/api/test_blueprint_review.py -v` (create both files; unit test drives `ForgeAgent` with a `MockProvider` registered with a canned review payload; integration test uses httpx + the app's test DB from `tests/conftest.py`, creates a blueprint + version, posts review, asserts 200 + persisted vulnerabilities).
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: with no LLM key, `curl -X POST localhost:8000/api/v1/blueprints/{id}/review -H "Authorization: Bearer <token>"` returns schema-valid JSON with ≥1 vulnerability.

**Dependencies:** T21, T17

**Files likely touched:**
- `backend/app/agents/prompts/forge_system.md`
- `backend/app/agents/forge.py`
- `backend/app/schemas/blueprint.py`
- `backend/app/api/v1/endpoints/blueprints.py`
- `backend/tests/unit/agents/test_forge.py`
- `backend/tests/integration/api/test_blueprint_review.py`
- `backend/tests/conftest.py` (optional: shared mock-provider fixture)

**Estimated scope:** M

---

## Task T23: Hurdle generator — vital-signs snapshot → Format B hurdle JSON + chronicle memory

**Description:** Build the context-aware hurdle generation pipeline from spec §6 (Steps 1–3). Two modules. First `app/agents/chronicle.py` — narrative memory, pure Python, no LLM: dataclasses `ActorState` (`name: str`, `kind: str`, `first_seen_month: int`, `last_seen_month: int`, `notes: list[str]`), `ChronicleEntry` (`month: int`, `event_id: str`, `title: str`, `actors: list[str]`, `summary: str`, `chosen_option_id: str | None = None`), and `class Chronicle` holding `actors: dict[str, ActorState]` and `entries: list[ChronicleEntry]` with methods `add_entry(entry) -> None` (auto-creates/updates `ActorState` rows for every actor name — spec §13 constraint 4: a competitor introduced in Month 4 must be consistent in Month 8), `get_actor(name) -> ActorState | None`, and `to_prompt_summary(max_chars: int = 2000) -> str` (compact, newest-first bullet list of entries plus a one-line actor roster, truncated to `max_chars`). Chronicle must be JSON-serializable via a `to_dict()` / `from_dict()` pair so `hurdle_service` (later phases) can persist it. Second `app/agents/hurdle_generator.py`: `def build_vital_signs(state: BusinessState, kpis: dict) -> dict` producing the spec §6 Step 1 snapshot shape from engine state:

```json
{"burn_rate": 47000, "runway_months": 8, "cash_reserves": 376000,
 "revenue_concentration": {"top_client_percent": 40, "top_3_clients_percent": 72},
 "cac": 850, "ltv": 2400, "churn_monthly": 0.05, "mrr": 32000,
 "month": 7, "organic_acquisition": false}
```

(field values come from `BusinessState`/KPI snapshot fields defined in T11/T12 — map what exists, omit what doesn't). Then `class HurdleGenerator(provider)` with `async def generate(self, state: BusinessState, kpis: dict, chronicle: Chronicle, *, difficulty: int = 1, month: int) -> HurdleEvent`: system prompt loaded from `app/agents/prompts/hurdle_generation.md` (create it: instruct the model to act as The Forge, pick the business's "jugular vein" from the vital signs, reuse existing chronicle actors when relevant, respect adaptive difficulty — standard for runs 1–3, compounding for 4–10, nightmare for 10+ per spec §6 — and output ONLY Format B JSON); user prompt = vital-signs JSON + `chronicle.to_prompt_summary()` + current month + difficulty. Validate via `bridge.generate_structured` against a new `HurdleEvent` schema in `app/schemas/hurdle.py` (Pydantic v2, Format B from spec §10 *without* `strategic_options` — the Strategist in T24 owns options): `HurdleEvent` = `event_id: str`, `trigger_timing: str`, `category: Literal["market","operational","financial","black_swan","internal"]`, `narrative: HurdleNarrative` (`title`, `story`, `source_actor`, `believability_score: float` in [0,1]), `mechanical_impact: MechanicalImpact` (`immediate: ImmediateDeltas` — optional numeric fields `cac_delta_percent`, `churn_delta_percent`, `new_signups_delta_percent`, `team_morale_delta`, `cash_burn_delta_monthly`, `mrr_delta_percent`; `cascading: dict[str, str]`), `ai_game_master_note: str`. Call `generate_structured(..., clamp=True)` so mechanical deltas get clamped by the bridge bounds. After generation, append a `ChronicleEntry` to the chronicle (this happens in the generator so continuity is automatic). No HTTP endpoint in this task — the generator is consumed by hurdle_service in Phase 5.

**Acceptance criteria:**
- [ ] `build_vital_signs` returns a JSON-serializable dict containing at least `burn_rate`, `runway_months`, `cash_reserves`, `cac`, `ltv`, `churn_monthly`, `month` computed from the engine fixture state (reuse the 24-month fixture from T15).
- [ ] `HurdleGenerator.generate` with a `MockProvider` registered to a valid Format B payload returns a `HurdleEvent` that passes `HurdleEvent.model_validate` and records exactly one `ChronicleEntry` with the hurdle's `source_actor` present in `chronicle.actors`.
- [ ] A `source_actor` seen in a first hurdle reappears via `chronicle.to_prompt_summary()` in the user prompt of the *next* `generate` call (assert with a recording stub provider).
- [ ] A mock LLM response with `cac_delta_percent: 9999` is accepted after clamping to `200.0`, not rejected.
- [ ] `Chronicle.to_dict()` → `Chronicle.from_dict()` round-trips losslessly (actors + entries equal).
- [ ] An invalid-then-valid mock response exercises the bridge repair loop and still returns a `HurdleEvent`.

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/agents/test_hurdle_generator.py tests/unit/agents/test_chronicle.py -v` (create both; use the engine fixture state from `tests/fixtures/` and `MockProvider` with canned Format B payloads).
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: run a small REPL snippet that generates two hurdles in a row with the mock and prints `chronicle.to_prompt_summary()` — the second prompt visibly references the first hurdle's actor.

**Dependencies:** T21, T15

**Files likely touched:**
- `backend/app/agents/chronicle.py`
- `backend/app/agents/hurdle_generator.py`
- `backend/app/agents/prompts/hurdle_generation.md`
- `backend/app/schemas/hurdle.py`
- `backend/tests/unit/agents/test_hurdle_generator.py`
- `backend/tests/unit/agents/test_chronicle.py`

**Estimated scope:** M

---

## Task T24: Strategist — 2–4 branching options + 12-month engine projection per option

**Description:** Build the War Room advisor from spec §8. In `app/schemas/decision.py` add `StrategicOption` (Pydantic v2, per Format B's `strategic_options` entries): `option_id: str` (e.g. "A"), `name: str`, `description: str`, `cash_impact_monthly: float`, `probability_success: float` (clamped [0,1] via bridge), `second_order_risk: str`, `required_execution: str`; plus `OptionProjection` = `option_id: str`, `monthly_cash: list[float]` (exactly 12 entries), `end_cash: float`, `min_cash: float`, `survives: bool` (cash never < 0 across the 12 months), `runway_months: float`; and `StrategistResult` = `hurdle_id: str`, `options: list[StrategicOption]`, `projections: list[OptionProjection]`. In `app/agents/strategist.py` implement `class Strategist(provider)` with two responsibilities. (1) `async def propose_options(self, state: BusinessState, kpis: dict, hurdle: HurdleEvent, chronicle: Chronicle) -> list[StrategicOption]`: system prompt from `app/agents/prompts/strategic_options.md` (create it: The Forge in advisory mode; produce 2–4 strategically distinct options with honest risk/reward, spec §8 War Room style; respect the engine — never propose spending more cash than available, spec §13 constraint 5; output ONLY JSON `{"options": [...]}`); user prompt = vital signs (reuse `build_vital_signs` from `hurdle_generator.py`) + hurdle JSON + chronicle summary; validate via `bridge.generate_structured` against a wrapper schema `StrategicOptionList` (`options: list[StrategicOption]` with `min_length=2, max_length=4`) with `clamp=True`. (2) `def project_option(self, state: BusinessState, option: StrategicOption, *, months: int = 12, seed: int = 0) -> OptionProjection`: PURE deterministic — no LLM call. Deep-copy the engine state, apply the option mechanically (add `option.cash_impact_monthly` to monthly cash flow each month; if the hurdle's `ImmediateDeltas` were not yet applied, apply them first via the T15 event-injector function from `app/engine/events.py` so the projection reflects "hurdle + response"), then run the T13 monthly loop for `months` steps collecting end-of-month cash, and derive `survives`, `min_cash`, `end_cash`, `runway_months`. And `async def advise(...) -> StrategistResult` combining both: propose options, then project each. The strategist must follow the same rules as the rest of the phase: LLM only through the bridge; projection only through engine functions (no reimplemented math — reuse `app/engine/loop.py` / `events.py` / `financials.py`). No HTTP endpoint here; `POST /simulations/{id}/decide` in T26 will consume this.

**Acceptance criteria:**
- [ ] `propose_options` with a mock canned payload of 3 options returns exactly 3 `StrategicOption` objects; a canned payload of 1 or 5 options fails schema validation (min/max enforced) and triggers the bridge repair loop.
- [ ] Each option has a non-empty `second_order_risk` and `required_execution` (schema `min_length=1` on those strings).
- [ ] `project_option` returns `monthly_cash` of length 12, `survives == (min_cash >= 0)`, and is fully deterministic: two calls with the same state/option/seed produce identical projections.
- [ ] A `cash_impact_monthly` larger (more negative) than current cash produces `survives is False` — the projection honestly reports death (spec §13: respect the engine).
- [ ] `advise` returns one `OptionProjection` per option, `option_id`s aligned between `options` and `projections`.
- [ ] `project_option` performs no LLM calls (assert with a recording stub provider that call count is unchanged) and imports only from `app/engine/*`, never from `app/agents/llm/`.

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/agents/test_strategist.py -v` (create it; fixture: engine state from the T15 fixture blueprint at month 7 + a mock `HurdleEvent`; cover schema bounds, determinism, survival logic, advise alignment).
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: in a REPL, run `advise` against the fixture state with the mock provider and print the resulting table of option names vs. `end_cash`/`survives` — options are distinct and projections differ per option.

**Dependencies:** T23, T15

**Files likely touched:**
- `backend/app/agents/strategist.py`
- `backend/app/agents/prompts/strategic_options.md`
- `backend/app/schemas/decision.py`
- `backend/tests/unit/agents/test_strategist.py`

**Estimated scope:** M

---

## Checkpoint C

- [ ] With `LLM_*` env vars set, review + hurdle endpoints return schema-valid JSON; with no key, mock provider keeps dev flow working
- [ ] `cd backend && pytest tests/unit/agents -v` is fully green with no network access (all tests run on `MockProvider`/stub providers)
- [ ] `cd backend && ruff check app tests && mypy app` clean

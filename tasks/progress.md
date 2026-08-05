# Project Progress — The Forge

Live status tracker for the build. Updated as phases complete; full detail in `tasks/todo.md` and per-phase cards in `tasks/phases/`.

**Last updated:** 2026-08-05

## Summary

| Phase | Scope | Status |
|---|---|---|
| 0 | Scaffolding & DevOps (T01–T05) | Complete |
| 1 | Auth & Multi-Tenancy (T06–T10) | Complete |
| 2 | Deterministic Simulation Engine (T11–T15) | Complete |
| 3 | Blueprints (T16–T19) | Complete |
| 4 | AI Cortex (T20–T24) | **Complete** |
| 5 | Simulation Runs (T25–T29) | Not started |
| 6 | Reports & Optimization (T30–T33) | Not started |
| 7 | App Shell, Dashboard & Marketing (T34–T39) | Not started |
| 8 | Monetization & Platform Features (T40–T46) | Not started |
| 9 | Production Hardening (T47–T51) | Not started |

**Next up:** Phase 5 — Simulation Runs (T25–T29). Deps ready: engine (T15), blueprints (T17), AI Cortex (T20–T24).

## Phase 4 — AI Cortex (T20–T24) — Complete ✅

The LLM layer on top of the deterministic engine. All LLM access flows through the provider abstraction + structured-output bridge; everything works with no API key via the deterministic `MockProvider`.

### Delivered

- **T20 — LLM provider abstraction** (`app/agents/llm/`)
  - `LLMResponse` dataclass (content, model, prompt/completion tokens, cost_usd, latency_ms)
  - `LLMProvider` Protocol — single async `complete(system, user, ...)` method
  - `MockProvider` — deterministic, `sha256(system+user)`-seeded; substring registry pins canned outputs; stable `{}` fallback
  - `OpenAICompatibleProvider` — OpenAI SDK client; retries on timeout/rate-limit/connection/5xx with exponential backoff (1s, 2s, 4s, … cap 10s); token-cost formula (0.0 prices → 0.0 cost)
  - `get_llm_provider` factory — `LLM_PROVIDER=mock` forces mock; `auto` = mock when no `LLM_API_KEY`
  - `LLM_*` settings in `app/core/config.py` + `.env.example`; `openai>=1.40` in requirements

- **T21 — Structured output bridge** (`app/agents/bridge.py`)
  - `generate_structured(provider, schema, system, user)` — JSON extraction (fences/prose stripped), `clamp_deltas` on `MECHANICAL_DELTA_BOUNDS`, Pydantic v2 validation, repair-retry loop (max 2 repairs with schema embedded in repair prompt), raises `StructuredOutputError` on exhaustion
  - `clamp_deltas` deep-copies + clamps exact/suffix matches (e.g. `cac_delta_percent` → `_delta_percent` bound [-90, 200])

- **T22 — Forge agent** (`app/agents/forge.py` + `prompts/forge_system.md`)
  - `ForgeAgent.review_blueprint` → `ForgeReviewResponse` (Format A vulnerabilities) via bridge only
  - `POST /api/v1/blueprints/{id}/review` — 200 + persists `identified_vulnerabilities` to `BlueprintVersion.vulnerabilities`; 404 cross-workspace; 502 (not 500) when LLM output stays invalid

- **T23 — Hurdle generator + chronicle** (`app/agents/hurdle_generator.py`, `chronicle.py`, `prompts/hurdle_generation.md`)
  - `build_vital_signs(state, kpis)` — §6 Step 1 snapshot (burn rate, runway, cash, concentration, CAC/LTV/churn, MRR, month)
  - `HurdleGenerator.generate` → Format B `HurdleEvent` (`app/schemas/hurdle.py`), `clamp=True`, auto-records `ChronicleEntry`
  - `Chronicle` narrative memory — actor continuity (actor from Month 4 consistent in Month 8), lossless `to_dict`/`from_dict`

- **T24 — Strategist** (`app/agents/strategist.py` + `prompts/strategic_options.md`)
  - `propose_options` — 2–4 distinct options via bridge against `StrategicOptionList` (min 2 / max 4 enforced)
  - `project_option` — PURE deterministic 12-month engine projection (reuses `tick`/`apply_event`, no LLM, no reimplemented math); honestly reports death when cash goes negative
  - `advise` — options + aligned `OptionProjection`s

### Verification (Checkpoint C)

- `cd backend && pytest` → **202 passed** (incl. 50 phase-4 unit + integration tests)
- `cd backend && ruff check app tests && mypy app` → **clean** (also fixed pre-existing mypy errors in `app/services/blueprint_service.py` and model column typing)
- No `openai` imports anywhere under `app/agents/` except `openai_compat.py`
- No API key: factory returns `MockProvider`; strategist REPL check shows distinct projections per option; chronicle actor continuity confirmed across consecutive hurdle generations

## How to run checks

```bash
cd backend
.venv/bin/python -m pytest          # full suite
.venv/bin/ruff check app tests      # lint
.venv/bin/mypy app                  # types
```

Full-stack (requires Docker): `docker compose up -d` then `curl localhost:8000/health`.

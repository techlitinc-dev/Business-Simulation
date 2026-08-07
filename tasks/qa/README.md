# The Forge — Automated QA Guide (ZERO-HUMAN-INTERVENTION)

This directory contains a fully automated, self-executing test suite for the
Business Simulation ("The Forge") monorepo. Every phase and every module is
covered by a **Self-Executing Test Card** (7 fields), and the entire guide
reduces to **ONE command**:

```bash
./orchestrator/run_qa.sh --env qa --build
```

Run with `--help` for all options. The orchestrator runs the 7 phases in
sequence, writes a JSON phase summary after every phase, and exits non-zero on
any phase that fails its Go/No-Go gate. No human decision points anywhere:
every instruction below is deterministic, every expected output is a boolean
assertion, and every failure path specifies retry / mark / rollback behavior.

## Layout

| Path | Purpose |
|---|---|
| `README.md` | This file |
| `orchestrator/run_qa.sh` | **Master Test Orchestrator** — the one command |
| `orchestrator/run_phase.sh` | Phase runner shared by the orchestrator (isolation, retries, JSON summary) |
| `orchestrator/assert_lib.sh` | Assertion / retry / summary library |
| `cards/phase-1-unit.md` | **Phase 1** — unit/module isolation (P1T001–P1T024) |
| `cards/phase-2-integration.md` | **Phase 2** — integration & data contracts (P2T001–P2T016) |
| `cards/phase-3-e2e.md` | **Phase 3** — end-to-end workflows (P3T001–P3T012) |
| `cards/phase-4-performance.md` | **Phase 4** — performance & load (P4T001–P4T011) |
| `cards/phase-5-security.md` | **Phase 5** — security & compliance (P5T001–P5T016) |
| `cards/phase-6-production.md` | **Phase 6** — production readiness / smoke (P6T001–P6T009) |
| `cards/phase-7-continuous.md` | **Phase 7** — continuous validation (P7T001–P7T006) |
| `fixtures/fixtures.md` | Mock/fixture data definitions (C) |
| `fixtures/env-matrix.md` | Environment configuration matrix (D) |
| `rollback-and-recovery.md` | Rollback & recovery procedures (E) |
| `go-no-go-matrix.md` | Final Go/No-Go decision matrix (F) |

## Card anatomy

```
TEST CARD: [Phase] → [Module] → [Test ID]
1. TRIGGER          — what starts the test
2. PRE-CONDITIONS   — exact system state
3. AI INSTRUCTIONS  — deterministic, branchless commands (IF X THEN Y ELSE Z)
4. INPUT DATA       — exact payloads / utterances / requests
5. EXPECTED OUTPUT  — ASSERT [condition] == [value] (boolean checks only)
6. CLEANUP          — exact reset commands
7. NEXT TEST ID     — the card that runs automatically after this one
```

## Fixture convention (important)

- `fixtures/blueprint_golden.json` is the **only** blueprint whose baseline
  survives all 24 months at every seed. Cards that assert a baseline run
  `status == "completed"` MUST create their blueprint from this fixture.
- `fixtures/blueprint_valid.json` passes schema validation but dies at month 12
  at every seed — use it only for validation/422 tests, never for completion
  assertions. The seeded demo blueprints (SaaSFlow/BrewBox/ConsultPro) also die
  at month 12 with seed 42; use the golden fixture for smoke journeys.
- Register returns `UserOut` (no tokens): every card helper registers
  (201/409) **then logs in** to obtain the access token.

## AI Tester rules (mandatory)

1. **No decision points.** Every instruction is deterministic; every branch is
   written `IF [X] THEN [Y] ELSE [Z]`.
2. **Verifiable only.** Every EXPECTED OUTPUT is a boolean `ASSERT` an AI can
   execute (HTTP status, JSON field equality, regex match, command exit code).
3. **Self-healing.** On failure: retry 2x with 2s/4s backoff; if still failing
   on a **non-deterministic** check mark `FLAKY` and continue; on a
   **deterministic** check mark `FAILED` and trigger the card's rollback
   procedure (see `rollback-and-recovery.md`).
4. **State management.** Setup before test 1 (`P1T001`), teardown after the
   last test; each phase runner verifies a clean environment before starting.
5. **Chaining.** `NEXT TEST ID` forms one unbroken chain P1T001 → P7T006.
   The orchestrator aborts only on a phase-level NO-GO.
6. **Reporting.** After every phase the orchestrator emits JSON:
   `{"phase": "...", "tests_run": N, "passed": N, "failed": N, "blocked": N,
   "total_time_ms": N, "go_no_go": "GO"|"NO-GO"}`.
7. **One command.** `./orchestrator/run_qa.sh` runs everything unattended.

## Phase gates (see go-no-go-matrix.md)

| Phase | Gate (exit 0 required) |
|---|---|
| 1 Unit | passed == tests_run, failed == 0 |
| 2 Integration | passed == tests_run, failed == 0 |
| 3 E2E | passed == tests_run, failed == 0 |
| 4 Performance | passed == tests_run, failed == 0 (thresholds hard-coded in cards) |
| 5 Security | passed == tests_run, failed == 0 |
| 6 Production | passed == tests_run, failed == 0 |
| 7 Continuous | passed == tests_run, failed == 0 (auto-rollback on fail) |

## Module coverage index

Backend modules (unit + integration + E2E): `app/engine/*`
(state, financials, market, loop, events, metrics), `app/agents/*`
(llm base/factory/openai_compat, bridge, forge, hurdle_generator, strategist,
post_mortem, ghost, chronicle), `app/services/*` (auth, workspace, blueprint,
simulation, report, optimization, billing, metering, scenario, ghost, api_key,
admin), `app/api/v1/endpoints/*` (auth, users, workspaces, blueprints,
simulations, reports, scenarios, leaderboard, billing, webhooks, api_keys,
admin, ws), `app/workers/*` (monte_carlo, email_tasks), `app/core/*`
(config, security, exceptions, rate_limit, audit), `app/utils/*` (ids, pdf,
email, seed), `app/main.py`, `app/db/*`.

Frontend modules (unit): stores (auth, workspace, simulation, blueprint,
billing, notifications), lib (api-client, ws, utils, constants, toast), test
setup, router.

End-to-end journeys (Phase 3): auth → onboarding → blueprint → simulation →
war room → report → export/share → marketplace → ghost → leaderboard → billing
→ settings → admin.

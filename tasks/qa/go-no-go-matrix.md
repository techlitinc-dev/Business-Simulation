# Final Go/No-Go Decision Matrix (Deliverable F)

The orchestrator computes a single verdict after Phase 7. No human judgment is
involved; the matrix below is the complete decision procedure, and the
orchestrator's `emit_go_no_go` implements it.

## Per-phase gate (computed by `run_phase.sh`)

```
phase_go = (failed == 0) AND (blocked == 0) AND (passed == tests_run)
```

| Phase | Card range | Gate |
|---|---|---|
| 1 Unit | P1T001–P1T024 | all pass |
| 2 Integration | P2T001–P2T016 | all pass |
| 3 E2E | P3T001–P3T012 | all pass |
| 4 Performance | P4T001–P4T011 | all pass (thresholds in cards) |
| 5 Security | P5T001–P5T016 | all pass |
| 6 Production | P6T001–P6T009 | all pass |
| 7 Continuous | P7T001–P7T006 | all pass |

`FLAKY` cards count as `blocked` → the phase gate fails → NO-GO. A card marked
FLAKY twice in a row is escalated to FAILED and triggers the phase's rollback
procedure.

## Overall decision table

| Condition | Verdict | Action |
|---|---|---|
| All 7 phases GO | **GO** | Promote release; keep Phase 7 watch loop running in production |
| Any phase NO-GO (deterministic failure) | **NO-GO** | Block promotion; run R1 (rollback) if the failure was in Phase 6/7; file the failing card IDs |
| Phase 7 watch loop: 2 consecutive failures | **NO-GO + auto-rollback** | Trigger R1, then re-run the failed checks |
| Preflight fails (missing tool/venv) | **ABORT (exit 1)** | Fix environment, re-run orchestrator |
| Build/deploy step fails | **ABORT (exit 3)** | Investigate build; no tests ran |

## Go/No-Go JSON (written by the orchestrator)

```json
{
  "overall_verdict": "GO",
  "env": "qa",
  "results_dir": "tasks/qa/qa-results/20260807-101500"
}
```

Per-phase summary lines are appended to `summary.jsonl`:

```jsonl
{"phase": "unit", "tests_run": 24, "passed": 24, "failed": 0, "blocked": 0, "total_time_ms": 8200, "go_no_go": "GO"}
{"phase": "integration", "tests_run": 16, "passed": 16, "failed": 0, "blocked": 0, "total_time_ms": 21400, "go_no_go": "GO"}
...
```

## Go threshold summary

- **Unit coverage gates** (from CI): engine ≥ 90%, API integration ≥ 70%.
- **Performance thresholds**: engine baseline < 100 ms; API p95 < 200 ms;
  p99 < 500 ms; 50-run throughput all 201; MC 100 runs < 30 s; backend RSS
  < 1.5 GB; bursts yield 429 (not 5xx).
- **Security**: zero 5xx on any attack probe; all privilege escalations
  blocked; audit rows present for every mutation; no secrets in metrics/schema.
- **Production**: `/health` 200 always; `/ready` 200 with db+redis ok;
  HSTS on; backups valid and restorable; migration round-trip clean.
- **Continuous**: watch loop green; auto-rollback triggers only on real
  regressions.

## Human intervention points (none required)

By design there are **zero** required human interventions. The only
non-automated inputs are initial environment provisioning (installing Docker,
secrets in `.env`) which the orchestrator's preflight validates and fails
loudly on — it never prompts.

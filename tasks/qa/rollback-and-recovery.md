# Rollback & Recovery Procedures (Deliverable E)

Every rollback is deterministic and executable by an AI with no human input.
Each procedure lists: trigger condition, exact commands, and verification.

## R1 — Image / release rollback (used by Phase 7 auto-rollback)

**Trigger:** P7T001–P7T004 fail 2 consecutive watch cycles, or any
deterministic Phase 6/7 card fails after 2 retries.

```bash
# 1. Stop the app services (keep Postgres + Redis data intact).
docker compose -f docker-compose.prod.yml stop backend worker frontend

# 2. Swap to the previous release tag (env-driven; no human input).
export BACKEND_IMAGE_TAG=<previous-tag>          # resolved by the pipeline
export FRONTEND_IMAGE_TAG=<previous-tag>
docker compose -f docker-compose.prod.yml pull backend frontend

# 3. Bring the previous release up (no-deps: DB/Redis untouched).
docker compose -f docker-compose.prod.yml up -d --no-deps backend worker frontend

# 4. Wait for green probes.
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost/health)
  [ "$code" = 200 ] && break
  sleep 5
done
curl -sf http://localhost/ready | grep -q '"status":"ready"'

# 5. Re-run the failed assertion (self-healing verification).
#    If it passes, the rollback is COMPLETE. If it still fails after 3
#    rollback attempts, mark the phase NO-GO and halt the orchestrator.
```

**Verification:** `curl -s localhost/health` returns `{"status":"ok",...}`,
`curl -s localhost/ready` returns `"checks":{"db":"ok","redis":"ok"}`.

## R2 — Database restore (used by P6T006 drill and real incidents)

**Trigger:** data corruption, failed migration, or manual restore request.

```bash
# 1. Pick the newest backup that predates the incident.
BACKUP=$(ls -t backups/forge-*.sql.gz | head -1)

# 2. Restore into Postgres (destructive — only after the incident is confirmed).
gunzip -c "$BACKUP" | \
  docker compose -f docker-compose.prod.yml exec -T postgres psql -U forge forge

# 3. Verify row counts match the pre-incident baseline.
docker compose -f docker-compose.prod.yml exec -T postgres psql -U forge forge \
  -tAc "SELECT count(*) FROM users; SELECT count(*) FROM workspaces;"
```

**Verification:** counts non-zero and consistent with the backup timestamp.

## R3 — Migration rollback (used by P6T008)

**Trigger:** `alembic upgrade head` fails, or a Phase 6/7 assertion fails right
after a deploy that included migrations.

```bash
docker compose -f docker-compose.prod.yml exec -T backend alembic downgrade -1
# After confirming the previous revision works:
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
```

**Verification:** `alembic current` returns the expected revision; `/ready`
200.

## R4 — Dependency recovery (used by P6T007)

**Trigger:** `/ready` returns 503 with `checks.db` or `checks.redis` = error.

```bash
docker compose -f docker-compose.prod.yml start redis
docker compose -f docker-compose.prod.yml start postgres
```

**Verification:** `/ready` returns 200 within 60s. `/health` never goes down
during this procedure (liveness is independent of dependencies by design).

## R5 — Self-healing loop (Phase 7 watch cycles)

The continuous runner repeats the synthetic checks (P7T001–P7T004) every
`P7_CYCLE_SLEEP` seconds for `P7_MAX_CYCLES` cycles:

| Consecutive failures | Action |
|---|---|
| 1 | Retry the cycle (backoff 2s, 4s, then mark FLAKY) |
| 2 | Trigger R1 (rollback) |
| 3+ | Halt; phase NO-GO; orchestrator exits 2 |

Non-deterministic checks (latency, WS timing) may be marked FLAKY and
continue; deterministic checks (status codes, JSON shapes) that fail twice
always trigger rollback.

## R6 — Environment reset between phases

The orchestrator's `reset_env` runs before every phase:

```bash
docker compose -f docker-compose.yml down -v --remove-orphans   # qa only
docker compose -f docker-compose.prod.yml down -v --remove-orphans   # staging only
rm -rf backend/.pytest_cache backend/.coverage   # all envs
```

**Production (`--env production`) NEVER tears down the live stack.** `reset_env`
only clears pytest caches and verifies `/health` is 200 — Phases 6-7 assume an
already-deployed stack (see `env-matrix.md`). This is a safety invariant: QA
must never be able to destroy a production deployment.

**Verification:** qa/staging — `docker ps` shows zero forge containers before
the next phase starts. production — `http://localhost/health` returns 200.

## Incident log

Every rollback event is appended (by the orchestrator) to
`qa-results/<ts>/rollback.log` with: timestamp, trigger card, procedure id,
command output tail, and verification result.

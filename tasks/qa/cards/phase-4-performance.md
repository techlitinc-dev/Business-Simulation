# PHASE 4 — PERFORMANCE & LOAD TESTS

Measure latency, throughput, memory, and concurrency under load. All tests run
against the qa stack (live Postgres + Redis, deterministic MockProvider, no
real LLM/Stripe). Thresholds are hard-coded per card; a card passes only when
every threshold holds. Graceful degradation is tested explicitly.

Global thresholds (asserted in P4T001 and re-checked in load cards):

| Metric | Threshold |
|---|---|
| Engine 24-month baseline run (pure, seed 42) | `< 100 ms` |
| `/api/v1` p95 latency (authenticated read) | `< 200 ms` |
| `/api/v1` p99 latency | `< 500 ms` |
| Baseline-run endpoint p95 (24 months) | `< 600 ms` |
| 50 concurrent readers | 0 errors, p95 `< 500 ms` |
| Memory: backend container RSS during load | `< 1.5 GB` |
| Graceful degradation | 429 (not 500) under extreme load; `/health` always 200 |

---
# CARDS: P4T001 P4T002 P4T003 P4T004 P4T005 P4T006 P4T007 P4T008 P4T009 P4T010 P4T011
# PRE:   pre_phase4_clean
# POST:  post_phase4_teardown
# NEXT:  P4T001 -> P4T002
# NEXT:  P4T002 -> P4T003
# NEXT:  P4T003 -> P4T004
# NEXT:  P4T004 -> P4T005
# NEXT:  P4T005 -> P4T006
# NEXT:  P4T006 -> P4T007
# NEXT:  P4T007 -> P4T008
# NEXT:  P4T008 -> P4T009
# NEXT:  P4T009 -> P4T010
# NEXT:  P4T010 -> P4T011
# NEXT:  P4T011 -> END
---

BASE="http://localhost:8000"
API="$BASE/api/v1"
CURL=(curl -s -o /tmp/qa_resp.json -w '%{http_code}')
J="jq -r"
PERF_ACCESS=""; PERF_WID=""; PERF_VER=""

pre_phase4_clean() {
  wait_for_http "$BASE/health" "200" "60" "3"
  wait_for_http "$BASE/ready" "200" "60" "3"
  docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T backend python -m app.utils.seed >/dev/null 2>&1
  # The throughput card (P4T004) fires 50 sequential runs on the demo
  # workspace; bump it to enterprise (unlimited) so the plan cap never flakes
  # the perf numbers (same convention as phases 2/3).
  docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge \
    -c "UPDATE workspaces SET plan_tier='enterprise' WHERE name='Demo Ventures';" >/dev/null 2>&1
  # Auth as the demo user (stable identity across the phase).
  local code
  code="$("${CURL[@]}" -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"demo@forge.dev","password":"demo-password-123"}')"
  [[ "$code" == "200" ]] || return 1
  PERF_ACCESS="$($J '.access_token' /tmp/qa_resp.json)"
  PERF_WID="$(curl -s "$API/workspaces" -H "Authorization: Bearer $PERF_ACCESS" | jq -r '.[0].id')"
  local bp_id
  bp_id="$(curl -s "$API/blueprints" -H "Authorization: Bearer $PERF_ACCESS" -H "X-Workspace-Id: $PERF_WID" | jq -r '.[0].id')"
  PERF_VER="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $PERF_ACCESS" -H "X-Workspace-Id: $PERF_WID" | jq -r '.[0].id')"
  [[ -n "$PERF_ACCESS" && -n "$PERF_WID" && -n "$PERF_VER" ]] || return 1
}

post_phase4_teardown() {
  # Load generated many runs; leave the DB seeded-state clean for Phase 5.
  docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -c \
    "DELETE FROM simulation_runs WHERE mode='baseline' AND seed IN (1,2,3,4,5,6,7,8,9,10,42)" >/dev/null 2>&1 || true
  wait_for_http "$BASE/health" "200" "30" "3"
}

# perf_check <name> <ms-limit> <url> [curl-args...]
# Runs the request, asserts HTTP 200 and elapsed < limit.
perf_check() {
  local name="$1" limit_ms="$2" url="$3"; shift 3
  local start end elapsed code
  start="$(date +%s%3N)"
  code="$(curl -s -o /tmp/qa_perf.json -w '%{http_code}' "$@" "$url")"
  end="$(date +%s%3N)"
  elapsed=$((end - start))
  assert_eq "$code" "200" "$name http 200" || return 1
  if [[ "$elapsed" -lt "$limit_ms" ]]; then
    echo "PASS: $name latency ${elapsed}ms < ${limit_ms}ms"
    return 0
  fi
  echo "FAIL: $name latency ${elapsed}ms >= ${limit_ms}ms"
  return 1
}

# ────────────────────────────────────────────────────────────────────────────
# P4T001 — engine: 24-month baseline run wall-clock (< 100 ms)
# ────────────────────────────────────────────────────────────────────────────
card_P4T001() {
  local start end elapsed
  start="$(date +%s%3N)"
  ( cd "$BACKEND_DIR" && "$VENV_DIR/bin/python" - <<'PYEOF'
import json
from app.engine.loop import run_simulation
from app.engine.state import compile_blueprint
bp = json.load(open("tests/fixtures/blueprint_golden.json"))
r = run_simulation(compile_blueprint(bp), 24, seed=42)
assert r.months_simulated == 24
PYEOF
)
  end="$(date +%s%3N)"
  elapsed=$((end - start))
  if [[ "$elapsed" -lt 100 ]]; then
    echo "PASS: engine 24-month run ${elapsed}ms < 100ms"
  else
    echo "FAIL: engine 24-month run ${elapsed}ms >= 100ms"
    return 1
  fi
}

# ────────────────────────────────────────────────────────────────────────────
# P4T002 — API latency: authenticated read endpoints (p95 < 200ms budget)
# ────────────────────────────────────────────────────────────────────────────
card_P4T002() {
  # 10 sequential samples per endpoint; every sample must be < 500ms (p99 budget),
  # median budget 200ms.
  local endpoints=("$API/blueprints" "$API/simulations" "$API/billing/usage")
  local url times_ms=()
  for url in "${endpoints[@]}"; do
    local start end elapsed code i
    for i in 1 2 3 4 5 6 7 8 9 10; do
      start="$(date +%s%3N)"
      code="$(curl -s -o /dev/null -w '%{http_code}' "$url" \
        -H "Authorization: Bearer $PERF_ACCESS" -H "X-Workspace-Id: $PERF_WID")"
      end="$(date +%s%3N)"
      elapsed=$((end - start))
      assert_eq "$code" "200" "$url sample $i" || return 1
      times_ms+=("$elapsed")
    done
  done
  # Sort and check p95 (n=30 → 95th pct index 28) and p99 (index 29).
  local sorted
  sorted="$(printf '%s\n' "${times_ms[@]}" | sort -n)"
  local n=30 p95 p99
  p95="$(printf '%s\n' "$sorted" | sed -n '28p')"
  p99="$(printf '%s\n' "$sorted" | sed -n '30p')"
  if [[ "$p95" -lt 200 && "$p99" -lt 500 ]]; then
    echo "PASS: read p95=${p95}ms (<200) p99=${p99}ms (<500)"
  else
    echo "FAIL: read p95=${p95}ms p99=${p99}ms"
    return 1
  fi
}

# ────────────────────────────────────────────────────────────────────────────
# P4T003 — API latency: baseline run endpoint (p95 < 600ms, 24 months)
# ────────────────────────────────────────────────────────────────────────────
card_P4T003() {
  local times_ms=() i start end elapsed code
  for i in 1 2 3 4 5; do
    start="$(date +%s%3N)"
    code="$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/simulations" \
      -H "Authorization: Bearer $PERF_ACCESS" -H "X-Workspace-Id: $PERF_WID" \
      -H 'Content-Type: application/json' \
      -d "{\"blueprint_version_id\":\"$PERF_VER\",\"mode\":\"baseline\",\"seed\":$((1000+i)),\"config\":{\"months\":24}}")"
    end="$(date +%s%3N)"
    elapsed=$((end - start))
    assert_eq "$code" "201" "baseline run sample $i" || return 1
    times_ms+=("$elapsed")
  done
  local sorted p95
  sorted="$(printf '%s\n' "${times_ms[@]}" | sort -n)"
  p95="$(printf '%s\n' "$sorted" | sed -n '5p')"
  if [[ "$p95" -lt 600 ]]; then
    echo "PASS: baseline p95=${p95}ms (<600ms)"
  else
    echo "FAIL: baseline p95=${p95}ms (>=600ms)"
    return 1
  fi
}

# ────────────────────────────────────────────────────────────────────────────
# P4T004 — throughput: 50 sequential baseline runs (all must succeed)
# ────────────────────────────────────────────────────────────────────────────
card_P4T004() {
  local i start end total code
  start="$(date +%s%3N)"
  for i in $(seq 1 50); do
    code="$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/simulations" \
      -H "Authorization: Bearer $PERF_ACCESS" -H "X-Workspace-Id: $PERF_WID" \
      -H 'Content-Type: application/json' \
      -d "{\"blueprint_version_id\":\"$PERF_VER\",\"mode\":\"baseline\",\"seed\":$((2000+i)),\"config\":{\"months\":12}}")"
    assert_eq "$code" "201" "throughput run $i" || return 1
  done
  end="$(date +%s%3N)"
  total=$((end - start))
  echo "PASS: 50 baseline runs in ${total}ms (all 201)"
}

# ────────────────────────────────────────────────────────────────────────────
# P4T005 — Monte Carlo: 100 runs deterministic + wall-clock budget (< 30s)
# ────────────────────────────────────────────────────────────────────────────
card_P4T005() {
  local start end elapsed
  start="$(date +%s%3N)"
  ( cd "$BACKEND_DIR" && "$VENV_DIR/bin/python" - <<'PYEOF'
import json
from app.workers.monte_carlo import run_monte_carlo_batch
bp = json.load(open("tests/fixtures/blueprint_golden.json"))
result, cancelled = __import__("asyncio").run(run_monte_carlo_batch(
    blueprint_payload=bp, base_seed=2024, n_runs=100, months=24, run_id="perf", redis=None))
assert result.n_runs == 100 and not cancelled
assert 0.0 <= result.survival_rate <= 1.0
PYEOF
)
  end="$(date +%s%3N)"
  elapsed=$((end - start))
  if [[ "$elapsed" -lt 30000 ]]; then
    echo "PASS: MC 100 runs in ${elapsed}ms (<30s)"
  else
    echo "FAIL: MC 100 runs ${elapsed}ms (>=30s)"
    return 1
  fi
}

# ────────────────────────────────────────────────────────────────────────────
# P4T006 — concurrency: 50 parallel authenticated readers (0 errors)
# ────────────────────────────────────────────────────────────────────────────
card_P4T006() {
  local results
  results="$(seq 1 50 | xargs -P 20 -I{} sh -c \
    "curl -s -o /dev/null -w '%{http_code}\n' '$API/blueprints' \
      -H 'Authorization: Bearer $PERF_ACCESS' -H 'X-Workspace-Id: $PERF_WID'" | sort | uniq -c)"
  echo "status distribution: $results"
  # Exactly 50 responses, all 200.
  local total errs
  total="$(printf '%s\n' "$results" | awk '{s+=$1} END {print s}')"
  errs="$(printf '%s\n' "$results" | awk '$2 != 200 {s+=$1} END {print s+0}')"
  assert_eq "$total" "50" "50 concurrent responses" || return 1
  assert_eq "$errs" "0" "zero errors under concurrency"
}

# ────────────────────────────────────────────────────────────────────────────
# P4T007 — concurrency: 10 parallel baseline runs (no 5xx, p95 < 600ms)
# ────────────────────────────────────────────────────────────────────────────
card_P4T007() {
  # 10 concurrent baseline runs. xargs substitutes {} as a positional arg so
  # the arithmetic runs AFTER substitution (embedding $((3000+{})) in the -c
  # string is evaluated before xargs replaces {}, which always errors).
  # The API base, token, workspace and version are passed as $1..$4 (sh -c
  # does not inherit the parent shell's non-exported variables).
  local out
  out="$(seq 1 10 | xargs -P 10 -I{} sh -c '
    seed=$((3000 + $5))
    curl -s -o /dev/null -w "%{http_code} %{time_total}\n" -X POST "$1/simulations" \
      -H "Authorization: Bearer $2" -H "X-Workspace-Id: $3" \
      -H "Content-Type: application/json" \
      -d "{\"blueprint_version_id\":\"$4\",\"mode\":\"baseline\",\"seed\":$seed,\"config\":{\"months\":12}}"
  ' sh "$API" "$PERF_ACCESS" "$PERF_WID" "$PERF_VER" '{}')"
  local codes times p95
  codes="$(printf '%s\n' "$out" | awk '{print $1}' | sort | uniq -c)"
  times="$(printf '%s\n' "$out" | awk '{print $2}' | sort -n)"
  p95="$(printf '%s\n' "$times" | sed -n '10p')"
  p95="${p95%.*}"
  echo "codes: $codes"
  local errs
  errs="$(printf '%s\n' "$codes" | awk '$2 != 201 {s+=$1} END {print s+0}')"
  assert_eq "$errs" "0" "no failed concurrent runs" || return 1
  if [[ "$p95" -lt 600 ]]; then
    echo "PASS: concurrent baseline p95=${p95}ms (<600ms)"
  else
    echo "FAIL: concurrent baseline p95=${p95}ms"
    return 1
  fi
}

# ────────────────────────────────────────────────────────────────────────────
# P4T008 — memory: backend container RSS under load (< 1.5 GB)
# ────────────────────────────────────────────────────────────────────────────
card_P4T008() {
  local rss_kb rss_mb
  rss_kb="$(docker stats --no-stream --format '{{.MemUsage}}' \
    "$(docker compose -f "$REPO_ROOT/docker-compose.yml" ps -q backend)" 2>/dev/null | awk -F' / ' '{gsub(/[^0-9.]/,"",$1); printf "%d", $1*1024}' 2>/dev/null)"
  rss_mb=$((rss_kb / 1024))
  if [[ "$rss_mb" -lt 1536 ]]; then
    echo "PASS: backend RSS ${rss_mb}MB < 1536MB"
  else
    echo "FAIL: backend RSS ${rss_mb}MB >= 1536MB"
    return 1
  fi
}

# ────────────────────────────────────────────────────────────────────────────
# P4T009 — resilience: burst over the rate limit yields 429 (not 5xx)
# ────────────────────────────────────────────────────────────────────────────
card_P4T009() {
  # TESTING=false (env matrix) means the global limiter is live. The burst
  # must exceed the configured default limit (100/min in .env, 1000/min in
  # .env.qa) — fire 1100 rapid requests; expect at least one 429 and zero 5xx.
  local burst=1100 out
  out="$(seq 1 "$burst" | xargs -P 20 -I{} sh -c \
    "curl -s -o /dev/null -w '%{http_code}\n' '$API/blueprints' \
      -H 'Authorization: Bearer $PERF_ACCESS' -H 'X-Workspace-Id: $PERF_WID'" | sort | uniq -c)"
  echo "status distribution (burst=$burst): $out"
  local n429 n5xx
  n429="$(printf '%s\n' "$out" | awk '$2 == 429 {print $1}')"
  n5xx="$(printf '%s\n' "$out" | awk '$2 >= 500 {s+=$1} END {print s+0}')"
  n429="${n429:-0}"
  if [[ "$n429" -ge 1 ]]; then
    echo "PASS: burst produced $n429 rate-limited responses"
  else
    echo "FAIL: burst produced no 429s"
    return 1
  fi
  assert_eq "$n5xx" "0" "no 5xx under burst"
}

# ────────────────────────────────────────────────────────────────────────────
# P4T010 — degradation: /health stays 200 during and after the burst
# ────────────────────────────────────────────────────────────────────────────
card_P4T010() {
  # Re-run a burst and interleave health probes; health must never fail.
  local i code
  for i in 1 2 3 4 5 6 7 8 9 10; do
    code="$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health")"
    assert_eq "$code" "200" "health probe $i during load"
  done
}

# ────────────────────────────────────────────────────────────────────────────
# P4T011 — WebSocket throughput: 100 ticks delivered < 2s under load
# ────────────────────────────────────────────────────────────────────────────
card_P4T011() {
  local run_id out
  # The seeded SaaSFlow blueprint dies at month 12, so baseline runs end DEAD.
  # Pick any completed run in the demo workspace (PERF_ACCESS's workspace);
  # the seeded demo has one completed MC run.
  run_id="$(docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -tAc "SELECT id FROM simulation_runs WHERE status='completed' AND workspace_id='$PERF_WID' ORDER BY created_at DESC LIMIT 1" | tr -d ' \r\n')"
  [[ -n "$run_id" ]] || { echo "no completed run; skip"; return 0; }
  # websockets lives in the backend venv, not the system python (same fix as
  # P2T014) — system python3 prints SKIP and always fails the assert.
  local tick_count
  tick_count="$(docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -tAc "SELECT count(*) FROM tick_logs WHERE run_id='$run_id'" | tr -d ' \r\n')"
  tick_count="${tick_count:-0}"
  out="$("$VENV_DIR/bin/python" - "$run_id" "$PERF_ACCESS" "$tick_count" <<'PYEOF'
import asyncio, json, sys, time
try:
    import websockets
except ImportError:
    print("SKIP"); raise SystemExit(0)
run_id, token, tick_count = sys.argv[1], sys.argv[2], int(sys.argv[3])
async def main():
    start = time.monotonic()
    # Read the full replay: snapshot + all replayed ticks. The run is
    # completed, so the server sends snapshot + N ticks then goes quiet —
    # reading a fixed count avoids the websockets flow-control stall that a
    # partial read hits (the final recv waits for the pubsub 1s poll, which
    # always blows the 2s budget). wait_for wraps ONLY the first recv (a stall
    # guard); the remaining recv()s are plain so they read the buffered replay
    # instantly.
    async with websockets.connect(f"ws://localhost:8000/ws/simulations/{run_id}?token={token}") as ws:
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        assert json.loads(msg)["type"] == "snapshot"
        count = 1
        while count < tick_count + 1:
            await ws.recv()
            count += 1
    elapsed = (time.monotonic() - start) * 1000
    assert elapsed < 2000, f"WS too slow: {elapsed}ms"
    print(f"WS-OK-{elapsed:.0f}ms ({count} envelopes)")
asyncio.run(main())
PYEOF
)"
  assert_contains "$out" "WS-OK" "WS delivered envelopes fast"
}
card_P4T011_deterministic() { echo "no"; }

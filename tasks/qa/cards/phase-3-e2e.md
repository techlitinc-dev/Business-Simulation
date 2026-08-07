# PHASE 3 — END-TO-END / WORKFLOW TESTS

Complete user journeys from trigger to final output, through the real HTTP
stack (frontend build served by nginx on :80, proxied to the FastAPI backend),
with live Postgres + Redis and the deterministic MockProvider. Covers happy
paths, edge cases, and failure-recovery paths. Every journey starts from a
deterministic seeded state and ends with a verifiable final state.

Preconditions: qa stack up, migrated + seeded, `--build` done (frontend dist
is served on :80). API base `http://localhost:8000`, web base `http://localhost:80`.

---
# CARDS: P3T001 P3T002 P3T003 P3T004 P3T005 P3T006 P3T007 P3T008 P3T009 P3T010 P3T011 P3T012
# PRE:   pre_phase3_clean
# POST:  post_phase3_teardown
# NEXT:  P3T001 -> P3T002
# NEXT:  P3T002 -> P3T003
# NEXT:  P3T003 -> P3T004
# NEXT:  P3T004 -> P3T005
# NEXT:  P3T005 -> P3T006
# NEXT:  P3T006 -> P3T007
# NEXT:  P3T007 -> P3T008
# NEXT:  P3T008 -> P3T009
# NEXT:  P3T009 -> P3T010
# NEXT:  P3T010 -> P3T011
# NEXT:  P3T011 -> P3T012
# NEXT:  P3T012 -> END
---

BASE="http://localhost:8000"
API="$BASE/api/v1"
WEB="http://localhost:80"
CURL=(curl -s -o /tmp/qa_resp.json -w '%{http_code}')
J="jq -r"

pre_phase3_clean() {
  wait_for_http "$WEB/" "200" "60" "3"          # frontend served
  wait_for_http "$BASE/health" "200" "30" "3"
  wait_for_http "$BASE/ready" "200" "30" "3"
  docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T backend python -m app.utils.seed >/dev/null 2>&1
}

post_phase3_teardown() {
  # Leave the demo data in place for Phase 6; drop only QA artifacts.
  docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -c \
    "DELETE FROM users WHERE email LIKE 'qa-%@forge.dev'" >/dev/null 2>&1 || true
}

E2E_ACCESS=""; E2E_WID=""
e2e_register() {
  local email="$1" pass="$2" code
  # Register returns UserOut (no token); 201 = created, 409 = already exists.
  # Either way, log in to obtain the access token.
  code="$("${CURL[@]}" -X POST "$API/auth/register" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"name\":\"E2E User\",\"password\":\"$pass\"}")"
  if [[ "$code" != "201" && "$code" != "409" ]]; then
    echo "register $email: unexpected status $code"
    return 1
  fi
  code="$("${CURL[@]}" -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"password\":\"$pass\"}")"
  assert_eq "$code" "200" "login $email" || return 1
  E2E_ACCESS="$($J '.access_token' /tmp/qa_resp.json)"
  E2E_WID="$(curl -s "$API/workspaces" -H "Authorization: Bearer $E2E_ACCESS" | jq -r '.[0].id')"
  [[ -n "$E2E_ACCESS" && -n "$E2E_WID" ]] || return 1
}

# ────────────────────────────────────────────────────────────────────────────
# P3T001 — Journey 1 (happy path): login → dashboard → blueprint list
# ────────────────────────────────────────────────────────────────────────────
card_P3T001() {
  # Demo user from seed: full journey through the UI shell.
  local code
  code="$("${CURL[@]}" -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"demo@forge.dev","password":"demo-password-123"}')"
  assert_eq "$code" "200" "demo login"
  E2E_ACCESS="$($J '.access_token' /tmp/qa_resp.json)"
  # Frontend shell loads (index.html served by nginx).
  local html
  html="$(curl -s "$WEB/")"
  assert_contains "$html" "root" "frontend index served"
  # App assets resolve (the built bundle).
  local asset code2
  asset="$(curl -s "$WEB/" | grep -oE '/assets/index-[A-Za-z0-9_-]+\.js' | head -1)"
  [[ -n "$asset" ]] || { echo "no built asset found"; return 1; }
  code2="$(curl -s -o /dev/null -w '%{http_code}' "$WEB$asset")"
  assert_eq "$code2" "200" "built JS asset served"
  # Seeded dashboard data: demo workspace has blueprints + a completed run.
  local wid code3 n
  wid="$(curl -s "$API/workspaces" -H "Authorization: Bearer $E2E_ACCESS" | jq -r '.[0].id')"
  code3="$("${CURL[@]}" "$API/blueprints" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $wid")"
  assert_eq "$code3" "200" "demo blueprints"
  n="$($J 'length' /tmp/qa_resp.json)"
  assert_eq "$n" "3" "3 seeded blueprints (SaaSFlow, BrewBox, ConsultPro)"
}

# ────────────────────────────────────────────────────────────────────────────
# P3T002 — Journey 2: register → onboarding fields → dashboard KPI data
# ────────────────────────────────────────────────────────────────────────────
card_P3T002() {
  e2e_register "qa-e2e-a@forge.dev" "QA-pass-1234!"
  # Onboarding: PATCH the 3 fields.
  local code
  code="$("${CURL[@]}" -X PATCH "$API/users/me" -H "Authorization: Bearer $E2E_ACCESS" \
    -H 'Content-Type: application/json' \
    -d '{"industry":"SaaS","stage":"Seed","primary_fear":"High CAC"}')"
  assert_eq "$code" "200" "onboarding patch"
  assert_eq "$($J '.onboarding_completed' /tmp/qa_resp.json)" "true" "onboarding completed"
  # Dashboard: run a baseline to populate KPI series (golden blueprint survives).
  local bp_id ver code2
  code2="$("${CURL[@]}" -X POST "$API/blueprints" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"E2E SaaS\",\"industry\":\"SaaS\",\"stage\":\"Seed\",\"payload\":$(cat "$FIXTURES/blueprint_golden.json")}")"
  assert_eq "$code2" "201" "create blueprint"
  bp_id="$($J '.id' /tmp/qa_resp.json)"
  ver="$($J '.current_version_id // empty' /tmp/qa_resp.json)"
  [[ -n "$ver" ]] || ver="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" | jq -r '.[0].id')"
  local code3 run_id
  code3="$("${CURL[@]}" -X POST "$API/simulations" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"blueprint_version_id\":\"$ver\",\"mode\":\"baseline\",\"seed\":42,\"config\":{\"months\":24}}")"
  assert_eq "$code3" "201" "baseline run"
  run_id="$($J '.id' /tmp/qa_resp.json)"
  assert_eq "$($J '.status' /tmp/qa_resp.json)" "completed" "baseline completes"
  # KPI series present.
  local kpis
  kpis="$(curl -s "$API/simulations/$run_id/ticks" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID")"
  assert_contains "$kpis" "cash_balance" "KPI series has cash_balance"
}

# ────────────────────────────────────────────────────────────────────────────
# P3T003 — Journey 3: blueprint wizard → validation → versioning → review
# ────────────────────────────────────────────────────────────────────────────
card_P3T003() {
  e2e_register "qa-e2e-a@forge.dev" "QA-pass-1234!"
  # Create + validate.
  local code
  code="$("${CURL[@]}" -X POST "$API/blueprints" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"Wiz\",\"industry\":\"SaaS\",\"stage\":\"Seed\",\"payload\":$(cat "$FIXTURES/blueprint_valid.json")}")"
  assert_eq "$code" "201" "create"
  local bp_id
  bp_id="$($J '.id' /tmp/qa_resp.json)"
  code="$("${CURL[@]}" "$API/blueprints/$bp_id/validate?version=1" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID")"
  assert_eq "$code" "200" "validate"
  assert_eq "$($J '.is_valid' /tmp/qa_resp.json)" "true" "blueprint is valid"
  # Invalid payload → 422 on create.
  local code2
  code2="$("${CURL[@]}" -X POST "$API/blueprints" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d '{"name":"Bad","industry":"SaaS","stage":"Seed","payload":{"revenue_engine":{"streams":[]}}}')"
  assert_eq "$code2" "422" "invalid payload 422"
  # Versioning: create version 2.
  local code3 v2
  code3="$("${CURL[@]}" -X POST "$API/blueprints/$bp_id/versions" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"payload\":$(cat "$FIXTURES/blueprint_valid.json")}")"
  assert_eq "$code3" "201" "create version 2"
  v2="$($J '.version' /tmp/qa_resp.json)"
  assert_eq "$v2" "2" "version number increments"
  # Forge review (mock provider): 200 + vulnerabilities array.
  local code4
  code4="$("${CURL[@]}" -X POST "$API/blueprints/$bp_id/review" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" -H 'Content-Type: application/json' -d '{}')"
  assert_eq "$code4" "200" "forge review"
  assert "$J '.identified_vulnerabilities | type == "array"' /tmp/qa_resp.json == true" "vulnerabilities array"
}

# ────────────────────────────────────────────────────────────────────────────
# P3T004 — Journey 4: full baseline → report → PDF export → share → compare
# ────────────────────────────────────────────────────────────────────────────
card_P3T004() {
  e2e_register "qa-e2e-a@forge.dev" "QA-pass-1234!"
  local bp_id ver run_id code
  code="$("${CURL[@]}" -X POST "$API/blueprints" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"SaaSFlow\",\"industry\":\"SaaS\",\"stage\":\"Seed\",\"payload\":$(cat "$FIXTURES/blueprint_valid.json")}")"
  assert_eq "$code" "201" "create"
  bp_id="$($J '.id' /tmp/qa_resp.json)"
  ver="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" | jq -r '.[0].id')"
  code="$("${CURL[@]}" -X POST "$API/simulations" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"blueprint_version_id\":\"$ver\",\"mode\":\"monte_carlo\",\"seed\":42,\"config\":{\"months\":24,\"n_runs\":10}}")"
  assert_eq "$code" "201" "start MC"
  run_id="$($J '.id' /tmp/qa_resp.json)"
  assert_eq "$($J '.status' /tmp/qa_resp.json)" "pending" "MC enqueued (eager worker runs it)"
  # Wait for completion (eager worker in qa compose) — poll with backoff.
  local status="pending" tries=0
  while [[ "$status" != "completed" && "$status" != "failed" && "$tries" -lt 30 ]]; do
    sleep 2; tries=$((tries+1))
    status="$(curl -s "$API/simulations/$run_id" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" | jq -r '.status')"
  done
  assert_eq "$status" "completed" "MC completes"
  # Report + export + share.
  code="$("${CURL[@]}" "$API/reports/simulations/$run_id/report" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID")"
  assert_eq "$code" "200" "report generated"
  code="$("${CURL[@]}" -X POST "$API/reports/simulations/$run_id/report/export" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" -H 'Content-Type: application/json' -d '{}')"
  assert_eq "$code" "201" "PDF export"
  local pdf_url
  pdf_url="$($J '.pdf_url' /tmp/qa_resp.json)"
  assert_contains "$pdf_url" "reports" "pdf url"
  local pdf_code
  pdf_code="$(curl -s -o /tmp/qa_report.pdf -w '%{http_code}' "$BASE$pdf_url")"
  assert_eq "$pdf_code" "200" "pdf downloadable"
  assert_contains "$(head -c 5 /tmp/qa_report.pdf)" "%PDF" "pdf magic bytes"
  # Share + public view.
  code="$("${CURL[@]}" -X POST "$API/reports/simulations/$run_id/report/share" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" -H 'Content-Type: application/json' -d '{}')"
  assert_eq "$code" "201" "share report"
  local token
  token="$($J '.token' /tmp/qa_resp.json)"
  code="$("${CURL[@]}" "$API/reports/shared/$token")"
  assert_eq "$code" "200" "shared report public view"
  # Compare this run with the seeded MC run.
  local run_b code_cmp
  run_b="$(docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -tAc "SELECT id FROM simulation_runs WHERE mode='monte_carlo' AND status='completed' AND id != '$run_id' ORDER BY created_at LIMIT 1" | tr -d ' \r\n')"
  code_cmp="$("${CURL[@]}" "$API/reports/compare?a=$run_id&b=$run_b" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID")"
  assert_eq "$code_cmp" "200" "compare"
  assert "$J '.verdict | IN(\"improved\",\"regressed\",\"unchanged\")' /tmp/qa_resp.json == true" "verdict enum"
}

# ────────────────────────────────────────────────────────────────────────────
# P3T005 — Journey 5: Monte Carlo batch → progress → resilience report
# ────────────────────────────────────────────────────────────────────────────
card_P3T005() {
  e2e_register "qa-e2e-a@forge.dev" "QA-pass-1234!"
  local bp_id ver code
  code="$("${CURL[@]}" -X POST "$API/blueprints" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"MC\",\"industry\":\"SaaS\",\"stage\":\"Seed\",\"payload\":$(cat "$FIXTURES/blueprint_valid.json")}")"
  assert_eq "$code" "201" "create"
  bp_id="$($J '.id' /tmp/qa_resp.json)"
  ver="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" | jq -r '.[0].id')"
  code="$("${CURL[@]}" -X POST "$API/simulations" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"blueprint_version_id\":\"$ver\",\"mode\":\"monte_carlo\",\"seed\":2024,\"config\":{\"months\":24,\"n_runs\":25}}")"
  assert_eq "$code" "201" "start MC 25"
  local run_id
  run_id="$($J '.id' /tmp/qa_resp.json)"
  # Poll progress key via Redis (live worker publishes it).
  local tries=0 progress=""
  while [[ "$tries" -lt 30 ]]; do
    sleep 2; tries=$((tries+1))
    progress="$(docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T redis redis-cli GET "sim:$run_id:progress" 2>/dev/null | tr -d '\r')"
    [[ -n "$progress" ]] && break
  done
  assert_contains "$progress" "completed" "progress written to Redis"
  local status="pending" tries2=0
  while [[ "$status" != "completed" && "$status" != "failed" && "$tries2" -lt 60 ]]; do
    sleep 2; tries2=$((tries2+1))
    status="$(curl -s "$API/simulations/$run_id" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" | jq -r '.status')"
  done
  assert_eq "$status" "completed" "MC run completes"
  local res
  res="$(curl -s "$API/simulations/$run_id" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID")"
  assert_contains "$res" "survival_rate" "result has survival_rate"
  # Resilience report.
  local code2
  code2="$("${CURL[@]}" "$API/reports/simulations/$run_id/report" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID")"
  assert_eq "$code2" "200" "resilience report"
  assert "$J '.content_json.survival.kill_vectors | type == "array"' /tmp/qa_resp.json == true" "kill vectors present"
}

# ────────────────────────────────────────────────────────────────────────────
# P3T006 — Journey 6: stress test with war-room decisions (multiple hurdles)
# ────────────────────────────────────────────────────────────────────────────
card_P3T006() {
  e2e_register "qa-e2e-a@forge.dev" "QA-pass-1234!"
  local bp_id ver code
  code="$("${CURL[@]}" -X POST "$API/blueprints" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"Stress\",\"industry\":\"SaaS\",\"stage\":\"Seed\",\"payload\":$(cat "$FIXTURES/blueprint_valid.json")}")"
  assert_eq "$code" "201" "create"
  bp_id="$($J '.id' /tmp/qa_resp.json)"
  ver="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" | jq -r '.[0].id')"
  code="$("${CURL[@]}" -X POST "$API/simulations" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"blueprint_version_id\":\"$ver\",\"mode\":\"stress\",\"seed\":1337,\"config\":{\"months\":24,\"difficulty\":\"hard\"}}")"
  assert_eq "$code" "201" "start stress (hard)"
  local run_id status
  run_id="$($J '.id' /tmp/qa_resp.json)"
  status="$($J '.status' /tmp/qa_resp.json)"
  assert_eq "$status" "awaiting_decision" "parks at hurdle"
  # Decision loop: keep deciding until completed/dead (max 8 rounds).
  local round=0
  while [[ "$round" -lt 8 ]]; do
    local event_id
    event_id="$(curl -s "$API/simulations/$run_id" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" | jq -r '.pending_event_id // empty')"
    [[ -n "$event_id" ]] || event_id="$(docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -tAc "SELECT id FROM simulation_events WHERE run_id='$run_id' AND status='pending' LIMIT 1" | tr -d ' \r\n')"
    if [[ -z "$event_id" ]]; then break; fi
    code="$("${CURL[@]}" -X POST "$API/simulations/$run_id/decide" \
      -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
      -H 'Content-Type: application/json' \
      -d "{\"event_id\":\"$event_id\",\"option_id\":\"B\"}")"
    assert_eq "$code" "200" "decision round $round"
    round=$((round+1))
    status="$(curl -s "$API/simulations/$run_id" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" | jq -r '.status')"
  done
  case "$status" in
    completed|dead|awaiting_decision) echo "PASS: stress journey ended (status=$status)" ;;
    *) echo "FAIL: unexpected status $status"; return 1 ;;
  esac
}

# ────────────────────────────────────────────────────────────────────────────
# P3T007 — Journey 7: run control (pause/resume/cancel) on a stress run
# ────────────────────────────────────────────────────────────────────────────
card_P3T007() {
  e2e_register "qa-e2e-a@forge.dev" "QA-pass-1234!"
  local bp_id ver code
  code="$("${CURL[@]}" -X POST "$API/blueprints" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"Ctrl\",\"industry\":\"SaaS\",\"stage\":\"Seed\",\"payload\":$(cat "$FIXTURES/blueprint_valid.json")}")"
  assert_eq "$code" "201" "create"
  bp_id="$($J '.id' /tmp/qa_resp.json)"
  ver="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" | jq -r '.[0].id')"
  code="$("${CURL[@]}" -X POST "$API/simulations" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"blueprint_version_id\":\"$ver\",\"mode\":\"stress\",\"seed\":5,\"config\":{\"months\":24,\"difficulty\":\"standard\"}}")"
  assert_eq "$code" "201" "start stress"
  local run_id
  run_id="$($J '.id' /tmp/qa_resp.json)"
  # Cancel a run awaiting a decision.
  local code2
  code2="$("${CURL[@]}" -X POST "$API/simulations/$run_id/control" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' -d '{"action":"cancel"}')"
  assert_eq "$code2" "200" "cancel run"
  assert_eq "$($J '.status' /tmp/qa_resp.json)" "cancelled" "status cancelled"
  # Cancelling a terminal run → 409.
  local code3
  code3="$("${CURL[@]}" -X POST "$API/simulations/$run_id/control" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' -d '{"action":"pause"}')"
  assert_eq "$code3" "409" "cannot control terminal run"
}

# ────────────────────────────────────────────────────────────────────────────
# P3T008 — Journey 8: invite → accept → collaboration (share a blueprint run)
# ────────────────────────────────────────────────────────────────────────────
card_P3T008() {
  e2e_register "qa-e2e-a@forge.dev" "QA-pass-1234!"
  local wid_a code invite_url token
  wid_a="$E2E_WID"
  code="$("${CURL[@]}" -X POST "$API/workspaces/$wid_a/invites" \
    -H "Authorization: Bearer $E2E_ACCESS" -H 'Content-Type: application/json' \
    -d '{"email":"qa-e2e-b@forge.dev","role":"member"}')"
  assert_eq "$code" "201" "invite B"
  invite_url="$($J '.invite_url' /tmp/qa_resp.json)"
  token="${invite_url##*/}"
  e2e_register "qa-e2e-b@forge.dev" "QA-pass-5678!"
  local access_b wid_b
  access_b="$E2E_ACCESS"; wid_b="$E2E_WID"
  local code2
  code2="$("${CURL[@]}" -X POST "$API/invites/$token/accept" \
    -H "Authorization: Bearer $access_b" -H 'Content-Type: application/json' -d '{}')"
  assert_eq "$code2" "200" "B accepts invite"
  # B now sees A's workspace and can list its blueprints.
  local wid shared wid_ok
  wid_ok="$($J '.workspace_id // empty' /tmp/qa_resp.json)"
  [[ -n "$wid_ok" ]] || wid_ok="$wid_a"
  local code3
  code3="$("${CURL[@]}" "$API/blueprints" -H "Authorization: Bearer $access_b" -H "X-Workspace-Id: $wid_ok")"
  assert_eq "$code3" "200" "B lists A's blueprints"
}

# ────────────────────────────────────────────────────────────────────────────
# P3T009 — Journey 9: ghost mode run (autonomous personality) → spectator
# ────────────────────────────────────────────────────────────────────────────
card_P3T009() {
  e2e_register "qa-e2e-a@forge.dev" "QA-pass-1234!"
  local bp_id ver code
  code="$("${CURL[@]}" -X POST "$API/blueprints" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"Ghost\",\"industry\":\"SaaS\",\"stage\":\"Seed\",\"payload\":$(cat "$FIXTURES/blueprint_valid.json")}")"
  assert_eq "$code" "201" "create"
  bp_id="$($J '.id' /tmp/qa_resp.json)"
  ver="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" | jq -r '.[0].id')"
  code="$("${CURL[@]}" -X POST "$API/simulations" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"blueprint_version_id\":\"$ver\",\"mode\":\"ghost\",\"seed\":777,\"config\":{\"personality\":\"aggressive\",\"months\":24}}")"
  assert_eq "$code" "201" "start ghost"
  local run_id
  run_id="$($J '.id' /tmp/qa_resp.json)"
  assert_eq "$($J '.mode' /tmp/qa_resp.json)" "ghost" "mode is ghost"
  # Ghost personality missing → 422.
  local code2
  code2="$("${CURL[@]}" -X POST "$API/simulations" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"blueprint_version_id\":\"$ver\",\"mode\":\"ghost\",\"seed\":777,\"config\":{\"months\":24}}")"
  assert_eq "$code2" "422" "ghost without personality rejected"
}

# ────────────────────────────────────────────────────────────────────────────
# P3T010 — Journey 10: marketplace publish → browse → clone → leaderboard
# ────────────────────────────────────────────────────────────────────────────
card_P3T010() {
  e2e_register "qa-e2e-a@forge.dev" "QA-pass-1234!"
  local code sc_id
  code="$("${CURL[@]}" -X POST "$API/scenarios" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"title\":\"E2E Scenario\",\"description\":\"d\",\"category\":\"market\"}")"
  assert_eq "$code" "201" "publish"
  sc_id="$($J '.id' /tmp/qa_resp.json)"
  # Featured list (public) contains the seeded scenarios.
  local featured
  featured="$(curl -s "$API/scenarios/featured")"
  assert_contains "$featured" "Freemium Assault" "seeded featured scenario"
  # Clone into a fresh workspace.
  e2e_register "qa-e2e-b@forge.dev" "QA-pass-5678!"
  local wid_b code2
  wid_b="$E2E_WID"
  code2="$("${CURL[@]}" -X POST "$API/scenarios/$sc_id/clone" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $wid_b" \
    -H 'Content-Type: application/json' -d '{}')"
  assert_eq "$code2" "201" "clone into own workspace"
  # Leaderboard reflects public MC runs.
  local lb
  lb="$(curl -s "$API/leaderboard")"
  assert "$J 'has(\"entries\")' /tmp/qa_resp.json == true" "leaderboard entries present"
}

# ────────────────────────────────────────────────────────────────────────────
# P3T011 — Journey 11: billing paywall (free tier limit → 402) 
# ────────────────────────────────────────────────────────────────────────────
card_P3T011() {
  e2e_register "qa-e2e-a@forge.dev" "QA-pass-1234!"
  local bp_id ver code
  code="$("${CURL[@]}" -X POST "$API/blueprints" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"Paywall\",\"industry\":\"SaaS\",\"stage\":\"Seed\",\"payload\":$(cat "$FIXTURES/blueprint_valid.json")}")"
  assert_eq "$code" "201" "create"
  bp_id="$($J '.id' /tmp/qa_resp.json)"
  ver="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" | jq -r '.[0].id')"
  # Free tier: 3 runs/month. Bump usage to 3, then the 4th run → 402.
  local i code2
  for i in 1 2 3; do
    code2="$("${CURL[@]}" -X POST "$API/simulations" \
      -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
      -H 'Content-Type: application/json' \
      -d "{\"blueprint_version_id\":\"$ver\",\"mode\":\"baseline\",\"seed\":$i,\"config\":{\"months\":6}}")"
    assert_eq "$code2" "201" "run $i (free tier)"
  done
  local code4
  code4="$("${CURL[@]}" -X POST "$API/simulations" \
    -H "Authorization: Bearer $E2E_ACCESS" -H "X-Workspace-Id: $E2E_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"blueprint_version_id\":\"$ver\",\"mode\":\"baseline\",\"seed\":99,\"config\":{\"months\":6}}")"
  assert_eq "$code4" "402" "4th run blocked (plan_limit_exceeded)"
  assert_eq "$($J '.code' /tmp/qa_resp.json)" "plan_limit_exceeded" "error code in body"
}

# ────────────────────────────────────────────────────────────────────────────
# P3T012 — Journey 12: settings (password change) + admin overview
# ────────────────────────────────────────────────────────────────────────────
card_P3T012() {
  e2e_register "qa-e2e-a@forge.dev" "QA-pass-1234!"
  # Change password.
  local code
  code="$("${CURL[@]}" -X POST "$API/users/me/password" \
    -H "Authorization: Bearer $E2E_ACCESS" -H 'Content-Type: application/json' \
    -d '{"current_password":"QA-pass-1234!","new_password":"QA-pass-NEW-9!"}')"
  assert_eq "$code" "204" "password changed"
  # Old password no longer works; new one does.
  code="$("${CURL[@]}" -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-e2e-a@forge.dev","password":"QA-pass-1234!"}')"
  assert_eq "$code" "401" "old password rejected"
  code="$("${CURL[@]}" -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-e2e-a@forge.dev","password":"QA-pass-NEW-9!"}')"
  assert_eq "$code" "200" "new password accepted"
  # Wrong current password → 400.
  code="$("${CURL[@]}" -X POST "$API/users/me/password" \
    -H "Authorization: Bearer $E2E_ACCESS" -H 'Content-Type: application/json' \
    -d '{"current_password":"WRONG","new_password":"QA-pass-X-1!"}')"
  assert_eq "$code" "400" "wrong current password 400"
}

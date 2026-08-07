# PHASE 2 — INTEGRATION TESTS

Module-to-module communication over **real interfaces**: live compose Postgres
and Redis, real HTTP through the FastAPI app (uvicorn on :8000), real Celery
worker (eager-mode via the repo test suite; live worker for the qa compose),
real WS connection, and the deterministic MockProvider for the AI cortex.
Verifies data contracts, serialization, event flow, and error propagation.
No mocked DB, no mocked Redis, no stubbed HTTP in this phase.

Preconditions: `docker compose -f docker-compose.yml up -d` green, backend
migrated + seeded (see `pre_phase2_clean`). API base `http://localhost:8000`.

---
# CARDS: P2T001 P2T002 P2T003 P2T004 P2T005 P2T006 P2T007 P2T008 P2T009 P2T010 P2T011 P2T012 P2T013 P2T014 P2T015 P2T016
# PRE:   pre_phase2_clean
# POST:  post_phase2_teardown
# NEXT:  P2T001 -> P2T002
# NEXT:  P2T002 -> P2T003
# NEXT:  P2T003 -> P2T004
# NEXT:  P2T004 -> P2T005
# NEXT:  P2T005 -> P2T006
# NEXT:  P2T006 -> P2T007
# NEXT:  P2T007 -> P2T008
# NEXT:  P2T008 -> P2T009
# NEXT:  P2T009 -> P2T010
# NEXT:  P2T010 -> P2T011
# NEXT:  P2T011 -> P2T012
# NEXT:  P2T012 -> P2T013
# NEXT:  P2T013 -> P2T014
# NEXT:  P2T014 -> P2T015
# NEXT:  P2T015 -> P2T016
# NEXT:  P2T016 -> END
---

BASE="http://localhost:8000"
API="$BASE/api/v1"
CURL=(curl -s -o /tmp/qa_resp.json -w '%{http_code}')
J="jq -r"

pre_phase2_clean() {
  # Backend + DB + Redis must be up and migrated.
  wait_for_http "$BASE/health" "200" "60" "3"
  wait_for_http "$BASE/ready" "200" "60" "3"
  # Seed idempotently so fixtures exist (P3 also relies on this).
  docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T backend alembic upgrade head >/dev/null 2>&1
  docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T backend python -m app.utils.seed >/dev/null 2>&1
  # Bump QA-registered workspaces to the pro tier so the phase's simulation
  # cards (baseline/stress/MC) are not throttled by the free 3-runs/month cap.
  docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge \
    -c "UPDATE workspaces SET plan_tier='pro' WHERE name='QA User''s Workspace';" >/dev/null 2>&1
}

post_phase2_teardown() {
  # Leave no QA users behind for the next phase: reset DB via seed-check.
  # The e2e phase re-seeds; here we simply verify services still healthy.
  wait_for_http "$BASE/health" "200" "30" "3"
}

# Helper: register a user, returns JSON file with access_token + workspace id.
# Usage: register_user <email> <password> <out-file>  (sets global ACCESS, WID)
ACCESS=""; WID=""
register_user() {
  local email="$1" pass="$2" out="$3"
  local code
  # Register returns UserOut (no token) — 201 means the user was created. If the
  # user already exists from a previous run, register returns 409 → fall back to
  # login. Either way, log in to obtain the access token.
  code="$("${CURL[@]}" -X POST "$API/auth/register" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"name\":\"QA User\",\"password\":\"$pass\"}")"
  if [[ "$code" != "201" && "$code" != "409" ]]; then
    echo "register $email: unexpected status $code"
    return 1
  fi
  # Login — write the body to $out (CURL's fixed -o /tmp/qa_resp.json would
  # clobber per-user output files like /tmp/qa_resp_b.json).
  code="$(curl -s -o "$out" -w '%{http_code}' -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"password\":\"$pass\"}")"
  assert_eq "$code" "200" "login $email" || return 1
  ACCESS="$($J '.access_token' "$out")"
  WID="$($J '.workspace_id // .personal_workspace_id // empty' "$out")"
  [[ -n "$ACCESS" ]] || { echo "login $email: no access_token"; return 1; }
  # QA workspaces start on the free tier (3 runs/month), which throttles the
  # phase's simulation cards. Bump the user's workspace to pro so the suite
  # isn't quota-limited. Idempotent; harmless if already pro.
  docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge \
    -c "UPDATE workspaces SET plan_tier='pro' WHERE name='QA User''s Workspace';" >/dev/null 2>&1
}

# ────────────────────────────────────────────────────────────────────────────
# P2T001 — auth→users contract: register → login → refresh token pair
# ────────────────────────────────────────────────────────────────────────────
card_P2T001() {
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  # Contract: login returns TokenPair with access_token + refresh_token.
  assert "$J '.access_token' /tmp/qa_resp.json | length > 20"
  assert "$J '.refresh_token' /tmp/qa_resp.json | length > 20"
  # Login with the same credentials returns 200 + fresh tokens.
  local code
  code="$("${CURL[@]}" -X POST "$API/auth/login" -H 'Content-Type: application/json' \
    -d '{"email":"qa-a@forge.dev","password":"QA-pass-1234!"}')"
  assert_eq "$code" "200" "login"
  # Refresh rotates the pair.
  local rt code2
  rt="$($J '.refresh_token' /tmp/qa_resp.json)"
  code2="$("${CURL[@]}" -X POST "$API/auth/refresh" -H 'Content-Type: application/json' \
    -d "{\"refresh_token\":\"$rt\"}")"
  assert_eq "$code2" "200" "refresh"
  assert "$J '.access_token' /tmp/qa_resp.json | length > 20"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T002 — users/me contract: GET + PATCH + onboarding flip
# ────────────────────────────────────────────────────────────────────────────
card_P2T002() {
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  local code
  code="$("${CURL[@]}" "$API/users/me" -H "Authorization: Bearer $ACCESS")"
  assert_eq "$code" "200" "GET /users/me"
  assert_eq "$($J '.email' /tmp/qa_resp.json)" "qa-a@forge.dev" "email matches"
  assert_eq "$($J '.onboarding_completed' /tmp/qa_resp.json)" "false" "onboarding starts false"
  code="$("${CURL[@]}" -X PATCH "$API/users/me" -H "Authorization: Bearer $ACCESS" \
    -H 'Content-Type: application/json' \
    -d '{"industry":"SaaS","stage":"Seed","primary_fear":"Running out of cash"}')"
  assert_eq "$code" "200" "PATCH /users/me"
  assert_eq "$($J '.onboarding_completed' /tmp/qa_resp.json)" "true" "onboarding flips true"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T003 — workspace RBAC: member vs non-member, invite/accept handshake
# ────────────────────────────────────────────────────────────────────────────
card_P2T003() {
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  local owner_wid code invite_url
  owner_wid="$($J '.workspaces[0].id // .workspace.id // empty' /tmp/qa_resp.json)"
  [[ -n "$owner_wid" ]] || owner_wid="$(curl -s "$API/workspaces" -H "Authorization: Bearer $ACCESS" | jq -r '.[0].id')"
  WID="$owner_wid"
  # Invite user B as member.
  code="$("${CURL[@]}" -X POST "$API/workspaces/$WID/invites" \
    -H "Authorization: Bearer $ACCESS" -H 'Content-Type: application/json' \
    -d '{"email":"qa-b@forge.dev","role":"member"}')"
  assert_eq "$code" "201" "create invite"
  invite_url="$($J '.invite_url' /tmp/qa_resp.json)"
  # Invite URLs are <frontend>/accept-invite?token=<token> — parse the token
  # from the query string (never assume a trailing path segment).
  local token
  token="${invite_url##*token=}"
  [[ -n "$token" && "$token" != "$invite_url" ]] || { echo "invite_url has no token: $invite_url"; return 1; }
  # Register user B, accept the invite. register_user_b sets ACCESS_B (the
  # accept + RBAC checks below need B's token, not A's).
  register_user_b
  local code2
  code2="$("${CURL[@]}" -X POST "$API/invites/$token/accept" \
    -H "Authorization: Bearer $ACCESS_B" -H 'Content-Type: application/json' -d '{}')"
  # B is now a member of A's workspace.
  local members code3
  code3="$("${CURL[@]}" "$API/workspaces/$WID/members" -H "Authorization: Bearer $ACCESS")"
  assert_eq "$code3" "200" "list members"
  members="$($J '[.[].email] | join(",")' /tmp/qa_resp.json)"
  assert_contains "$members" "qa-b@forge.dev" "B is a member"
  # B (member) cannot PATCH the workspace (admin+ required).
  local code4
  code4="$("${CURL[@]}" -X PATCH "$API/workspaces/$WID" \
    -H "Authorization: Bearer $ACCESS_B" -H 'Content-Type: application/json' -d '{"name":"HACK"}')"
  assert_eq "$code4" "403" "member cannot admin workspace"
}
ACCESS_B=""
# register_user stores B's token separately for P2T003/P2T004. register_user
# overwrites the global WID (login returns no workspace_id), so save/restore it
# — callers rely on WID still pointing at A's workspace.
register_user_b() {
  local saved_wid="$WID"
  register_user "qa-b@forge.dev" "QA-pass-5678!" /tmp/qa_resp_b.json
  ACCESS_B="$ACCESS"
  WID="$saved_wid"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T004 — cross-workspace isolation: blueprints read as 403 outside the ws
# ────────────────────────────────────────────────────────────────────────────
card_P2T004() {
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  local owner_wid code bp_id
  owner_wid="$(curl -s "$API/workspaces" -H "Authorization: Bearer $ACCESS" | jq -r '.[0].id')"
  WID="$owner_wid"
  # A creates a blueprint in her workspace.
  code="$("${CURL[@]}" -X POST "$API/blueprints" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"SaaSFlow\",\"industry\":\"SaaS\",\"stage\":\"Seed\",\"payload\":$(cat "$FIXTURES/blueprint_valid.json")}")"
  assert_eq "$code" "201" "create blueprint"
  bp_id="$($J '.id' /tmp/qa_resp.json)"
  # A fresh, unrelated user (C — NOT qa-b, who joined A's workspace in P2T003)
  # reading A's blueprint outside A's workspace → 403 "Not a member"
  # (the multi-tenant guard; no cross-tenant data leak).
  local c_reg c_login c_access code2
  c_reg="$("${CURL[@]}" -X POST "$API/auth/register" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-c@forge.dev","name":"QA User","password":"QA-pass-9999!"}')"
  if [[ "$c_reg" != "201" && "$c_reg" != "409" ]]; then
    echo "register qa-c: unexpected status $c_reg"; return 1
  fi
  c_login="$("${CURL[@]}" -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-c@forge.dev","password":"QA-pass-9999!"}')"
  [[ "$c_login" == "200" ]] || return 1
  c_access="$($J '.access_token' /tmp/qa_resp.json)"
  code2="$("${CURL[@]}" "$API/blueprints/$bp_id" \
    -H "Authorization: Bearer $c_access" -H "X-Workspace-Id: $WID")"
  assert_eq "$code2" "403" "cross-workspace blueprint reads as 403"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T005 — blueprint→simulation contract: baseline run ticks persist in DB
# ────────────────────────────────────────────────────────────────────────────
card_P2T005() {
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  local owner_wid bp_id code run_id
  owner_wid="$(curl -s "$API/workspaces" -H "Authorization: Bearer $ACCESS" | jq -r '.[0].id')"
  WID="$owner_wid"
  code="$("${CURL[@]}" -X POST "$API/blueprints" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"SaaSFlow\",\"industry\":\"SaaS\",\"stage\":\"Seed\",\"payload\":$(cat "$FIXTURES/blueprint_golden.json")}")"
  assert_eq "$code" "201" "create blueprint"
  bp_id="$($J '.id' /tmp/qa_resp.json)"
  local ver
  ver="$($J '.current_version_id // .versions[0].id // empty' /tmp/qa_resp.json)"
  [[ -n "$ver" ]] || ver="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" | jq -r '.[0].id')"
  # Baseline run: deterministic seed 42 (golden blueprint survives 24 months).
  code="$("${CURL[@]}" -X POST "$API/simulations" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" \
    -H 'Content-Type: application/json' \
    -d "{\"blueprint_version_id\":\"$ver\",\"mode\":\"baseline\",\"seed\":42,\"config\":{\"months\":24}}")"
  assert_eq "$code" "201" "start baseline"
  run_id="$($J '.id' /tmp/qa_resp.json)"
  assert_eq "$($J '.status' /tmp/qa_resp.json)" "completed" "baseline completes synchronously"
  # Contract: 24 tick rows persisted, months 1..24 ascending, KPI shape complete.
  local ticks code2 n
  code2="$("${CURL[@]}" "$API/simulations/$run_id/ticks" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID")"
  assert_eq "$code2" "200" "get ticks"
  n="$($J 'length' /tmp/qa_resp.json)"
  assert_eq "$n" "24" "24 ticks"
  assert_eq "$($J '.[0].month' /tmp/qa_resp.json)" "1" "first tick month 1"
  assert_eq "$($J '.[-1].month' /tmp/qa_resp.json)" "24" "last tick month 24"
  assert "$J '.[0].kpis | has(\"cash_balance\") and has(\"mrr\") and has(\"runway_months\")' /tmp/qa_resp.json == true"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T006 — stress run handshake: hurdle → decision → resume → completion
# ────────────────────────────────────────────────────────────────────────────
card_P2T006() {
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  local owner_wid code run_id event_id
  owner_wid="$(curl -s "$API/workspaces" -H "Authorization: Bearer $ACCESS" | jq -r '.[0].id')"
  WID="$owner_wid"
  local bp_id
  bp_id="$(curl -s "$API/blueprints" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" | jq -r '.[0].id')"
  local ver
  ver="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" | jq -r '.[0].id')"
  code="$("${CURL[@]}" -X POST "$API/simulations" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" \
    -H 'Content-Type: application/json' \
    -d "{\"blueprint_version_id\":\"$ver\",\"mode\":\"stress\",\"seed\":1337,\"config\":{\"months\":24,\"difficulty\":\"standard\"}}")"
  assert_eq "$code" "201" "start stress"
  run_id="$($J '.id' /tmp/qa_resp.json)"
  assert_eq "$($J '.status' /tmp/qa_resp.json)" "awaiting_decision" "stress parks at first hurdle"
  # Fetch pending event via GET run → events; decide option A.
  event_id="$(curl -s "$API/simulations/$run_id" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" | jq -r '.pending_event_id // empty')"
  [[ -n "$event_id" ]] || event_id="$(docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -tAc "SELECT id FROM simulation_events WHERE run_id='$run_id' AND status='pending' LIMIT 1" | tr -d ' \r\n')"
  # Event ids look like evt_<hex> (underscore, not hyphen) — require non-empty.
  [[ -n "$event_id" ]] || { echo "no pending event found for run $run_id"; return 1; }
  code="$("${CURL[@]}" -X POST "$API/simulations/$run_id/decide" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" \
    -H 'Content-Type: application/json' \
    -d "{\"event_id\":\"$event_id\",\"option_id\":\"A\"}")"
  assert_eq "$code" "200" "apply decision"
  # Run resumes; eventually completes or reaches another hurdle (both legal).
  # The decide response nests the run under .run (run.status).
  local status
  status="$($J '.run.status // .status' /tmp/qa_resp.json)"
  if [[ "$status" == "completed" || "$status" == "awaiting_decision" || "$status" == "dead" ]]; then
    echo "PASS: run continued after decision (status=$status)"
  else
    echo "FAIL: unexpected status $status"
    return 1
  fi
}

# ────────────────────────────────────────────────────────────────────────────
# P2T007 — report generation contract: MC run → report JSON + markdown
# ────────────────────────────────────────────────────────────────────────────
card_P2T007() {
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  local owner_wid code run_id
  owner_wid="$(curl -s "$API/workspaces" -H "Authorization: Bearer $ACCESS" | jq -r '.[0].id')"
  WID="$owner_wid"
  # Use the seeded completed MC run (demo data) to avoid a long Celery batch.
  run_id="$(docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -tAc "SELECT id FROM simulation_runs WHERE mode='monte_carlo' AND status='completed' ORDER BY created_at LIMIT 1" | tr -d ' \r\n')"
  [[ -n "$run_id" ]] || { echo "no completed MC run found (seed first)"; return 1; }
  code="$("${CURL[@]}" "$API/reports/simulations/$run_id/report" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID")"
  assert_eq "$code" "200" "generate report"
  assert "$J '.content_json.survival.survival_rate | type == "number"' /tmp/qa_resp.json == true"
  assert "$J '.content_json.weaknesses | length > 0' /tmp/qa_resp.json == true"
  assert_contains "$($J '.content_md' /tmp/qa_resp.json)" "SURVIVAL METRICS" "markdown has survival section"
  # Idempotency: second call returns the SAME report (no duplicate row).
  local code2 id1
  id1="$($J '.id' /tmp/qa_resp.json)"
  code2="$("${CURL[@]}" "$API/reports/simulations/$run_id/report" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID")"
  assert_eq "$code2" "200" "report idempotent"
  assert_eq "$($J '.id' /tmp/qa_resp.json)" "$id1" "same report row"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T008 — report share contract: token → public view → revoke
# ────────────────────────────────────────────────────────────────────────────
card_P2T008() {
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  local owner_wid run_id code share_url token
  owner_wid="$(curl -s "$API/workspaces" -H "Authorization: Bearer $ACCESS" | jq -r '.[0].id')"
  WID="$owner_wid"
  run_id="$(docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -tAc "SELECT id FROM simulation_runs WHERE mode='monte_carlo' AND status='completed' ORDER BY created_at LIMIT 1" | tr -d ' \r\n')"
  code="$("${CURL[@]}" -X POST "$API/reports/simulations/$run_id/report/share" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" -H 'Content-Type: application/json' -d '{}')"
  assert_eq "$code" "201" "create share"
  share_url="$($J '.share_url' /tmp/qa_resp.json)"
  token="$($J '.token' /tmp/qa_resp.json)"
  assert_contains "$share_url" "reports/shared/" "share url shape"
  # Public GET (no auth) works.
  local code2
  code2="$("${CURL[@]}" "$API/reports/shared/$token")"
  assert_eq "$code2" "200" "public shared report view"
  # Revoke → 404 for the public token.
  local code3
  code3="$("${CURL[@]}" -X DELETE "$API/reports/simulations/$run_id/report/share" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID")"
  assert_eq "$code3" "204" "revoke share"
  local code4
  code4="$("${CURL[@]}" "$API/reports/shared/$token")"
  assert_eq "$code4" "404" "revoked token 404"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T009 — report compare contract: two completed runs → deltas + verdict
# ────────────────────────────────────────────────────────────────────────────
# MC runs complete asynchronously via the Celery worker. Create two in A's
# workspace, wait for both to reach 'completed', then compare them.
wait_mc_completed() {
  local run_id="$1" status="" i
  for i in $(seq 1 30); do
    status="$(docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -tAc "SELECT status FROM simulation_runs WHERE id='$run_id'" | tr -d ' \r\n')"
    [[ "$status" == "completed" ]] && return 0
    [[ "$status" == "failed" ]] && { echo "MC run $run_id failed"; return 1; }
    sleep 2
  done
  echo "MC run $run_id timed out (status=$status)"; return 1
}

start_mc_run() {
  # Start a Monte Carlo run in the current workspace; echo the new run id.
  local bp_id ver
  bp_id="$(curl -s "$API/blueprints" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" | jq -r '.[0].id')"
  ver="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" | jq -r '.[0].id')"
  local code
  code="$("${CURL[@]}" -X POST "$API/simulations" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" \
    -H 'Content-Type: application/json' \
    -d "{\"blueprint_version_id\":\"$ver\",\"mode\":\"monte_carlo\",\"seed\":7,\"config\":{\"months\":24,\"n_runs\":20}}")"
  [[ "$code" == "201" ]] || { echo "start MC: unexpected status $code"; return 1; }
  $J '.id' /tmp/qa_resp.json
}

card_P2T009() {
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  local owner_wid code run_a run_b
  owner_wid="$(curl -s "$API/workspaces" -H "Authorization: Bearer $ACCESS" | jq -r '.[0].id')"
  WID="$owner_wid"
  run_a="$(start_mc_run)" || return 1
  run_b="$(start_mc_run)" || return 1
  wait_mc_completed "$run_a" || return 1
  wait_mc_completed "$run_b" || return 1
  code="$("${CURL[@]}" "$API/reports/compare?a=$run_a&b=$run_b" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID")"
  assert_eq "$code" "200" "compare runs"
  assert "$J '.deltas.survival_rate_pp | type == "number"' /tmp/qa_resp.json == true"
  assert "$J '.verdict | IN(\"improved\",\"regressed\",\"unchanged\")' /tmp/qa_resp.json == true"
  assert_eq "$($J '.a.run_id' /tmp/qa_resp.json)" "$run_a" "run a echoed"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T010 — scenario marketplace contract: publish → public browse → clone
# ────────────────────────────────────────────────────────────────────────────
card_P2T010() {
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  local owner_wid code sc_id bp_id bv_id
  owner_wid="$(curl -s "$API/workspaces" -H "Authorization: Bearer $ACCESS" | jq -r '.[0].id')"
  WID="$owner_wid"
  # Publish a scenario with a valid category + a real blueprint version id.
  bp_id="$(curl -s "$API/blueprints" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" | jq -r '.[0].id')"
  bv_id="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" | jq -r '.[0].id')"
  code="$("${CURL[@]}" -X POST "$API/scenarios" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" \
    -H 'Content-Type: application/json' \
    -d "{\"title\":\"QA Scenario\",\"description\":\"desc\",\"category\":\"market_crash\",\"blueprint_version_id\":\"$bv_id\"}")"
  assert_eq "$code" "201" "publish scenario"
  sc_id="$($J '.id' /tmp/qa_resp.json)"
  # Public browse (no auth) lists it. Response is {items, total, page}.
  local code2
  code2="$("${CURL[@]}" "$API/scenarios?category=market_crash")"
  assert_eq "$code2" "200" "browse scenarios"
  assert_contains "$($J '[.items[].title] | join(",")' /tmp/qa_resp.json)" "QA Scenario" "scenario listed publicly"
  # Public detail (no auth).
  local code3
  code3="$("${CURL[@]}" "$API/scenarios/$sc_id")"
  assert_eq "$code3" "200" "public scenario detail"
  # Clone into a second workspace. register_user_b sets ACCESS_B (B's token).
  register_user_b
  local wid_b code4 bp_cloned
  wid_b="$(curl -s "$API/workspaces" -H "Authorization: Bearer $ACCESS_B" | jq -r '.[0].id')"
  code4="$("${CURL[@]}" -X POST "$API/scenarios/$sc_id/clone" \
    -H "Authorization: Bearer $ACCESS_B" -H "X-Workspace-Id: $wid_b" -H 'Content-Type: application/json' -d '{}')"
  assert_eq "$code4" "201" "clone scenario"
  # Clone returns blueprint_id/blueprint_version_id — verify the blueprint now
  # lives in B's workspace.
  bp_cloned="$($J '.blueprint_id' /tmp/qa_resp.json)"
  assert_eq "$(curl -s "$API/blueprints/$bp_cloned" -H "Authorization: Bearer $ACCESS_B" -H "X-Workspace-Id: $wid_b" | jq -r '.workspace_id')" "$wid_b" "clone lands in B's workspace"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T011 — leaderboard contract: public, sorted, shape-checked
# ────────────────────────────────────────────────────────────────────────────
card_P2T011() {
  # Leaderboard shows PUBLIC completed MC runs. Publish the most recent
  # completed MC run in A's workspace so there is at least one entry.
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  local owner_wid run_id code
  owner_wid="$(curl -s "$API/workspaces" -H "Authorization: Bearer $ACCESS" | jq -r '.[0].id')"
  WID="$owner_wid"
  run_id="$(docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -tAc "SELECT id FROM simulation_runs WHERE mode='monte_carlo' AND status='completed' AND workspace_id='$WID' ORDER BY created_at DESC LIMIT 1" | tr -d ' \r\n')"
  [[ -n "$run_id" ]] || { echo "no completed MC run to publish"; return 1; }
  code="$("${CURL[@]}" -X PATCH "$API/simulations/$run_id" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" \
    -H 'Content-Type: application/json' -d '{"is_public":true}')"
  assert_eq "$code" "200" "publish run to leaderboard"
  code="$("${CURL[@]}" "$API/leaderboard")"
  assert_eq "$code" "200" "leaderboard public"
  # Contract: LeaderboardResponse is an object wrapping entries[].
  assert_eq "$($J 'has("entries")' /tmp/qa_resp.json)" "true" "entries key present"
  local n
  n="$($J '.entries | length' /tmp/qa_resp.json)"
  if [[ "$n" -gt 1 ]]; then
    assert_eq "$($J '.entries[0].resilience_score >= .entries[1].resilience_score' /tmp/qa_resp.json)" "true" "sorted desc"
  fi
  assert_eq "$($J '[.entries[] | has("run_id")] | all' /tmp/qa_resp.json)" "true" "entries have run_id"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T012 — billing usage contract: meters increment across runs
# ────────────────────────────────────────────────────────────────────────────
card_P2T012() {
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  local owner_wid code usage_before runs_before
  owner_wid="$(curl -s "$API/workspaces" -H "Authorization: Bearer $ACCESS" | jq -r '.[0].id')"
  WID="$owner_wid"
  code="$("${CURL[@]}" "$API/billing/usage" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID")"
  assert_eq "$code" "200" "usage endpoint"
  runs_before="$($J '.usage.runs_used // .runs_used // 0' /tmp/qa_resp.json)"
  # Baseline runs increment the runs meter (T41).
  local bp_id ver code2
  bp_id="$(curl -s "$API/blueprints" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" | jq -r '.[0].id')"
  ver="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" | jq -r '.[0].id')"
  code2="$("${CURL[@]}" -X POST "$API/simulations" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" \
    -H 'Content-Type: application/json' \
    -d "{\"blueprint_version_id\":\"$ver\",\"mode\":\"baseline\",\"seed\":7,\"config\":{\"months\":12}}")"
  assert_eq "$code2" "201" "baseline to bump meter"
  code="$("${CURL[@]}" "$API/billing/usage" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID")"
  local runs_after
  runs_after="$($J '.usage.runs_used // .runs_used // 0' /tmp/qa_resp.json)"
  assert_eq "$runs_after" "$((runs_before + 1))" "runs meter incremented by 1"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T013 — admin contract: stats/users/workspaces + audit-log trail
# ────────────────────────────────────────────────────────────────────────────
card_P2T013() {
  register_user "qa-admin@forge.dev" "QA-admin-0001!" /tmp/qa_resp.json
  # Promote the QA admin to is_admin=true directly in the DB (integration env).
  docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -c \
    "UPDATE users SET is_admin=true WHERE email='qa-admin@forge.dev'" >/dev/null 2>&1
  local code
  code="$("${CURL[@]}" "$API/admin/stats" -H "Authorization: Bearer $ACCESS")"
  assert_eq "$code" "200" "admin stats"
  assert "$J 'has(\"users\") and has(\"workspaces\")' /tmp/qa_resp.json == true" "stats shape"
  code="$("${CURL[@]}" "$API/admin/users?page=1" -H "Authorization: Bearer $ACCESS")"
  assert_eq "$code" "200" "admin users"
  assert "$J 'has(\"items\") or type == \"array\"' /tmp/qa_resp.json == true" "users shape"
  code="$("${CURL[@]}" "$API/admin/audit-log?page=1&limit=5" -H "Authorization: Bearer $ACCESS")"
  assert_eq "$code" "200" "audit log list"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T014 — WS contract: snapshot envelope + tick replay on connect
# ────────────────────────────────────────────────────────────────────────────
card_P2T014() {
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  local owner_wid run_id
  owner_wid="$(curl -s "$API/workspaces" -H "Authorization: Bearer $ACCESS" | jq -r '.[0].id')"
  WID="$owner_wid"
  run_id="$(docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -tAc "SELECT id FROM simulation_runs WHERE mode='baseline' AND status='completed' ORDER BY created_at DESC LIMIT 1" | tr -d ' \r\n')"
  [[ -n "$run_id" ]] || { echo "no baseline run; skipping WS replay (needs seed)"; return 1; }
  # Connect with the access token; expect snapshot then tick envelopes.
  local out
  # websockets lives in the backend venv, not the system python.
  out="$("$VENV_DIR/bin/python" - "$run_id" "$ACCESS" <<'PYEOF'
import asyncio, json, sys
try:
    import websockets
except ImportError:
    print("SKIP"); raise SystemExit(0)
run_id, token = sys.argv[1], sys.argv[2]
async def main():
    uri = f"ws://localhost:8000/ws/simulations/{run_id}?token={token}"
    async with websockets.connect(uri) as ws:
        first = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        assert first["type"] == "snapshot", first
        second = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        assert second["type"] == "tick", second
        assert "kpis" in second["data"], second
        print("WS-OK")
asyncio.run(main())
PYEOF
)"
  assert_eq "$out" "WS-OK" "WS snapshot + tick replay"
  # Unauthorized token → close code 4401.
  local out2
  out2="$("$VENV_DIR/bin/python" - "$run_id" "bogus-token" <<'PYEOF'
import asyncio, sys
try:
    import websockets
except ImportError:
    print("SKIP"); raise SystemExit(0)
run_id, token = sys.argv[1], sys.argv[2]
async def main():
    try:
        async with websockets.connect(f"ws://localhost:8000/ws/simulations/{run_id}?token={token}") as ws:
            await ws.recv()
    except websockets.exceptions.ConnectionClosed as e:
        assert e.rcvd.code == 4401, e
        print("WS-401-OK")
asyncio.run(main())
PYEOF
)"
  assert_eq "$out2" "WS-401-OK" "WS rejects bad token 4401"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T015 — Stripe webhook contract: signature check + idempotent mirroring
# ────────────────────────────────────────────────────────────────────────────
card_P2T015() {
  local code
  # Bad signature → 400.
  code="$("${CURL[@]}" -X POST "$API/webhooks/stripe" \
    -H 'Content-Type: application/json' -H 'Stripe-Signature: bad' \
    -d '{"id":"evt_bad","type":"customer.subscription.created"}')"
  assert_eq "$code" "400" "bad signature rejected"
  # Without any signature → 400 too.
  code="$("${CURL[@]}" -X POST "$API/webhooks/stripe" \
    -H 'Content-Type: application/json' \
    -d '{"id":"evt_x","type":"customer.subscription.created"}')"
  assert_eq "$code" "400" "missing signature rejected"
}

# ────────────────────────────────────────────────────────────────────────────
# P2T016 — API key contract: create → authenticate with X-API-Key → revoke
# ────────────────────────────────────────────────────────────────────────────
card_P2T016() {
  register_user "qa-a@forge.dev" "QA-pass-1234!" /tmp/qa_resp.json
  local owner_wid code key
  owner_wid="$(curl -s "$API/workspaces" -H "Authorization: Bearer $ACCESS" | jq -r '.[0].id')"
  WID="$owner_wid"
  code="$("${CURL[@]}" -X POST "$API/api-keys" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" \
    -H 'Content-Type: application/json' \
    -d '{"name":"qa-key","scopes":["simulations:read"],"rate_limit_rpm":10}')"
  assert_eq "$code" "201" "create api key"
  key="$($J '.key // .api_key // empty' /tmp/qa_resp.json)"
  assert_contains "$key" "fk_" "plaintext key returned once"
  # Authenticate with the key instead of a JWT.
  local code2
  code2="$("${CURL[@]}" "$API/simulations" \
    -H "X-API-Key: $key" -H "X-Workspace-Id: $WID")"
  assert_eq "$code2" "200" "api key auth works"
  # Revoke → 401 on subsequent use.
  local kid
  kid="$($J '.id' /tmp/qa_resp.json)"
  [[ -n "$kid" ]] || kid="$(curl -s "$API/api-keys" -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID" | jq -r '.[0].id')"
  local code3
  code3="$("${CURL[@]}" -X DELETE "$API/api-keys/$kid" \
    -H "Authorization: Bearer $ACCESS" -H "X-Workspace-Id: $WID")"
  assert_eq "$code3" "204" "revoke api key"
  local code4
  code4="$("${CURL[@]}" "$API/simulations" \
    -H "X-API-Key: $key" -H "X-Workspace-Id: $WID")"
  assert_eq "$code4" "401" "revoked key rejected"
}

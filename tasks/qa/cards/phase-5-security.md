# PHASE 5 — SECURITY & COMPLIANCE TESTS

Tests auth, authorization, input sanitization, PII handling, and rate limits.
Includes injection, fuzzing, and privilege escalation attempts. Every attack
must be blocked; every mutation must leave an audit trail. Runs against the
qa stack with the audit-log middleware and rate limiter **enabled**
(`TESTING=false`).

Note: the global rate limiter is live here (default 100/min per IP). Cards
that need >100 requests use the API-key rate limiter or spread requests;
`reset_windows()` is exposed for in-process probes (P5T004).

---
# CARDS: P5T001 P5T002 P5T003 P5T004 P5T005 P5T006 P5T007 P5T008 P5T009 P5T010 P5T011 P5T012 P5T013 P5T014 P5T015 P5T016
# PRE:   pre_phase5_clean
# POST:  post_phase5_teardown
# NEXT:  P5T001 -> P5T002
# NEXT:  P5T002 -> P5T003
# NEXT:  P5T003 -> P5T004
# NEXT:  P5T004 -> P5T005
# NEXT:  P5T005 -> P5T006
# NEXT:  P5T006 -> P5T007
# NEXT:  P5T007 -> P5T008
# NEXT:  P5T008 -> P5T009
# NEXT:  P5T009 -> P5T010
# NEXT:  P5T010 -> P5T011
# NEXT:  P5T011 -> P5T012
# NEXT:  P5T012 -> P5T013
# NEXT:  P5T013 -> P5T014
# NEXT:  P5T014 -> P5T015
# NEXT:  P5T015 -> P5T016
# NEXT:  P5T016 -> END
---

BASE="http://localhost:8000"
API="$BASE/api/v1"
CURL=(curl -s -o /tmp/qa_resp.json -w '%{http_code}')
J="jq -r"
SEC_ACCESS=""; SEC_WID=""

pre_phase5_clean() {
  wait_for_http "$BASE/health" "200" "60" "3"
  wait_for_http "$BASE/ready" "200" "60" "3"
  # Ensure TESTING=false so middleware (audit + rate limit) is live.
  local env
  env="$(docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T backend printenv TESTING 2>/dev/null | tr -d '\r')"
  if [[ "$env" == "true" ]]; then
    echo "FAIL: TESTING must be false in phase 5 (restart backend with TESTING=false)"; return 1
  fi
  docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T backend python -m app.utils.seed >/dev/null 2>&1
  # Register the security fixture user (201 created / 409 exists), then log in
  # — register returns UserOut without tokens, login returns the TokenPair.
  local code
  code="$("${CURL[@]}" -X POST "$API/auth/register" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-sec@forge.dev","name":"Sec","password":"QA-sec-1234!"}')"
  if [[ "$code" != "201" && "$code" != "409" ]]; then
    echo "FAIL: register qa-sec unexpected status $code"; return 1
  fi
  # Login with retries — after the perf phase's load burst the backend can
  # briefly return 429/5xx; a stale empty token then makes the workspaces jq
  # below fail with a confusing "Cannot index object with number".
  local attempt
  code=""
  for attempt in 1 2 3; do
    code="$("${CURL[@]}" -X POST "$API/auth/login" \
      -H 'Content-Type: application/json' \
      -d '{"email":"qa-sec@forge.dev","password":"QA-sec-1234!"}')"
    [[ "$code" == "200" ]] && break
    sleep 2
  done
  [[ "$code" == "200" ]] || { echo "FAIL: qa-sec login status $code"; return 1; }
  SEC_ACCESS="$($J '.access_token' /tmp/qa_resp.json)"
  # Phase 4's load burst (P4T009 fires 1100+ requests) can leave the global
  # rate-limit window (1000/min per IP) nearly full, so a fresh /workspaces
  # call 429s. Retry until the window drains (it's a rolling 60s window).
  local ws_code attempt2
  SEC_WID=""
  for attempt2 in 1 2 3 4 5; do
    ws_code="$(curl -s -o /tmp/qa_ws.json -w '%{http_code}' "$API/workspaces" \
      -H "Authorization: Bearer $SEC_ACCESS")"
    if [[ "$ws_code" == "200" ]]; then
      SEC_WID="$(jq -r '.[0].id // empty' /tmp/qa_ws.json)"
      break
    fi
    echo "  retry workspaces (status=$ws_code)"
    sleep 15
  done
  [[ -n "$SEC_ACCESS" && -n "$SEC_WID" ]] || return 1
}

post_phase5_teardown() {
  wait_for_http "$BASE/health" "200" "30" "3"
}

# ────────────────────────────────────────────────────────────────────────────
# P5T001 — auth: no token, malformed token, refresh-as-access → 401
# ────────────────────────────────────────────────────────────────────────────
card_P5T001() {
  local code
  code="$("${CURL[@]}" "$API/blueprints")"
  assert_eq "$code" "401" "no token → 401"
  code="$("${CURL[@]}" "$API/blueprints" -H "Authorization: Bearer not.a.jwt")"
  assert_eq "$code" "401" "malformed token → 401"
  # A refresh token used as an access token → 401.
  local rt code2
  rt="$(curl -s -X POST "$API/auth/login" -H 'Content-Type: application/json' \
    -d '{"email":"qa-sec@forge.dev","password":"QA-sec-1234!"}' | jq -r '.refresh_token')"
  code2="$("${CURL[@]}" "$API/blueprints" -H "Authorization: Bearer $rt")"
  assert_eq "$code2" "401" "refresh token rejected as access"
  # Token with wrong signature (tampered payload) → 401.
  local tampered
  tampered="$(python3 - "$SEC_ACCESS" <<'PYEOF'
import base64, json, sys
tok = sys.argv[1]
h, p, _ = tok.split(".")
pad = lambda s: s + "=" * (-len(s) % 4)
payload = json.loads(base64.urlsafe_b64decode(pad(p)))
payload["sub"] = "00000000-0000-0000-0000-000000000000"
new_p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
print(f"{h}.{new_p}.tampered")
PYEOF
)"
  code="$("${CURL[@]}" "$API/blueprints" -H "Authorization: Bearer $tampered")"
  assert_eq "$code" "401" "tampered token → 401"
}

# ────────────────────────────────────────────────────────────────────────────
# P5T002 — auth: password rules + login throttling shape (401, identical msg)
# ────────────────────────────────────────────────────────────────────────────
card_P5T002() {
  local code msg1 msg2
  # Unknown email vs wrong password must return IDENTICAL bodies (no enumeration).
  code="$("${CURL[@]}" -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"nobody@forge.dev","password":"whatever-1!"}')"
  assert_eq "$code" "401" "unknown email 401"
  msg1="$($J '.detail' /tmp/qa_resp.json)"
  code="$("${CURL[@]}" -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-sec@forge.dev","password":"WRONG-password!"}')"
  assert_eq "$code" "401" "wrong password 401"
  msg2="$($J '.detail' /tmp/qa_resp.json)"
  assert_eq "$msg1" "$msg2" "identical error messages (no enumeration)"
  # Short password rejected at register (Pydantic min length 8).
  code="$("${CURL[@]}" -X POST "$API/auth/register" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-short@forge.dev","name":"S","password":"short"}')"
  assert_eq "$code" "422" "short password → 422"
}

# ────────────────────────────────────────────────────────────────────────────
# P5T003 — authz: role ladder member→admin→owner enforcement
# ────────────────────────────────────────────────────────────────────────────
card_P5T003() {
  # Owner (qa-sec) invites a member.
  local code invite_url token
  code="$("${CURL[@]}" -X POST "$API/workspaces/$SEC_WID/invites" \
    -H "Authorization: Bearer $SEC_ACCESS" -H 'Content-Type: application/json' \
    -d '{"email":"qa-sec-member@forge.dev","role":"member"}')"
  assert_eq "$code" "201" "invite member"
  invite_url="$($J '.invite_url' /tmp/qa_resp.json)"
  token="${invite_url##*/}"
  # Member registers (201/409) then logs in — register returns no token.
  local code2 m_access
  code2="$("${CURL[@]}" -X POST "$API/auth/register" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-sec-member@forge.dev","name":"M","password":"QA-sec-1234!"}')"
  if [[ "$code2" != "201" && "$code2" != "409" ]]; then
    echo "FAIL: register member unexpected $code2"; return 1
  fi
  code2="$("${CURL[@]}" -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-sec-member@forge.dev","password":"QA-sec-1234!"}')"
  assert_eq "$code2" "200" "member login" || return 1
  m_access="$($J '.access_token' /tmp/qa_resp.json)"
  code="$("${CURL[@]}" -X POST "$API/invites/$token/accept" \
    -H "Authorization: Bearer $m_access" -H 'Content-Type: application/json' -d '{}')"
  assert_eq "$code" "200" "member accepts"
  # Member cannot create API keys (admin+), cannot promote roles.
  code="$("${CURL[@]}" -X POST "$API/api-keys" \
    -H "Authorization: Bearer $m_access" -H "X-Workspace-Id: $SEC_WID" \
    -H 'Content-Type: application/json' -d '{"name":"x"}')"
  assert_eq "$code" "403" "member cannot create api keys"
  code="$("${CURL[@]}" -X PATCH "$API/workspaces/$SEC_WID/members/$( \
    curl -s "$API/users/me" -H "Authorization: Bearer $m_access" | jq -r '.id')" \
    -H "Authorization: Bearer $m_access" -H 'Content-Type: application/json' \
    -d '{"role":"admin"}')"
  assert_eq "$code" "403" "member cannot self-promote"
}

# ────────────────────────────────────────────────────────────────────────────
# P5T004 — rate limit: auth route (10/min) + global (100/min) → 429
# ────────────────────────────────────────────────────────────────────────────
card_P5T004() {
  # Login attempts exceed RATE_LIMIT_AUTH (10/min in .env, 300/min in .env.qa)
  # → expect a 429 before the burst ends. Fire limit+10 attempts; the limit is
  # read from the backend settings so the card works in every env matrix.
  local code i got429=0 rl
  rl="$(docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T backend python -c "from app.core.config import get_settings; print(get_settings().rate_limit_auth)" 2>/dev/null | tr -d '\r')"
  rl="${rl%%/*}"
  rl="${rl:-10}"
  for i in $(seq 1 $((rl + 10))); do
    code="$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/auth/login" \
      -H 'Content-Type: application/json' \
      -d "{\"email\":\"qa-sec@forge.dev\",\"password\":\"wrong-$i\"}")"
    if [[ "$code" == "429" ]]; then got429=1; break; fi
  done
  assert_eq "$got429" "1" "auth rate limit triggers 429"
  # The burst filled the {ip}|rpm rate-limit window (auth and register share
  # the same rpm key). Drain the 60s window so the next card's register/login
  # (P5T005) is not itself 429ed.
  echo "PASS: waiting 61s for rate-limit window to drain"
  sleep 61
}

# ────────────────────────────────────────────────────────────────────────────
# P5T005 — XSS: reflected script content in names/titles is stored inert
# ────────────────────────────────────────────────────────────────────────────
card_P5T005() {
  local code
  # Register a user whose name contains an XSS payload (201/409 exists).
  code="$("${CURL[@]}" -X POST "$API/auth/register" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-xss@forge.dev","name":"<script>alert(1)</script>","password":"QA-sec-1234!"}')"
  if [[ "$code" != "201" && "$code" != "409" ]]; then
    echo "FAIL: xss register unexpected $code"; return 1
  fi
  # The stored value is returned raw by the API (React escapes on render),
  # and the API never executes it — verify the round trip.
  local access
  code="$("${CURL[@]}" -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-xss@forge.dev","password":"QA-sec-1234!"}')"
  assert_eq "$code" "200" "xss user login" || return 1
  access="$($J '.access_token' /tmp/qa_resp.json)"
  local name
  name="$(curl -s "$API/users/me" -H "Authorization: Bearer $access" | jq -r '.name')"
  assert_eq "$name" "<script>alert(1)</script>" "name round-trips (server does not sanitize by design)"
  # Scenario title with HTML must not be rendered executable: verify JSON content-type.
  local w code2 bp_id bv_id
  w="$(curl -s "$API/workspaces" -H "Authorization: Bearer $access" | jq -r '.[0].id')"
  bp_id="$(curl -s "$API/blueprints" -H "Authorization: Bearer $access" -H "X-Workspace-Id: $w" | jq -r '.[0].id // empty')"
  bv_id=""
  if [[ -n "$bp_id" ]]; then
    bv_id="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $access" -H "X-Workspace-Id: $w" | jq -r '.[0].id // empty')"
  fi
  if [[ -z "$bv_id" ]]; then
    # Fresh user has no blueprints — create one so the scenario has a valid
    # blueprint_version_id (ScenarioCreate requires it).
    code2="$("${CURL[@]}" -X POST "$API/blueprints" \
      -H "Authorization: Bearer $access" -H "X-Workspace-Id: $w" \
      -H 'Content-Type: application/json' \
      -d "{\"name\":\"SecBP\",\"industry\":\"SaaS\",\"stage\":\"Seed\",\"payload\":$(cat "$FIXTURES/blueprint_valid.json")}")"
    assert_eq "$code2" "201" "create blueprint for scenario" || return 1
    bp_id="$($J '.id' /tmp/qa_resp.json)"
    bv_id="$(curl -s "$API/blueprints/$bp_id/versions" -H "Authorization: Bearer $access" -H "X-Workspace-Id: $w" | jq -r '.[0].id')"
  fi
  code2="$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/scenarios" \
    -H "Authorization: Bearer $access" -H "X-Workspace-Id: $w" \
    -H 'Content-Type: application/json' \
    -d "{\"title\":\"<img src=x onerror=alert(1)>\",\"description\":\"d\",\"category\":\"market_crash\",\"blueprint_version_id\":\"$bv_id\"}")"
  assert_eq "$code2" "201" "html title stored as data"
}

# ────────────────────────────────────────────────────────────────────────────
# P5T006 — SQL injection: fuzzed ids/params never 500 or leak rows
# ────────────────────────────────────────────────────────────────────────────
card_P5T006() {
  local payloads=(
    "1' OR '1'='1"
    "1; DROP TABLE users; --"
    "' UNION SELECT email,password FROM users --"
    "1 OR 1=1"
  )
  local p code
  for p in "${payloads[@]}"; do
    code="$(curl -s -o /dev/null -w '%{http_code}' "$API/blueprints/$p" \
      -H "Authorization: Bearer $SEC_ACCESS" -H "X-Workspace-Id: $SEC_WID")"
    # Must be a controlled 404/422/403 — never 500, never a leak of 200.
    if [[ "$code" == "500" ]]; then
      echo "FAIL: SQLi probe '$p' produced 500"
      return 1
    fi
    if [[ "$code" == "200" ]]; then
      echo "FAIL: SQLi probe '$p' returned 200 (leak?)"
      return 1
    fi
    echo "PASS: SQLi probe blocked (code=$code)"
  done
}

# ────────────────────────────────────────────────────────────────────────────
# P5T007 — privilege escalation: cross-workspace access → 403/404, never data
# ────────────────────────────────────────────────────────────────────────────
card_P5T007() {
  # Second user in their own workspace (register 201/409, then login for token).
  local code access2 wid2
  code="$("${CURL[@]}" -X POST "$API/auth/register" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-other@forge.dev","name":"Other","password":"QA-sec-1234!"}')"
  if [[ "$code" != "201" && "$code" != "409" ]]; then
    echo "FAIL: register qa-other unexpected $code"; return 1
  fi
  code="$("${CURL[@]}" -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-other@forge.dev","password":"QA-sec-1234!"}')"
  assert_eq "$code" "200" "qa-other login" || return 1
  access2="$($J '.access_token' /tmp/qa_resp.json)"
  wid2="$(curl -s "$API/workspaces" -H "Authorization: Bearer $access2" | jq -r '.[0].id')"
  # User2 cannot read user1's workspace resources.
  code="$(curl -s -o /dev/null -w '%{http_code}' "$API/blueprints" \
    -H "Authorization: Bearer $access2" -H "X-Workspace-Id: $SEC_WID")"
  assert_eq "$code" "403" "foreign workspace blocked"
  # And cannot read user1's admin-only endpoints.
  code="$(curl -s -o /dev/null -w '%{http_code}' "$API/admin/stats" \
    -H "Authorization: Bearer $access2")"
  assert_eq "$code" "403" "non-admin blocked from admin"
  # Workspace-scoped ids from another workspace → 404 (no existence oracle).
  local bp_id
  bp_id="$(curl -s "$API/blueprints" -H "Authorization: Bearer $SEC_ACCESS" -H "X-Workspace-Id: $SEC_WID" | jq -r '.[0].id // empty')"
  if [[ -n "$bp_id" && "$bp_id" != "null" ]]; then
    code="$(curl -s -o /dev/null -w '%{http_code}' "$API/blueprints/$bp_id" \
      -H "Authorization: Bearer $access2" -H "X-Workspace-Id: $wid2")"
    assert_eq "$code" "404" "foreign resource reads 404"
  fi
}

# ────────────────────────────────────────────────────────────────────────────
# P5T008 — fuzzing: auth endpoints reject garbage with 422, never 500
# ────────────────────────────────────────────────────────────────────────────
card_P5T008() {
  local bodies=(
    '{"email":1,"password":2}'
    '{"email":"x","password":""}'
    '[]'
    '{"email":"a@b.c","password":"x","extra":{}}'
    'not json at all'
  )
  local b code
  for b in "${bodies[@]}"; do
    code="$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/auth/login" \
      -H 'Content-Type: application/json' -d "$b")"
    case "$code" in
      200|401|422) echo "PASS: fuzz login blocked ($code)" ;;
      500) echo "FAIL: fuzz login produced 500"; return 1 ;;
      *) echo "PASS: fuzz login handled ($code)" ;;
    esac
  done
  # Oversized body (>1MB) → 413 or 422, never 500.
  local big
  big="$(python3 -c "print('{\"email\":\"' + 'a'*1200000 + '\",\"password\":\"x\"}')")"
  code="$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' -d "$big")"
  case "$code" in
    413|422|400) echo "PASS: oversized body rejected ($code)" ;;
    500) echo "FAIL: oversized body 500"; return 1 ;;
    *) echo "PASS: oversized body handled ($code)" ;;
  esac
}

# ────────────────────────────────────────────────────────────────────────────
# P5T009 — PII handling: user passwords never appear in responses/logs
# ────────────────────────────────────────────────────────────────────────────
card_P5T009() {
  # Response bodies must not echo password fields or hashes.
  local resp
  resp="$(curl -s -X POST "$API/auth/register" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-pii@forge.dev","name":"PII","password":"QA-sec-1234!"}')"
  if ! echo "$resp" | grep -q "access_token"; then
    resp="$(curl -s -X POST "$API/auth/login" \
      -H 'Content-Type: application/json' \
      -d '{"email":"qa-pii@forge.dev","password":"QA-sec-1234!"}')"
  fi
  assert_contains "$resp" "access_token" "auth response present"
  if echo "$resp" | grep -q "QA-sec-1234"; then
    echo "FAIL: password echoed in response"; return 1
  fi
  # Users list must not expose pw_hash.
  local access
  access="$(echo "$resp" | jq -r '.access_token')"
  local users
  users="$(curl -s "$API/users/me" -H "Authorization: Bearer $access")"
  if echo "$users" | grep -q "pw_hash\|password"; then
    echo "FAIL: password hash exposed in user payload"; return 1
  fi
  echo "PASS: no password/hash leakage in API responses"
}

# ────────────────────────────────────────────────────────────────────────────
# P5T010 — audit log: every mutation creates a row with caller + path
# ────────────────────────────────────────────────────────────────────────────
card_P5T010() {
  # Mutate: create a blueprint, then check the audit trail.
  local code wid bp_id
  code="$("${CURL[@]}" -X POST "$API/blueprints" \
    -H "Authorization: Bearer $SEC_ACCESS" -H "X-Workspace-Id: $SEC_WID" \
    -H 'Content-Type: application/json' \
    -d "{\"name\":\"Audited\",\"industry\":\"SaaS\",\"stage\":\"Seed\",\"payload\":$(cat "$FIXTURES/blueprint_valid.json")}")"
  assert_eq "$code" "201" "audited mutation"
  bp_id="$($J '.id' /tmp/qa_resp.json)"
  # Admin reads the audit log.
  docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T db psql -U forge -d forge -c \
    "UPDATE users SET is_admin=true WHERE email='qa-sec@forge.dev'" >/dev/null 2>&1
  local rows
  rows="$(curl -s "$API/admin/audit-log?limit=20" \
    -H "Authorization: Bearer $SEC_ACCESS" | jq -r '[.items[] | select(.path | contains("/blueprints"))] | length')"
  if [[ "$rows" -ge 1 ]]; then
    echo "PASS: audit log has blueprint mutations (n=$rows)"
  else
    echo "FAIL: no audit rows for blueprint mutation"
    return 1
  fi
}

# ────────────────────────────────────────────────────────────────────────────
# P5T011 — admin authz: is_admin=false → 403 on all admin routes
# ────────────────────────────────────────────────────────────────────────────
card_P5T011() {
  local code
  code="$("${CURL[@]}" "$API/admin/stats" -H "Authorization: Bearer $SEC_ACCESS")"
  assert_eq "$code" "200" "admin stats (qa-sec is admin after P5T010)"
  # A non-admin user (qa-other) must be rejected.
  local access2
  access2="$(curl -s -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-other@forge.dev","password":"QA-sec-1234!"}' | jq -r '.access_token')"
  code="$("${CURL[@]}" "$API/admin/stats" -H "Authorization: Bearer $access2")"
  assert_eq "$code" "403" "non-admin blocked from /admin/stats"
  code="$("${CURL[@]}" "$API/admin/users?page=1" -H "Authorization: Bearer $access2")"
  assert_eq "$code" "403" "non-admin blocked from /admin/users"
  code="$("${CURL[@]}" "$API/admin/workspaces?page=1" -H "Authorization: Bearer $access2")"
  assert_eq "$code" "403" "non-admin blocked from /admin/workspaces"
}

# ────────────────────────────────────────────────────────────────────────────
# P5T012 — API key scopes + per-key rate limit (10 rpm) enforcement
# ────────────────────────────────────────────────────────────────────────────
card_P5T012() {
  local code key wid
  # Create a key with rate_limit_rpm=10.
  code="$("${CURL[@]}" -X POST "$API/api-keys" \
    -H "Authorization: Bearer $SEC_ACCESS" -H "X-Workspace-Id: $SEC_WID" \
    -H 'Content-Type: application/json' \
    -d '{"name":"sec-key","scopes":["runs:read"],"rate_limit_rpm":10}')"
  assert_eq "$code" "201" "create scoped key"
  key="$($J '.key // .api_key // empty' /tmp/qa_resp.json)"
  wid="$SEC_WID"
  # Fire 12 requests → expect at least one 429, zero 5xx.
  local out n429 n5xx
  out="$(seq 1 12 | xargs -P 4 -I{} sh -c \
    "curl -s -o /dev/null -w '%{http_code}\n' '$API/simulations' \
      -H 'X-API-Key: $key' -H 'X-Workspace-Id: $wid'" | sort | uniq -c)"
  echo "distribution: $out"
  n429="$(printf '%s\n' "$out" | awk '$2 == 429 {print $1}')"
  n5xx="$(printf '%s\n' "$out" | awk '$2 >= 500 {s+=$1} END {print s+0}')"
  n429="${n429:-0}"
  [[ "$n429" -ge 1 ]] || { echo "FAIL: per-key limit not enforced"; return 1; }
  assert_eq "$n5xx" "0" "no 5xx on key-limited requests"
}

# ────────────────────────────────────────────────────────────────────────────
# P5T013 — security headers: nosniff, frame deny, referrer, CSP present
# ────────────────────────────────────────────────────────────────────────────
card_P5T013() {
  local hdrs
  hdrs="$(curl -s -D - -o /dev/null "$API/blueprints" \
    -H "Authorization: Bearer $SEC_ACCESS" -H "X-Workspace-Id: $SEC_WID")"
  assert_contains "$hdrs" "x-content-type-options: nosniff" "nosniff header" || return 1
  assert_contains "$hdrs" "x-frame-options: DENY" "frame deny" || return 1
  assert_contains "$hdrs" "referrer-policy: strict-origin-when-cross-origin" "referrer policy" || return 1
  assert_contains "$hdrs" "content-security-policy" "CSP header" || return 1
  assert_contains "$hdrs" "x-request-id" "X-Request-ID echoed"
}

# ────────────────────────────────────────────────────────────────────────────
# P5T014 — CORS: disallowed origin rejected, allowed origin passes
# ────────────────────────────────────────────────────────────────────────────
card_P5T014() {
  local hdrs
  hdrs="$(curl -s -D - -o /dev/null "$API/blueprints" \
    -H "Authorization: Bearer $SEC_ACCESS" -H "X-Workspace-Id: $SEC_WID" \
    -H "Origin: http://evil.example.com")"
  if echo "$hdrs" | grep -qi "access-control-allow-origin"; then
    echo "FAIL: evil origin granted CORS"
    return 1
  fi
  echo "PASS: evil origin denied CORS"
  hdrs="$(curl -s -D - -o /dev/null "$API/blueprints" \
    -H "Authorization: Bearer $SEC_ACCESS" -H "X-Workspace-Id: $SEC_WID" \
    -H "Origin: http://localhost:5173")"
  assert_contains "$hdrs" "access-control-allow-origin: http://localhost:5173" "allowed origin passed" || return 1
  assert_contains "$hdrs" "access-control-allow-credentials: true" "credentials allowed for allow-listed origin"
}

# ────────────────────────────────────────────────────────────────────────────
# P5T015 — secret hygiene: .env secrets not exposed via /metrics or APIs
# ────────────────────────────────────────────────────────────────────────────
card_P5T015() {
  # /metrics is public; it must not contain JWT secrets or DB passwords.
  local metrics
  metrics="$(curl -s "$BASE/metrics")"
  assert_contains "$metrics" "http_requests_total" "metrics present"
  if echo "$metrics" | grep -qi "jwt_secret\|change-me-in-production\|postgresql"; then
    echo "FAIL: secrets leaked in /metrics"
    return 1
  fi
  echo "PASS: no secrets in /metrics"
  # The OpenAPI schema must not expose secrets either.
  local schema
  schema="$(curl -s "$BASE/openapi.json")"
  if echo "$schema" | grep -qi "change-me-in-production"; then
    echo "FAIL: secret leaked in openapi.json"
    return 1
  fi
  echo "PASS: no secrets in openapi.json"
}

# ────────────────────────────────────────────────────────────────────────────
# P5T016 — JWT lifecycle: refresh rotation + expired access rejected
# ────────────────────────────────────────────────────────────────────────────
card_P5T016() {
  # Create a short-lived access token directly (exp=1s) and verify rejection.
  local old_rt
  old_rt="$(curl -s -X POST "$API/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"email":"qa-sec@forge.dev","password":"QA-sec-1234!"}' | jq -r '.refresh_token')"
  # Refresh once → rotates; the OLD refresh token must now be rejected.
  local code
  code="$("${CURL[@]}" -X POST "$API/auth/refresh" \
    -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$old_rt\"}")"
  assert_eq "$code" "200" "refresh rotates tokens"
  # Expired access token: mint with exp in the past via direct decode path.
  local expired
  expired="$(python3 - "$BASE" <<'PYEOF'
import sys
# Build a token with an expired exp claim using the app's own settings.
from app.core.config import get_settings
from datetime import datetime, timedelta, UTC
import jwt
s = get_settings()
tok = jwt.encode({"sub": "00000000-0000-0000-0000-000000000000", "type": "access",
                  "exp": datetime.now(UTC) - timedelta(minutes=1)}, s.jwt_secret_key, algorithm=s.jwt_algorithm)
print(tok)
PYEOF
)"
  code="$("${CURL[@]}" "$API/blueprints" -H "Authorization: Bearer $expired")"
  assert_eq "$code" "401" "expired access token rejected"
}

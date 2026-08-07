#!/usr/bin/env bash
# ============================================================================
# Assertion + reporting library shared by run_qa.sh and run_phase.sh.
# Every function is a boolean check; non-zero exit = assertion failed.
# ============================================================================
set -u

# assert <description> <command...>  — pass when command exits 0
assert() {
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "PASS: $desc"
    return 0
  fi
  echo "FAIL: $desc"
  return 1
}

# assert_eq <actual> <expected> <description>
assert_eq() {
  local actual="$1" expected="$2" desc="$3"
  if [[ "$actual" == "$expected" ]]; then
    echo "PASS: $desc (actual == expected == '$expected')"
    return 0
  fi
  echo "FAIL: $desc (actual='$actual' expected='$expected')"
  return 1
}

# assert_contains <haystack> <needle> <description>
assert_contains() {
  local haystack="$1" needle="$2" desc="$3"
  if [[ "$haystack" == *"$needle"* ]]; then
    echo "PASS: $desc (found '$needle')"
    return 0
  fi
  echo "FAIL: $desc (missing '$needle')"
  return 1
}

# assert_json_eq <json-file-or-string> <jq-path> <expected> <description>
assert_json_eq() {
  local source="$1" jqpath="$2" expected="$3" desc="$4" actual
  if [[ -f "$source" ]]; then
    actual="$(jq -r "$jqpath" "$source" 2>/dev/null)"
  else
    actual="$(printf '%s' "$source" | jq -r "$jqpath" 2>/dev/null)"
  fi
  assert_eq "$actual" "$expected" "$desc"
}

# assert_http_status <url> <expected-status> [<method>] [<extra-curl-args...>]
assert_http_status() {
  local url="$1" expected="$2" method="${3:-GET}" code
  shift 3 || true
  code="$(curl -s -o /dev/null -w '%{http_code}' -X "$method" "$@" "$url" 2>/dev/null)"
  assert_eq "$code" "$expected" "HTTP $method $url -> $expected"
}

# wait_for_http <url> <expected-status> <timeout-seconds> <interval-seconds>
# Polls until the status matches or the timeout elapses (self-healing wait).
wait_for_http() {
  local url="$1" expected="$2" timeout_s="$3" interval_s="${4:-2}" elapsed=0 code=""
  while [[ "$elapsed" -lt "$timeout_s" ]]; do
    code="$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null)"
    if [[ "$code" == "$expected" ]]; then
      echo "PASS: wait_for_http $url -> $expected (after ${elapsed}s)"
      return 0
    fi
    sleep "$interval_s"
    elapsed=$((elapsed + interval_s))
  done
  echo "FAIL: wait_for_http $url never reached $expected (last=$code after ${elapsed}s)"
  return 1
}

# wait_for_log <log-file> <needle> <timeout-seconds> <interval-seconds>
wait_for_log() {
  local file="$1" needle="$2" timeout_s="$3" interval_s="${4:-2}" elapsed=0
  while [[ "$elapsed" -lt "$timeout_s" ]]; do
    if grep -q "$needle" "$file" 2>/dev/null; then
      echo "PASS: log contains '$needle'"
      return 0
    fi
    sleep "$interval_s"
    elapsed=$((elapsed + interval_s))
  done
  echo "FAIL: log never contained '$needle' after ${elapsed}s"
  return 1
}

# duration_lt <seconds> <description> — must be wrapped: start=$(date +%s%3N) ... 
duration_lt_ms() {
  local start_ms="$1" limit_ms="$2" desc="$3" now
  now="$(date +%s%3N)"
  local elapsed=$((now - start_ms))
  if [[ "$elapsed" -lt "$limit_ms" ]]; then
    echo "PASS: $desc (${elapsed}ms < ${limit_ms}ms)"
    return 0
  fi
  echo "FAIL: $desc (${elapsed}ms >= ${limit_ms}ms)"
  return 1
}

#!/usr/bin/env bash
# ============================================================================
# Phase runner — executes every test card in a phase script deterministically.
#
# A "phase script" is a bash file containing function definitions:
#   card_<ID>() { ... asserts ... }   # one function per test card
# plus a manifest comment header:
#   # CARDS: P1T001 P1T002 ...        # ordered list of card IDs (the chain)
#   # PRE:   <function that verifies clean env>
#   # POST:  <function that tears down>
#
# The runner:
#   1. runs PRE  (aborts the phase on failure)
#   2. runs each card in manifest order, enforcing NEXT TEST ID continuity
#   3. on a card failure: 2 retries with 2s/4s backoff, then marks FAILED or
#      FLAKY per the card's declared determinism (--deterministic per card),
#      running the card's cleanup/rollback
#   4. runs POST (teardown)
#   5. writes one JSON summary line to the shared summary file
#   6. exits 0 when every card passed (GO), else 1 (NO-GO)
# ============================================================================
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/assert_lib.sh"

NAME=""; SCRIPT=""; ENV_NAME=""; BACKEND_DIR=""; FRONTEND_DIR=""; VENV=""; LOG=""; SUMMARY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2 ;;
    --script) SCRIPT="$2"; shift 2 ;;
    --env) ENV_NAME="$2"; shift 2 ;;
    --backend-dir) BACKEND_DIR="$2"; shift 2 ;;
    --frontend-dir) FRONTEND_DIR="$2"; shift 2 ;;
    --venv) VENV="$2"; shift 2 ;;
    --log) LOG="$2"; shift 2 ;;
    --summary) SUMMARY="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -f "$SCRIPT" ]] || { echo "phase script not found: $SCRIPT" >&2; exit 1; }

# Export shared context to card scripts. REPO_ROOT and FIXTURES are derived so
# cards are also runnable standalone via run_phase.sh (not only via run_qa.sh).
# SCRIPT_DIR is .../tasks/qa/orchestrator → repo root is three levels up.
export QA_ENV="$ENV_NAME" BACKEND_DIR FRONTEND_DIR VENV_DIR="$VENV" QA_LOG="$LOG"
export REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
export FIXTURES="${FIXTURES:-$REPO_ROOT/tasks/qa/fixtures}"

# Source only the executable portion of the card file: the markdown prose
# header ends at the first '---' separator, and the bash functions follow.
# This keeps cards human-readable while remaining fully sourceable.
BODY="$(awk '/^---$/{found=1; next} found' "$SCRIPT")"
# shellcheck source=/dev/null
source /dev/stdin <<< "$BODY"

# ---------------------------------------------------------------------------
# Determinism registry: card_<ID>_deterministic() -> "yes"|"no"
# Cards may declare a companion function; default is "yes" (deterministic).
# ---------------------------------------------------------------------------
card_is_deterministic() {
  if declare -F "card_${1}_deterministic" >/dev/null 2>&1; then
    "card_${1}_deterministic"
  else
    echo "yes"
  fi
}

# ---------------------------------------------------------------------------
# Chain verification: manifest order must exactly match the declared NEXT IDs.
# ---------------------------------------------------------------------------
CARDS=( $(sed -n 's/^# CARDS: //p' "$SCRIPT" | head -1) )
PRE_FN="$(sed -n 's/^# PRE:   //p' "$SCRIPT" | head -1)"
POST_FN="$(sed -n 's/^# POST:  //p' "$SCRIPT" | head -1)"

[[ ${#CARDS[@]} -ge 1 ]] || { echo "phase $NAME: no CARDS manifest" >&2; exit 1; }
for id in "${CARDS[@]}"; do
  declare -F "card_$id" >/dev/null 2>&1 || { echo "phase $NAME: missing card function card_$id" >&2; exit 1; }
done

# Verify the chain has no gaps: each card declares NEXT <id> matching the next manifest entry.
for i in "${!CARDS[@]}"; do
  id="${CARDS[$i]}"
  expected="${CARDS[$((i+1))]:-END}"
  declared="$(sed -n "s/^# NEXT: *${id} *-> *//p" "$SCRIPT" | head -1)"
  declared="${declared:-END}"
  if [[ "$declared" != "$expected" ]]; then
    echo "phase $NAME: CHAIN GAP at $id (declared NEXT=$declared, expected=$expected)" >&2
    exit 1
  fi
done

START_MS="$(date +%s%3N)"
PASSED=0; FAILED=0; BLOCKED=0; TOTAL=0

phase_log() { printf '[%s] %s\n' "$NAME" "$*" | tee -a "$LOG"; }

# ---------------------------------------------------------------------------
# PRE: verify the environment is clean before any card runs.
# ---------------------------------------------------------------------------
if declare -F "$PRE_FN" >/dev/null 2>&1; then
  if ! "$PRE_FN"; then
    phase_log "PRE failed — environment not clean; aborting phase"
    exit 1
  fi
  phase_log "PRE passed"
else
  phase_log "no PRE function declared"
fi

# ---------------------------------------------------------------------------
# Card loop with retry / backoff and FAILED vs FLAKY classification.
# ---------------------------------------------------------------------------
for id in "${CARDS[@]}"; do
  TOTAL=$((TOTAL+1))
  phase_log "running $id"
  result="pass"
  attempt=1
  while :; do
    if "card_$id" >/dev/null 2>>"$LOG"; then
      result="pass"
      break
    fi
    phase_log "$id attempt $attempt failed"
    if [[ "$attempt" -ge 3 ]]; then
      if [[ "$(card_is_deterministic "$id")" == "no" ]]; then
        result="flaky"
      else
        result="fail"
      fi
      break
    fi
    sleep $((2 * attempt))   # backoff: 2s then 4s
    attempt=$((attempt+1))
  done

  case "$result" in
    pass)  PASSED=$((PASSED+1)); phase_log "$id PASSED" ;;
    flaky) BLOCKED=$((BLOCKED+1)); phase_log "$id FLAKY (non-deterministic; blocking downstream gate)" ;;
    fail)
      FAILED=$((FAILED+1)); phase_log "$id FAILED"
      # Post-failure cleanup: run the card's cleanup + rollback hook if declared.
      if declare -F "cleanup_$id" >/dev/null 2>&1; then
        "cleanup_$id" >>"$LOG" 2>&1 || phase_log "$id cleanup hook failed"
      fi
      if declare -F "rollback_$id" >/dev/null 2>&1; then
        "rollback_$id" >>"$LOG" 2>&1 || phase_log "$id rollback hook failed"
      fi
      # Stop the phase: a deterministic failure is a phase-level NO-GO.
      break
      ;;
  esac
done

# ---------------------------------------------------------------------------
# POST: teardown.
# ---------------------------------------------------------------------------
if declare -F "$POST_FN" >/dev/null 2>&1; then
  "$POST_FN" >>"$LOG" 2>&1 || phase_log "POST teardown failed"
  phase_log "POST teardown done"
fi

END_MS="$(date +%s%3N)"
ELAPSED=$((END_MS - START_MS))

if [[ "$FAILED" -eq 0 && "$BLOCKED" -eq 0 && "$PASSED" -eq "$TOTAL" ]]; then
  GATE="GO"
else
  GATE="NO-GO"
fi

SUMMARY_JSON="$(printf '{"phase": "%s", "tests_run": %d, "passed": %d, "failed": %d, "blocked": %d, "total_time_ms": %d, "go_no_go": "%s"}' \
  "$NAME" "$TOTAL" "$PASSED" "$FAILED" "$BLOCKED" "$ELAPSED" "$GATE")"
printf '%s\n' "$SUMMARY_JSON" | tee -a "$SUMMARY"
phase_log "summary: $SUMMARY_JSON"

[[ "$GATE" == "GO" ]] || exit 1
exit 0

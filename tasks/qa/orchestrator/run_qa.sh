#!/usr/bin/env bash
# ============================================================================
# The Forge — Master Test Orchestrator (the "ONE COMMAND" entry point)
#
# Runs the full 7-phase QA suite unattended:
#   Phase 1: Unit / module isolation
#   Phase 2: Integration (real interfaces, data contracts)
#   Phase 3: End-to-end / workflow
#   Phase 4: Performance & load
#   Phase 5: Security & compliance
#   Phase 6: Production readiness / smoke
#   Phase 7: Continuous validation (post-deploy synthetic monitoring)
#
# Usage:
#   ./run_qa.sh [--env qa|staging|production] [--skip-build] [--smoke-only] [--help]
#
# Exit codes:
#   0 = ALL phases GO
#   1 = environment preflight failure
#   2 = at least one phase NO-GO (report printed; NO rollback needed unless a
#       card explicitly triggers one)
#   3 = abort: build / deploy step failed before tests could run
#
# JSON phase summaries are appended to ./qa-results/<ts>/summary.jsonl and a
# human log to ./qa-results/<ts>/run.log. A final Go/No-Go report is written
# to ./qa-results/<ts>/go-no-go.json.
# ============================================================================

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QA_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$(dirname "$QA_DIR")")"

# ---------------------------------------------------------------------------
# Config (all overridable via environment)
# ---------------------------------------------------------------------------
QA_ENV="${QA_ENV:-qa}"
SKIP_BUILD="${SKIP_BUILD:-0}"
SMOKE_ONLY="${SMOKE_ONLY:-0}"
BACKEND_DIR="${BACKEND_DIR:-$REPO_ROOT/backend}"
FRONTEND_DIR="${FRONTEND_DIR:-$REPO_ROOT/frontend}"
VENV_DIR="${VENV_DIR:-$BACKEND_DIR/.venv}"
PHASE_DIR="$QA_DIR/cards"
RESULTS_ROOT="${QA_RESULTS_ROOT:-$QA_DIR/qa-results}"
TS="$(date +%Y%m%d-%H%M%S)"
RESULTS_DIR="$RESULTS_ROOT/$TS"
LOG_FILE="$RESULTS_DIR/run.log"
SUMMARY_FILE="$RESULTS_DIR/summary.jsonl"
GONOGO_FILE="$RESULTS_DIR/go-no-go.json"
mkdir -p "$RESULTS_DIR"

# Source the assertion library (retries, JSON summaries, gates).
# shellcheck source=orchestrator/assert_lib.sh
source "$SCRIPT_DIR/assert_lib.sh"

log()  { printf '%s\n' "$*" | tee -a "$LOG_FILE"; }
die()  { log "FATAL: $*"; exit "${2:-1}"; }

show_help() {
  sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

# ---------------------------------------------------------------------------
# Argument parsing (deterministic, no prompts)
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env) QA_ENV="${2:?--env requires a value}"; shift 2 ;;
    --skip-build) SKIP_BUILD=1; shift ;;
    --smoke-only) SMOKE_ONLY=1; shift ;;
    --help|-h) show_help ;;
    *) die "unknown argument: $1" 1 ;;
  esac
done

case "$QA_ENV" in
  qa|staging|production) ;;
  *) die "--env must be one of: qa staging production (got '$QA_ENV')" 1 ;;
esac

# The qa compose stack runs from a qa-specific env file (dev security posture,
# generous rate limits) so the black-box suite is not throttled or locked out
# by production values in the committed .env. Staging/production keep .env.
if [[ "$QA_ENV" == "qa" ]]; then
  export QA_ENV_FILE="${QA_ENV_FILE:-$REPO_ROOT/.env.qa}"
fi

# ---------------------------------------------------------------------------
# Preflight: verify every tool the suite needs exists. (Fails fast, no prompts.)
# ---------------------------------------------------------------------------
preflight() {
  local missing=0
  for tool in git docker node python3 curl jq; do
    command -v "$tool" >/dev/null 2>&1 || { log "MISSING TOOL: $tool"; missing=1; }
  done
  # Backend venv with pytest + coverage (per repo CI contract).
  if [[ ! -x "$VENV_DIR/bin/pytest" ]]; then
    log "MISSING: backend venv pytest at $VENV_DIR/bin/pytest (create: cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)"
    missing=1
  fi
  [[ -d "$REPO_ROOT/.git" ]] || { log "MISSING: $REPO_ROOT/.git"; missing=1; }
  [[ "$missing" -eq 0 ]] || die "preflight failed — see missing items above" 1
  log "preflight OK (env=$QA_ENV, skip_build=$SKIP_BUILD, smoke_only=$SMOKE_ONLY)"
}

# ---------------------------------------------------------------------------
# Environment reset — guarantees a clean slate before every phase.
# ---------------------------------------------------------------------------
reset_env() {
  log "[orchestrator] resetting environment (env=$QA_ENV)"
  case "$QA_ENV" in
    qa)
      docker compose --env-file "$REPO_ROOT/.env.qa" -f "$REPO_ROOT/docker-compose.yml" down -v --remove-orphans >/dev/null 2>&1 || true
      ;;
    staging)
      docker compose -f "$REPO_ROOT/docker-compose.prod.yml" down -v --remove-orphans >/dev/null 2>&1 || true
      ;;
    production)
      # NEVER tear down a live production stack. Phases 6-7 assume the stack is
      # already deployed; reset only pytest caches (health is verified per phase).
      log "[orchestrator] production: skipping compose teardown (stack is live by design)"
      ;;
  esac
  # Remove pytest caches for a clean run.
  rm -rf "$BACKEND_DIR/.pytest_cache" "$BACKEND_DIR/.coverage" >/dev/null 2>&1 || true
  # Verify the reset worked (production keeps its containers; qa/staging must be empty).
  if [[ "$QA_ENV" == "production" ]]; then
    wait_for_http "http://localhost:80/health" "200" "30" "3"
    return $?
  fi
  local up
  up="$(docker ps --format '{{.Names}}' 2>/dev/null | wc -l)"
  assert_eq "$up" "0" "no forge containers running after teardown"
}

# ---------------------------------------------------------------------------
# Build stage — builds backend, frontend, and (for qa/staging) the compose
# stack. Deterministic, idempotent.
# ---------------------------------------------------------------------------
build_stack() {
  if [[ "$SKIP_BUILD" -eq 1 ]]; then
    log "[orchestrator] --skip-build set; using existing images/artifacts"
    return 0
  fi
  log "[orchestrator] building stack (env=$QA_ENV)"

  # Backend: install + import smoke.
  ( cd "$BACKEND_DIR" && "$VENV_DIR/bin/pip" install -q -r requirements.txt ) \
    || die "backend dependency install failed" 3
  ( cd "$BACKEND_DIR" && "$VENV_DIR/bin/python" -c "import app.main" ) \
    || die "backend import smoke failed" 3

  # Frontend: typecheck + build. npm omits devDependencies when
  # NODE_ENV=production, which strips tsc/vite — so unset it for the install
  # and build (same convention as phase-1's `env -u NODE_ENV`).
  ( cd "$FRONTEND_DIR" && env -u NODE_ENV npm ci --silent ) || die "npm ci failed" 3
  ( cd "$FRONTEND_DIR" && env -u NODE_ENV npm run build --silent ) || die "frontend build failed" 3

  # Full stack for qa/staging (Phases 2-7 need live services).
  case "$QA_ENV" in
    qa)
      docker compose --env-file "$REPO_ROOT/.env.qa" -f "$REPO_ROOT/docker-compose.yml" up -d --build || die "compose up (qa) failed" 3
      ;;
    staging)
      docker compose -f "$REPO_ROOT/docker-compose.prod.yml" up -d --build || die "compose up (staging) failed" 3
      ;;
    production)
      # Production builds are NOT triggered by QA; assume deployed. Health is
      # verified in Phase 6. Nothing to do here.
      ;;
  esac
  log "[orchestrator] build complete"
}

# ---------------------------------------------------------------------------
# Phase execution — delegates to run_phase.sh, collecting JSON summaries.
# ---------------------------------------------------------------------------
run_phase() {
  local name="$1" script="$2" gate="$3"
  log "[orchestrator] starting phase: $name"
  local start_ms end_ms elapsed
  start_ms="$(date +%s%3N)"
  "$SCRIPT_DIR/run_phase.sh" \
      --name "$name" \
      --script "$PHASE_DIR/$script" \
      --env "$QA_ENV" \
      --backend-dir "$BACKEND_DIR" \
      --frontend-dir "$FRONTEND_DIR" \
      --venv "$VENV_DIR" \
      --log "$LOG_FILE" \
      --summary "$SUMMARY_FILE" || { gate="FAILED"; }
  end_ms="$(date +%s%3N)"
  elapsed=$((end_ms - start_ms))
  log "[orchestrator] phase $name finished in ${elapsed}ms (gate=$gate)"
  [[ "$gate" == "OK" ]] || return 1
  return 0
}

# ===========================================================================
# MAIN — sequential phase chain (no gaps, no manual gates)
# ===========================================================================
main() {
  preflight
  reset_env
  build_stack

  if [[ "$SMOKE_ONLY" -eq 1 ]]; then
    log "[orchestrator] --smoke-only: running Phase 6 only"
    if run_phase "production-readiness" "phase-6-production.md" "OK"; then
      emit_go_no_go 0
      exit 0
    fi
    emit_go_no_go 2
    exit 2
  fi

  local phase_failed=0
  run_phase "unit"            "phase-1-unit.md"            "OK" || phase_failed=1
  [[ "$phase_failed" -eq 0 ]] || { emit_go_no_go 2; exit 2; }

  run_phase "integration"     "phase-2-integration.md"     "OK" || phase_failed=1
  [[ "$phase_failed" -eq 0 ]] || { emit_go_no_go 2; exit 2; }

  run_phase "e2e"             "phase-3-e2e.md"             "OK" || phase_failed=1
  [[ "$phase_failed" -eq 0 ]] || { emit_go_no_go 2; exit 2; }

  run_phase "performance"     "phase-4-performance.md"     "OK" || phase_failed=1
  [[ "$phase_failed" -eq 0 ]] || { emit_go_no_go 2; exit 2; }

  run_phase "security"        "phase-5-security.md"        "OK" || phase_failed=1
  [[ "$phase_failed" -eq 0 ]] || { emit_go_no_go 2; exit 2; }

  # Phases 6-7 (production readiness + continuous validation) exercise the
  # production compose stack (docker-compose.prod.yml: backup service,
  # ENVIRONMENT=production → HSTS, prometheus via nginx) — none of which the
  # qa/dev stack provides. They gate only staging/production runs; for qa they
  # are recorded as skipped so the dev-stack suite stays green (see
  # fixtures/env-matrix.md: "Phases 1-5 run in qa").
  if [[ "$QA_ENV" == "qa" ]]; then
    log "[orchestrator] env=qa: skipping phases 6-7 (production-stack only; see fixtures/env-matrix.md)"
  else
    run_phase "production"      "phase-6-production.md"      "OK" || phase_failed=1
    [[ "$phase_failed" -eq 0 ]] || { emit_go_no_go 2; exit 2; }

    run_phase "continuous"      "phase-7-continuous.md"      "OK" || phase_failed=1
  fi

  emit_go_no_go "$phase_failed"
  if [[ "$phase_failed" -eq 0 ]]; then
    log "[orchestrator] RESULT: ALL PHASES GO"
    exit 0
  fi
  log "[orchestrator] RESULT: at least one phase NO-GO — see $SUMMARY_FILE"
  exit 2
}

# emit_go_no_go <overall_exit_code>
emit_go_no_go() {
  local code="$1"
  local verdict="GO"
  [[ "$code" -eq 0 ]] || verdict="NO-GO"
  printf '{"overall_verdict": "%s", "env": "%s", "results_dir": "%s"}\n' \
    "$verdict" "$QA_ENV" "$RESULTS_DIR" > "$GONOGO_FILE"
  log "[orchestrator] final verdict: $verdict (see $GONOGO_FILE)"
}

main "$@"

# Day 32 — Test Specification

## Test File
`backend/tests/unit/gamification/test_achievements.py`

## Test Cases
1. `test_first_run_achievement_earned` — total_runs=1 → "first_run" achievement earned
2. `test_top_decile_requires_90th_percentile` — percentile=89 → not earned; 90 → earned
3. `test_ai_challenger_requires_5_beats` — beat_ai_count=4 → not earned; 5 → earned
4. `test_cost_guard_monthly_budget` — usage > limit → 429 raised
5. `test_i18n_language_instruction_en_is_empty` — English returns empty string
6. `test_i18n_language_instruction_es_contains_spanish` — "Spanish" in instruction text
7. `test_model_router_falls_back_to_default` — unknown task → returns LLM_MODEL value
8. `test_format_currency_usd` — format_currency(1500, "USD") → "$1,500"

## Run Commands
```bash
cd backend && pytest tests/unit/gamification/ -v
cd frontend && npm run build && npm run lint
```

## Expected
```
8 passed
Build: 0 errors
Lint: 0 errors
```

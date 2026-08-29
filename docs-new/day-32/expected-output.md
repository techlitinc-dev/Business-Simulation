# Day 32 — Expected Output

## Files Created
```
backend/app/agents/llm/router.py
backend/app/services/cost_guard.py
backend/app/utils/i18n.py
backend/app/services/gamification/__init__.py
backend/app/services/gamification/achievements.py
backend/app/services/gamification/certification.py
backend/app/api/v1/endpoints/gamification.py
frontend/src/features/gamification/AchievementToast.tsx
frontend/src/features/gamification/CertificationBadge.tsx
backend/tests/unit/gamification/__init__.py
backend/tests/unit/gamification/test_achievements.py
```

## Files Modified
```
backend/app/core/config.py    — MODEL_EXECUTIVE_SUMMARY, MODEL_NARRATIVE etc. added
backend/app/agents/section_writer.py — uses router.get_model_for_task()
```

## Model Routing (via .env)
```env
# Use a reasoning model for executive summary and counterfactual
DEEPSEEK_MODEL_EXECUTIVE_SUMMARY=deepseek-reasoner
DEEPSEEK_MODEL_COUNTERFACTUAL=deepseek-reasoner
# Bulk narrative uses cheaper model
DEEPSEEK_MODEL_NARRATIVE=deepseek-chat
```

## Cost Guard Behavior
- Monthly usage at limit: next report request → 429 with `{"error": "monthly_token_budget_exceeded", "used": 2000001, "limit": 2000000}`
- Per-report limit hit mid-generation → current section aborted, fallback data-only render for remainder

## Localization
- Report in Spanish: `POST /reports/deep-dive` with `lang=es` → all narrative sections in Spanish
- Numbers, dates, currency still formatted correctly

## Achievements Earned
```json
[
  {"id": "first_run", "title": "Simulation Pioneer", "icon": "🚀"},
  {"id": "top_decile", "title": "Top Decile Resilience", "icon": "🏆"}
]
```

## Certification PDF
- Cover page with "Forge-Validated Business Certificate"
- Score, percentile, 4 criteria checkmarks
- Run ID and generation date

## Pytest: 8 passed
## Build: 0 errors
## Lint: 0 errors

---

## Final Deliverable Summary

All 32 days complete. Full `docs-new/` folder structure:
```
docs-new/
  day-01/ through day-32/
    instructions.md   — step-by-step implementation with code
    test.md           — test cases, file paths, run commands
    expected-output.md — API responses, file outputs, pytest results
    manual-test.md    — QA checklist with curl commands and UI steps
```

Total: 128 files covering F-01 through F-12 across 32 working days.

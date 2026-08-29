# Day 28 — Test Specification

## Test File
`backend/tests/unit/journal/test_journal_service.py`

## Test Cases
1. `test_score_positive_following_ai` — positive delta + followed AI → score=1.0
2. `test_score_positive_not_following_ai` — positive delta + didn't follow AI → score=0.5
3. `test_score_negative_outcome` — negative delta → score=0.0
4. `test_generate_playbook_returns_playbook` — MockProvider → Playbook with title, steps≥3
5. `test_journal_summary_beat_ai_pct` — 3 decisions, 2 beat AI → 66.7%

## Run Commands
```bash
cd backend && pytest tests/unit/journal/ -v
cd frontend && npm run build
```

## Expected
```
5 passed
Build: 0 errors
```

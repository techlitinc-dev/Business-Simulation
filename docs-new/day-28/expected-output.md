# Day 28 — Expected Output

## Files Created
```
backend/app/services/journal/journal_service.py
backend/app/agents/playbook_writer.py
backend/app/agents/prompts/playbook_writer.md
backend/app/api/v1/endpoints/journal.py
frontend/src/features/journal/DecisionJournalPage.tsx
backend/tests/unit/journal/test_journal_service.py
```

## Sample Journal Summary
```json
{
  "total_decisions": 7,
  "beat_ai_count": 4,
  "beat_ai_pct": 57.1,
  "summary": "You beat the AI's recommended path in 4 of 7 decisions"
}
```

## Decision Journal UI
- Summary card: "You beat the AI's recommended path in 4 of 7 decisions — 57.1% beat rate"
- Chronological list: Month 3 · "Reduce pricing by 20%" · ✅ Beat AI · 100pts
- Red entries: ❌ Missed AI · 0pts

## Pytest: 5 passed

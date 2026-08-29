# Day 18 — Expected Output

## Files Created
```
backend/app/services/copilot/__init__.py
backend/app/services/copilot/context_builder.py
backend/app/services/copilot/copilot_service.py
backend/app/agents/prompts/copilot_system.md
backend/app/api/v1/endpoints/copilot.py
backend/tests/unit/copilot/__init__.py
backend/tests/unit/copilot/test_copilot_service.py
```

## Sample Chat Response
```json
{
  "answer": "Cash dipped in month 9 because a demand shock event reduced revenue by 23% while fixed costs remained constant, depleting cash reserves from $82,000 to $61,000.",
  "sources_used": ["tick_logs", "events_decisions"],
  "confidence": "HIGH",
  "grounded": true,
  "flagged_claims": []
}
```

## Sample Flagged Response
```json
{
  "answer": "The company had $1,250,000 in revenue in month 6.",
  "grounded": false,
  "flagged_claims": ["1250000"]
}
```

## Pytest: 5 passed

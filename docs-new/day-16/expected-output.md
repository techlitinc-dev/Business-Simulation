# Day 16 — Expected Output

## Files Created
```
backend/app/agents/advisory_board.py
backend/app/schemas/advisory.py
backend/app/agents/prompts/cfo_persona.md
backend/app/agents/prompts/cmo_persona.md
backend/app/agents/prompts/risk_auditor_persona.md
backend/app/agents/prompts/operator_persona.md
backend/tests/unit/agents/test_advisory_board.py
```

## Sample Output (MockProvider)
```json
{
  "reviews": [
    {"persona": "CFO", "verdict": "Cash runway is dangerously short at 14 months median.", "top_concerns": ["High CAC", "Burn rate"], "opportunities": ["Reduce fixed costs"], "questions_for_founder": ["What is your plan for month 12?"], "confidence_level": "HIGH"},
    {"persona": "CMO", "verdict": "CAC of $450 is manageable if churn stays below 5%.", "top_concerns": ["5% churn is high for B2B"], "opportunities": ["Email nurture can reduce CAC"], "questions_for_founder": ["What is your CAC payback target?"], "confidence_level": "MEDIUM"},
    {"persona": "RiskAuditor", "verdict": "58% survival rate puts this in HIGH risk category.", "top_concerns": ["Cash exhaustion in 41% of runs"], "opportunities": [], "questions_for_founder": ["What triggers a pivot decision?"], "confidence_level": "HIGH"},
    {"persona": "Operator", "verdict": "Headcount plan looks unsupported by revenue growth.", "top_concerns": ["Scaling costs ahead of revenue"], "opportunities": ["Contractor model for first 6 months"], "questions_for_founder": ["When does the team scale?"], "confidence_level": "MEDIUM"}
  ],
  "summary": {
    "consensus_verdict": "The business faces HIGH risk with a 58% survival rate and 14-month median runway.",
    "points_of_agreement": ["Cash runway is the primary risk", "CAC needs to decrease"],
    "points_of_conflict": ["CFO wants cost cuts; CMO wants growth spend"],
    "top_priority_action": "Reduce monthly burn rate by 20% within 60 days.",
    "overall_risk_level": "HIGH"
  }
}
```

## Pytest: 6 passed

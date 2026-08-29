# Day 13 — Expected Output

## Files Created
```
backend/app/services/actuals/variance.py
backend/app/agents/variance_narrator.py
backend/app/agents/prompts/variance_narrative.md
backend/tests/unit/actuals/test_variance.py
```

## Sample VarianceDelta
```python
VarianceDelta(
  blueprint_id="bp_abc",
  month=3,
  prior_survival_rate=0.72,
  new_survival_rate=0.58,
  survival_delta=-0.14,
  prior_runway_median=19.0,
  new_runway_median=14.0,
  runway_delta=-5.0,
  prior_resilience_score=68.4,
  new_resilience_score=54.1,
  score_delta=-14.3,
  key_changes=["monthly_churn increased from 0.05 to 0.08"]
)
```

## Sample VarianceNarrativeOutput
```json
{
  "headline": "Your simulated 24-month survival dropped from 72% to 58% — a 14pp decline driven by higher churn.",
  "explanation": "Your Month 3 actuals show monthly churn increased from 5% to 8%, which is the single largest driver of this variance...",
  "primary_driver": "monthly_churn increased from 0.05 to 0.08",
  "outlook": "If churn remains at 8%, the model projects median runway shortening by 5 months to 14 months."
}
```

## Pytest: 13 total passing

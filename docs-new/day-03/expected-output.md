# Day 03 — Expected Output

## Files Created
```
backend/app/agents/section_writer.py
backend/app/agents/prompts/sections/executive_summary.md
backend/app/agents/prompts/sections/financial_narrative.md
backend/app/agents/prompts/sections/weaknesses_register.md
backend/app/agents/prompts/sections/generic_narrative.md
backend/app/services/deep_report/section_linter.py
backend/tests/unit/deep_report/test_section_writer.py
backend/tests/unit/deep_report/test_section_linter.py
```

## Files Modified
- `backend/app/workers/report_job.py` — section loop now calls generate_section + lint

## Pytest: 12 passed

## Sample `generate_section` Output (MockProvider)
```json
{
  "verdict": "Simulation indicates HIGH risk — survival rate 58% over 24 months.",
  "headline_metrics": [
    "Survival rate: 58%",
    "Median runway: 14 months",
    "Top kill vector: cash exhaustion (41% of failure runs)"
  ],
  "narrative": "The simulated business faces significant financial headwinds...",
  "risk_level": "HIGH",
  "section_number": 2,
  "title": "Executive Summary"
}
```

## Celery Job Log With Real Section Writer
```
[INFO] [section_writer] Generating section 2: Executive Summary
[INFO] [report_job] job=X section=2/21 'Executive Summary' ✓ lint passed
[INFO] [section_writer] Generating section 3: Business Blueprint Overview
[WARNING] [report_job] Lint failed section 3: ['Banned phrase found: ...'] Retrying.
[INFO] [section_writer] Generating section 3: Business Blueprint Overview (retry)
[INFO] [report_job] job=X section=3/21 ✓ lint passed on retry
```

## Fallback Render Example
When DeepSeek fails or lint fails twice:
```markdown
# Kill-Vector Autopsy

_AI narrative unavailable — displaying raw simulation data._

## Mc Aggregates
```json
{"survival_rate": 0.58, "kill_vectors": [...]}
```
```

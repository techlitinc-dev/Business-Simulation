# Day 03 — Manual Test Checklist

## Checklist

### 1. Test section generation with MockProvider (no API key)
```python
import asyncio, os
os.environ["LLM_PROVIDER"] = "mock"
from app.agents.section_writer import generate_section
from app.services.deep_report.manifest import SectionDef, DataInputKey

section = SectionDef(section_number=2, title="Executive Summary", page_budget=2,
    data_inputs=[DataInputKey.MC_AGGREGATES], prompt_template="executive_summary.md")
data_pack = {"mc_aggregates": {"survival_rate": 0.72, "median_lifespan": 18}}

result = asyncio.run(generate_section(section, data_pack))
print(result.keys())
```
- [ ] Result has `narrative`, `section_number`, `title` keys
- [ ] No exception raised

### 2. Test linter on valid content
```python
from app.services.deep_report.section_linter import lint_section

section_output = {"narrative": "The business simulation shows a survival rate of 72 percent over 24 months. " * 10}
lint = lint_section(section, section_output, data_pack)
print(lint.passed, lint.errors)
```
- [ ] `lint.passed == True`

### 3. Test linter catches banned phrase
```python
section_output = {"narrative": "As an AI, I cannot determine the exact survival rate. " * 10}
lint = lint_section(section, section_output, data_pack)
print(lint.passed, lint.errors)
```
- [ ] `lint.passed == False`
- [ ] Error message mentions "as an ai"

### 4. Test fallback render
```python
from app.agents.section_writer import render_data_only_fallback
fallback = render_data_only_fallback(section, data_pack)
print(fallback["is_fallback"])  # True
print(fallback["narrative"][:100])
```
- [ ] `is_fallback` is True
- [ ] Narrative contains "AI narrative unavailable"

### 5. Run full Celery job end-to-end (MockProvider)
```python
from app.workers.report_job import generate_deep_report
result = generate_deep_report.delay(
    job_id="day03-test", run_id="any", report_type="resilience_audit", tier="free"
)
import time; time.sleep(3)
print(result.result)
```
- [ ] Job completes
- [ ] 3 sections returned (free tier)
- [ ] Each section has a `narrative` key

### 6. Full pytest suite
```bash
cd backend && pytest --tb=short -q
```
- [ ] All previous tests pass
- [ ] New tests pass
- [ ] 0 failures

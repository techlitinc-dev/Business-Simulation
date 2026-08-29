# Day 01 — Test Specification

## Test File Location
`backend/tests/unit/deep_report/test_manifest.py`

Also create the package init:
`backend/tests/unit/deep_report/__init__.py` (empty)

---

## Test Cases

### 1. `test_full_manifest_section_count`
**Asserts:** `FULL_MANIFEST` has exactly 21 sections.
```python
assert len(FULL_MANIFEST.sections) == 21
```

### 2. `test_full_manifest_total_pages`
**Asserts:** Total page budget across all sections sums to 70.
```python
assert FULL_MANIFEST.total_page_budget == 70
```

### 3. `test_free_tier_sections`
**Asserts:** Free tier returns exactly 3 sections: 2 (Executive Summary), 9 (MC Results), 11 (Weaknesses).
```python
sections = FULL_MANIFEST.sections_for_tier(ReportTier.FREE)
assert len(sections) == 3
assert {s.section_number for s in sections} == {2, 9, 11}
```

### 4. `test_pro_tier_sections`
**Asserts:** Pro tier includes sections 1–13 but not 14–21.
```python
sections = FULL_MANIFEST.sections_for_tier(ReportTier.PRO)
numbers = {s.section_number for s in sections}
assert numbers.issuperset({1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13})
assert 14 not in numbers
assert 21 not in numbers
```

### 5. `test_enterprise_tier_all_sections`
**Asserts:** Enterprise tier returns all 21 sections.
```python
sections = FULL_MANIFEST.sections_for_tier(ReportTier.ENTERPRISE)
assert len(sections) == 21
```

### 6. `test_section_def_invalid_section_number`
**Asserts:** `SectionDef` with `section_number=0` raises a Pydantic `ValidationError`.
```python
with pytest.raises(ValidationError):
    SectionDef(section_number=0, title="x", page_budget=2,
               data_inputs=[], prompt_template="x.md")
```

### 7. `test_section_def_invalid_title_too_short`
**Asserts:** `SectionDef` with a 1-character title raises `ValidationError`.
```python
with pytest.raises(ValidationError):
    SectionDef(section_number=1, title="x", page_budget=2,
               data_inputs=[], prompt_template="x.md")
```

### 8. `test_get_manifest_known_type`
**Asserts:** `get_manifest("resilience_audit")` returns a `ReportManifest` instance.
```python
manifest = get_manifest("resilience_audit")
assert isinstance(manifest, ReportManifest)
```

### 9. `test_get_manifest_unknown_raises`
**Asserts:** `get_manifest("nonexistent")` raises `KeyError`.
```python
with pytest.raises(KeyError):
    get_manifest("nonexistent")
```

### 10. `test_manifest_page_budget_auto_computed`
**Asserts:** Creating a `ReportManifest` with 2 sections of page_budget 3 and 5 yields `total_page_budget == 8`.
```python
manifest = ReportManifest(
    name="Test", report_type="resilience_audit", tier=ReportTier.FREE,
    sections=[
        SectionDef(section_number=1, title="Sec One", page_budget=3,
                   data_inputs=[DataInputKey.RUN_METADATA], prompt_template="x.md"),
        SectionDef(section_number=2, title="Sec Two", page_budget=5,
                   data_inputs=[DataInputKey.BLUEPRINT], prompt_template="y.md"),
    ]
)
assert manifest.total_page_budget == 8
```

### 11. `test_data_pack_stub_returns_all_keys`
**Asserts:** The stub `build_data_pack` returns a dict with all requested `DataInputKey` values as keys, all set to `None`.
```python
import asyncio
from app.services.deep_report.data_pack import build_data_pack
from app.services.deep_report.manifest import SectionDef, DataInputKey

section = SectionDef(section_number=2, title="Executive Summary", page_budget=2,
                     data_inputs=[DataInputKey.TICK_LOGS, DataInputKey.MC_AGGREGATES],
                     prompt_template="executive_summary.md")

async def _run():
    return await build_data_pack(section, "run_test_123", db=None)

result = asyncio.get_event_loop().run_until_complete(_run())
assert "tick_logs" in result
assert "mc_aggregates" in result
assert result["tick_logs"] is None
```

### 12. `test_celery_task_importable`
**Asserts:** `generate_deep_report` can be imported and has the correct task name.
```python
from app.workers.report_job import generate_deep_report
assert generate_deep_report.name == "workers.report_job.generate_deep_report"
```

---

## Run Commands

```bash
# Run all day-01 tests
cd backend && pytest tests/unit/deep_report/test_manifest.py -v

# Run with coverage
cd backend && pytest tests/unit/deep_report/test_manifest.py -v --cov=app/services/deep_report --cov-report=term-missing

# Run lint
cd backend && ruff check app/services/deep_report/ app/workers/report_job.py

# Run type check
cd backend && mypy app/services/deep_report/ app/workers/report_job.py --ignore-missing-imports
```

---

## Expected Test Output
```
tests/unit/deep_report/test_manifest.py::test_full_manifest_section_count PASSED
tests/unit/deep_report/test_manifest.py::test_full_manifest_total_pages PASSED
tests/unit/deep_report/test_manifest.py::test_free_tier_sections PASSED
tests/unit/deep_report/test_manifest.py::test_pro_tier_sections PASSED
tests/unit/deep_report/test_manifest.py::test_enterprise_tier_all_sections PASSED
tests/unit/deep_report/test_manifest.py::test_section_def_invalid_section_number PASSED
tests/unit/deep_report/test_manifest.py::test_section_def_invalid_title_too_short PASSED
tests/unit/deep_report/test_manifest.py::test_get_manifest_known_type PASSED
tests/unit/deep_report/test_manifest.py::test_get_manifest_unknown_raises PASSED
tests/unit/deep_report/test_manifest.py::test_manifest_page_budget_auto_computed PASSED
tests/unit/deep_report/test_manifest.py::test_data_pack_stub_returns_all_keys PASSED
tests/unit/deep_report/test_manifest.py::test_celery_task_importable PASSED

12 passed in <2s
```

# Day 04 — Test Specification

## Test File
`backend/tests/unit/deep_report/test_charts.py`

## Test Cases

### 1. `test_cash_flow_curve_returns_png_bytes` — output starts with PNG magic bytes `\x89PNG`
### 2. `test_mc_histogram_returns_png_bytes` — valid PNG bytes
### 3. `test_kill_vector_bar_returns_png_bytes` — valid PNG bytes
### 4. `test_tornado_chart_returns_png_bytes` — valid PNG bytes
### 5. `test_cohort_gauge_returns_png_bytes` — valid PNG bytes
### 6. `test_charts_are_deterministic` — same input → identical byte output
### 7. `test_render_charts_for_run_creates_files` — 4 PNG files exist in output dir
### 8. `test_chart_bundle_get_path` — get_path() returns existing file >1KB
### 9. `test_empty_mc_does_not_crash` — kill_vector_bar({}) returns bytes without error
### 10. `test_chart_files_are_valid_png_size` — each PNG file is larger than 5KB (real image)

## Run Commands
```bash
cd backend && pytest tests/unit/deep_report/test_charts.py -v
cd backend && ruff check app/utils/charts.py
```

## Expected
```
10 passed in <5s
```

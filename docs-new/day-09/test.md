# Day 09 — Test Specification

## Test File
`backend/tests/unit/whatif/test_visualizer.py`

## Test Cases
1. `test_heatmap_returns_png_bytes` — starts with PNG magic bytes
2. `test_survival_line_chart_returns_png_bytes` — valid PNG
3. `test_render_sweep_charts_creates_three_files` — heatmap.png, survival_line.png, tornado.png all exist
4. `test_render_sweep_charts_returns_bundle_with_all_keys` — bundle.charts has 3 keys
5. `test_heatmap_is_deterministic` — same input → identical bytes
6. `test_heatmap_with_single_point_does_not_crash` — 1 grid point renders without error

## Run Commands
```bash
cd backend && pytest tests/unit/whatif/ -v
```

## Expected
```
All whatif tests passing (8 from Day 08 + 6 new = 14 total)
```

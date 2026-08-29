# Day 09 — Expected Output

## Files Created
```
backend/app/services/whatif/visualizer.py
backend/tests/unit/whatif/test_visualizer.py
```
## Files Modified
```
backend/app/utils/charts.py  — added sweep_heatmap(), survival_line_chart()
```

## Chart Descriptions
- **heatmap.png**: 1-row colored grid, green=high survival, red=low, % annotation in each cell
- **survival_line.png**: Blue line with P25/P75 shaded band, yellow dashed 50% threshold line
- **tornado.png**: Single horizontal bar showing survival delta range across the swept parameter

## Pytest: 14 total passing (8 + 6 new)

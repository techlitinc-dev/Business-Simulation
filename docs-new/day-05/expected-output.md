# Day 05 — Expected Output

## Files Created
```
backend/app/assets/report_template.css
backend/app/utils/pdf_deep.py
backend/app/services/deep_report/assembler.py
backend/tests/unit/deep_report/test_assembler.py
```

## Pytest: 7 passed

## PDF Output Properties
- File extension: `.pdf`
- Header bytes: `%PDF-1.5` (WeasyPrint output)
- File size: ~200KB–2MB depending on number of sections and charts
- Pages: 5 (free) / ~25 (pro) / ~70 (enterprise)

## PDF Visual Structure (in order)
1. Cover page — dark background, title "Business Simulation Resilience Audit", workspace name, run ID, date, tier badge
2. Table of contents — section numbers and titles with dotted separator
3. Section 1: Cover, Disclaimer, Table of Contents
4. Section 2: Executive Summary (with metric cards if generated)
5. … all sections …
6. Section 6: includes cash_flow.png chart
7. Section 9: includes mc_histogram.png chart
8. Section 10: includes kill_vectors.png chart
9. Final section: Glossary, Data Dictionary & Reproducibility

## Footer/Header (every page after cover)
- Header: "Business Simulation Audit" (centered)
- Footer left: workspace name
- Footer right: "Page N of M"

## Fallback (no WeasyPrint)
Returns UTF-8 HTML bytes — importable and renderable in a browser.

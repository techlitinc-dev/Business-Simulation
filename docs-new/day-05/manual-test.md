# Day 05 — Manual Test Checklist

## Checklist

### 1. Run assembler in Python shell
```python
import asyncio
from app.services.deep_report.assembler import assemble_report

sections = [
    {"section_number": 2, "title": "Executive Summary", "narrative": "Survival rate is 68%. " * 30},
    {"section_number": 9, "title": "Monte Carlo", "narrative": "Median lifespan 17 months. " * 20},
]
ticks = [{"month": i, "cash": 100000-i*4000, "revenue": 12000, "costs": 14000} for i in range(1,13)]
mc = {"survival_rate": 0.68, "lifespan_distribution": list(range(8,25)), "kill_vectors": []}

path = asyncio.run(assemble_report(sections, ticks, mc, "run_001", "Acme Corp", "pro"))
print(path)
```
- [ ] No exception
- [ ] Path printed to a `.pdf` file
- [ ] File exists at the printed path

### 2. Open PDF and verify visually
- [ ] Cover page: dark background, title visible, workspace name "Acme Corp"
- [ ] Table of contents: "2. Executive Summary" and "9. Monte Carlo" listed
- [ ] Section 2: content rendered, cash_flow chart visible in section 6 (if included)
- [ ] Page numbers in footer: "Page 1 of N"
- [ ] Header: "Business Simulation Resilience Audit" on every page

### 3. Verify footer branding
- [ ] Footer left shows "Acme Corp"
- [ ] Footer right shows page numbers

### 4. Test free tier (fewer sections)
```python
path = asyncio.run(assemble_report(sections[:1], ticks, mc, "run_002", "TestCo", "free"))
```
- [ ] Smaller file (fewer pages)
- [ ] Only 1 section in ToC

### 5. Run pytest
```bash
cd backend && pytest tests/unit/deep_report/ -v
```
- [ ] All tests pass including new assembler tests

### 6. Check no leftover temp files
- [ ] Temp chart directories are cleaned up after assembly

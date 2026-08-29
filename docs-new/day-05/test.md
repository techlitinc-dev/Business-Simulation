# Day 05 — Test Specification

## Test File
`backend/tests/unit/deep_report/test_assembler.py`

## Test Cases

### 1. `test_assemble_report_returns_pdf_path` — assemble_report returns a path to a file that exists and is >1KB
### 2. `test_assemble_report_file_is_pdf_or_html` — file starts with %PDF or <! (HTML fallback)
### 3. `test_assemble_empty_sections_does_not_crash` — empty sections + empty ticks + empty mc = file still created
### 4. `test_section_to_html_includes_title` — `_section_to_html` output contains section title
### 5. `test_cover_contains_workspace_name` — `_build_cover` output contains workspace name
### 6. `test_toc_has_all_section_titles` — `_build_toc` output contains all section titles
### 7. `test_chart_injected_for_section_6` — cash_flow chart path injected for section 6

## Run Commands
```bash
cd backend && pytest tests/unit/deep_report/test_assembler.py -v
```

## Expected
```
7 passed in <10s
```

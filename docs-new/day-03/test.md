# Day 03 — Test Specification

## Test Files
- `backend/tests/unit/deep_report/test_section_writer.py`
- `backend/tests/unit/deep_report/test_section_linter.py`

---

## Section Writer Tests

### 1. `test_generate_section_mock_provider_returns_narrative`
With `LLM_PROVIDER=mock`, `generate_section()` returns a dict with a non-empty `narrative` key.

### 2. `test_generate_section_includes_section_number`
Return dict has `section_number` matching the input section's number.

### 3. `test_data_only_fallback_always_returns_dict`
`render_data_only_fallback(section, {})` returns a dict with `narrative` and `is_fallback: True`.

### 4. `test_data_only_fallback_includes_data_keys`
Fallback with `{"tick_logs": [...]}` includes "Tick Logs" heading in narrative.

### 5. `test_prompt_loads_generic_when_template_missing`
If prompt template file doesn't exist, falls back to `generic_narrative.md`.

---

## Section Linter Tests

### 6. `test_lint_passes_valid_section`
Narrative with 200 words, no banned phrases, numbers from data pack → `result.passed == True`.

### 7. `test_lint_fails_banned_phrase`
Narrative containing "as an ai" → `result.passed == False`, error mentions "as an ai".

### 8. `test_lint_fails_narrative_too_short`
Narrative with 20 words for a page_budget=2 section → `result.passed == False`.

### 9. `test_lint_fails_narrative_too_long`
Narrative with 3000 words for page_budget=2 → `result.passed == False`.

### 10. `test_lint_flags_hallucinated_number`
Narrative contains "999999" that is not in data pack → `result.passed == False`.

### 11. `test_lint_allows_number_in_data_pack`
Narrative contains "72" and data_pack has `"survival_rate": 0.72` → passes (72 appears in pack str).

### 12. `test_lint_allows_small_integers`
Numbers ≤ 100 (like "24 months") are not checked against data pack → passes.

---

## Run Commands
```bash
cd backend && pytest tests/unit/deep_report/ -v
cd backend && ruff check app/agents/section_writer.py app/services/deep_report/section_linter.py
```

## Expected
```
12 passed in <3s
```

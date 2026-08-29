# Day 17 — Test Specification

## Tests
- Backend: `tests/integration/test_advisory_api.py` — POST returns 202, GET job returns result
- Frontend: build + lint pass, 4 PersonaCards render with correct color borders

## Key Test Cases
1. `test_request_board_review_returns_202` — status=202, job_id starts "adv_"
2. `test_get_board_review_404_for_unknown` — 404
3. `test_persona_card_renders_persona_name` — CFO card has "💼 CFO" heading
4. `test_advisory_panel_shows_button` — "Get Advisory Board Review" button visible
5. `test_advisory_panel_shows_4_cards_after_load` — result loaded → 4 PersonaCards

## Run Commands
```bash
cd backend && pytest tests/integration/test_advisory_api.py -v
cd frontend && npm run build
```
            
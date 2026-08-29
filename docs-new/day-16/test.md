# Day 16 — Test Specification

## Test File
`backend/tests/unit/agents/test_advisory_board.py`

## Test Cases
1. `test_advisory_board_returns_four_reviews` — result["reviews"] has exactly 4 items
2. `test_advisory_board_persona_names_correct` — personas are CFO, CMO, RiskAuditor, Operator
3. `test_advisory_board_summary_has_required_fields` — summary has consensus_verdict, points_of_agreement, overall_risk_level
4. `test_advisory_board_result_serializable` — json.dumps(result) does not raise
5. `test_each_review_has_top_concerns` — every review has at least 1 top_concern
6. `test_summary_agreement_list_non_empty` — points_of_agreement has at least 1 item

## Run Commands
```bash
cd backend && pytest tests/unit/agents/test_advisory_board.py -v
cd backend && ruff check app/agents/advisory_board.py
```

## Expected
```
6 passed in <5s
```

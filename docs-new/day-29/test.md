# Day 29 — Test Specification

## Test File
`backend/tests/unit/collaboration/test_comment_service.py`

## Test Cases
1. `test_add_comment_creates_record` — Comment added to DB with correct body
2. `test_add_comment_with_mentions` — mentions stored in comment.mentions field
3. `test_submit_for_approval_creates_pending` — status="pending" on creation
4. `test_decide_approval_sets_status` — decision="approved" updates status field
5. `test_list_comments_returns_sorted` — comments ordered by created_at
6. `test_comment_thread_renders_comments` — UI shows comment list

## Run Commands
```bash
cd backend && pytest tests/unit/collaboration/ -v
cd frontend && npm run build
```

## Expected
```
5 passed
Build: 0 errors
```

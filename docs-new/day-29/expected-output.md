# Day 29 — Expected Output

## Files Created
```
backend/app/models/comment.py
backend/app/services/collaboration/comment_service.py
backend/app/api/v1/endpoints/comments.py
frontend/src/features/collaboration/CommentThread.tsx
frontend/src/features/collaboration/ApprovalBanner.tsx
backend/tests/unit/collaboration/test_comment_service.py
```

## API
- POST /comments/ → 201 with comment id
- GET /comments/blueprint/{id} → list of comments
- POST /comments/approvals → 201 with approval_id, status="pending"
- POST /comments/approvals/{id}/decide → status="approved"|"rejected"

## UI
- Comment thread: comment list + input box with @mention support
- Approval banner: "Submit for Review" button → "Pending Approval" state → approver sees Approve/Reject buttons
- Decided: green "✅ Approved by <user>" or red "❌ Rejected: <note>"

## Pytest: 5 passed

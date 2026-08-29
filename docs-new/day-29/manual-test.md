# Day 29 — Manual Test Checklist

## Checklist

### 1. Post a comment
```bash
curl -X POST "http://localhost:8000/api/v1/comments/" \
  -H "Authorization: Bearer <token>" -H "X-Workspace-Id: <ws_id>" \
  -H "Content-Type: application/json" \
  -d '{"target_type":"blueprint","target_id":"<bp_id>","body":"This CAC looks high @alice"}'
```
- [ ] 201 response with comment id

### 2. List comments
```bash
curl "http://localhost:8000/api/v1/comments/blueprint/<bp_id>" \
  -H "Authorization: Bearer <token>"
```
- [ ] Returns list with the comment

### 3. Submit for approval
```bash
curl -X POST "http://localhost:8000/api/v1/comments/approvals" \
  -H "Authorization: Bearer <token>" -H "X-Workspace-Id: <ws_id>" \
  -H "Content-Type: application/json" \
  -d '{"target_type":"report","target_id":"<report_id>"}'
```
- [ ] 201 with approval_id, status="pending"

### 4. Approve the record
```bash
curl -X POST "http://localhost:8000/api/v1/comments/approvals/<approval_id>/decide" \
  -H "Authorization: Bearer <approver_token>" \
  -H "Content-Type: application/json" \
  -d '{"decision":"approved","note":"Looks great!"}'
```
- [ ] status="approved", decided_at set

### 5. Comment thread UI
- [ ] Open blueprint page
- [ ] Comment thread visible below blueprint canvas
- [ ] Type comment with @username → post
- [ ] Comment appears in thread

### 6. Build
```bash
cd frontend && npm run build
```
- [ ] 0 errors

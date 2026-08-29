# Day 26 — Manual Test Checklist

## Checklist

### 1. Create and view portfolio
- [ ] POST /portfolios → portfolio_id returned
- [ ] Add 2 workspaces with different resilience scores
- [ ] GET /portfolios/{id}/summary → workspaces sorted highest score first

### 2. Portfolio Dashboard UI
- [ ] Navigate to /portfolio/<id>
- [ ] Companies listed with rank numbers
- [ ] Score bars colored correctly (green/yellow/red)
- [ ] Drift Alert badge visible for workspace with negative delta

### 3. Cohort Rankings anonymize
- [ ] Click "Anonymize" → names replaced with "Company 1", "Company 2"
- [ ] Click "Show Names" → real names restored
- [ ] Rankings order unchanged during toggle

### 4. Remove workspace
- [ ] DELETE /portfolios/{id}/workspaces/{ws_id}
- [ ] Workspace disappears from summary
- [ ] Workspace data (blueprints, runs) still accessible in its own workspace

### 5. Build
```bash
cd frontend && npm run build
```
- [ ] 0 errors

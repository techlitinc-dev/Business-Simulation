# Day 07 — Manual Test Checklist

## Prerequisites
- Full stack running: `docker compose up -d`
- Logged-in as Pro plan user in the browser

## Checklist

### 1. Navigate to a completed simulation run's report page
- [ ] URL: `/simulations/<run_id>/report`
- [ ] "Deep-Dive Report" tab is visible

### 2. Paywall test (free plan)
- [ ] Log in as free plan user
- [ ] Open Deep-Dive Report tab
- [ ] Paywall card appears: "Upgrade to Pro — $49/mo"
- [ ] No generate button visible

### 3. Generate report (pro plan)
- [ ] Log in as Pro plan user
- [ ] Click "Generate Deep-Dive Report"
- [ ] Button disappears, progress section appears

### 4. Observe live progress
- [ ] Progress bar starts filling
- [ ] Section names appear one by one in the list
- [ ] Current section shows animated "Writing section N of M: <Title>"
- [ ] Green checkmarks appear as sections complete

### 5. Download PDF on completion
- [ ] Progress bar reaches 100%
- [ ] "✅ Report ready — 13 sections generated" message appears
- [ ] Click "⬇️ Download PDF"
- [ ] PDF downloads and opens correctly
- [ ] PDF has cover page with workspace name
- [ ] Page numbers visible in footer

### 6. Embedded viewer
- [ ] PDF iframe renders below the download button
- [ ] PDF is scrollable inside the iframe
- [ ] All charts visible

### 7. Frontend build
```bash
cd frontend && npm run build
```
- [ ] 0 errors
- [ ] 0 new lint warnings

### 8. Refresh resilience
- [ ] After download, refresh page
- [ ] No broken state — idle state shows (could improve by persisting job_id, but not required today)

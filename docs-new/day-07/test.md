# Day 07 — Test Specification

## Test Files
`frontend/src/__tests__/deep_report/DeepReportPage.test.tsx`
`frontend/src/__tests__/deep_report/SectionProgressFeed.test.tsx`

## Test Cases

### 1. `DeepReportPage renders paywall for free plan`
Free plan user sees "Upgrade to Pro" button, no generate button.

### 2. `DeepReportPage renders generate button for pro plan`
Pro plan user sees "Generate Deep-Dive Report" button.

### 3. `DeepReportPage calls requestDeepReport on click`
Clicking generate button calls `requestDeepReport` with the correct runId.

### 4. `DeepReportPage shows error message on API failure`
If `requestDeepReport` throws, error message is displayed.

### 5. `DeepReportPage shows progress feed while generating`
After successful enqueue, `SectionProgressFeed` is rendered.

### 6. `DeepReportPage shows download button on complete`
When phase=complete and pdf_url is set, download link is rendered.

### 7. `SectionProgressFeed calculates progress percentage`
With 5 "done" events out of 13 total, shows ~38%.

### 8. `SectionProgressFeed calls onComplete when all sections done`
Fires `onComplete` callback when section === total and status === "done".

## Run Commands
```bash
cd frontend && npm run test -- --run deep_report
cd frontend && npm run build
cd frontend && npm run lint
```

## Expected
```
Build: 0 errors
Lint: 0 errors
Tests: 8 passed
```

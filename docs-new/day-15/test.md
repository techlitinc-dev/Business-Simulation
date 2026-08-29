# Day 15 — Test Specification

## Test Files
`frontend/src/__tests__/actuals/ActualsUploadPage.test.tsx`
`frontend/src/__tests__/actuals/VarianceReportPage.test.tsx`

## Test Cases
1. `ActualsUploadPage shows paste step initially`
2. `ActualsUploadPage parses headers and shows mapping step`
3. `ActualsUploadPage auto-maps known columns`
4. `ActualsUploadPage calls uploadActuals with correct params`
5. `ActualsUploadPage shows success message after upload`
6. `VarianceReportPage shows loading state`
7. `VarianceReportPage renders 3 metric cards on success`
8. `VarianceReportPage shows narrative headline`
9. `VarianceReportPage shows "No variance data" when no actuals`
10. `RollingForecastTimeline renders line chart`

## Run Commands
```bash
cd frontend && npm run build && npm run lint
```

## Expected
```
Build: 0 errors, 0 lint warnings
```

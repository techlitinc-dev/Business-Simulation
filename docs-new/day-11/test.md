# Day 11 — Test Specification

## Test Files
`frontend/src/__tests__/whatif/WhatIfLabPage.test.tsx`
`frontend/src/__tests__/whatif/SweepHeatmap.test.tsx`

## Test Cases
1. `WhatIfLabPage shows paywall for free plan`
2. `WhatIfLabPage shows parameter selector and Run button for pro plan`
3. `WhatIfLabPage calls runSweep and findBreakeven on button click`
4. `WhatIfLabPage shows heatmap after successful sweep`
5. `WhatIfLabPage shows break-even card after sweep`
6. `WhatIfLabPage calls saveVersion with correct params on grid point click`
7. `SweepHeatmap renders correct number of cells`
8. `SweepHeatmap shows correct % labels`
9. `BreakevenCard shows loading state`
10. `BreakevenCard shows threshold value and message`

## Run Commands
```bash
cd frontend && npm run build && npm run lint
```

## Expected
```
Build: 0 errors
Lint: 0 errors
```

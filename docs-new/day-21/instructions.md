# Day 21 — F-05: Benchmark API + Dashboard Gauge Integration

## Feature
F-05: Cohort Benchmarks

## Goal
Expose benchmark endpoints. Embed the percentile badge into the existing dashboard resilience gauge and ReportPage. Add a cohort distribution chart.

---

## Step 1 — Backend API

`backend/app/api/v1/endpoints/benchmark.py`:
```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, get_current_workspace
from app.services.benchmark.aggregator import get_cohort_stats, score_percentile
from app.services.benchmark.schemas import CohortStats, PercentileResult

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("/cohort", response_model=CohortStats | None)
async def get_cohort(
    industry: str | None = Query(None),
    stage: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_cohort_stats(industry, stage, db)


@router.get("/percentile", response_model=PercentileResult)
async def get_percentile(
    score: float = Query(...),
    industry: str | None = Query(None),
    stage: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await score_percentile(score, industry, stage, db)
```

Register: `api_router.include_router(benchmark_router)`

---

## Step 2 — Frontend `frontend/src/features/benchmark/api.ts`

```typescript
import { apiClient } from "@/lib/api";

export interface PercentileResult {
  score: number;
  industry: string | null;
  stage: string | null;
  percentile: number;
  sample_size: number;
  label: string;
}

export interface CohortStats {
  sample_size: number;
  survival_rate_p25: number;
  survival_rate_p50: number;
  survival_rate_p75: number;
  resilience_score_p25: number;
  resilience_score_p50: number;
  resilience_score_p75: number;
  top_kill_vectors: string[];
}

export async function getPercentile(score: number, industry?: string, stage?: string): Promise<PercentileResult> {
  const params = new URLSearchParams({ score: String(score) });
  if (industry) params.set("industry", industry);
  if (stage) params.set("stage", stage);
  const res = await apiClient.get<PercentileResult>(`/benchmarks/percentile?${params}`);
  return res.data;
}

export async function getCohortStats(industry?: string, stage?: string): Promise<CohortStats | null> {
  const params = new URLSearchParams();
  if (industry) params.set("industry", industry);
  if (stage) params.set("stage", stage);
  const res = await apiClient.get<CohortStats | null>(`/benchmarks/cohort?${params}`);
  return res.data;
}
```

---

## Step 3 — `BenchmarkBadge.tsx`

```typescript
// frontend/src/features/benchmark/BenchmarkBadge.tsx
import { useEffect, useState } from "react";
import { getPercentile, PercentileResult } from "./api";

interface Props {
  score: number;
  industry?: string;
  stage?: string;
}

export function BenchmarkBadge({ score, industry, stage }: Props) {
  const [result, setResult] = useState<PercentileResult | null>(null);

  useEffect(() => {
    getPercentile(score, industry, stage).then(setResult).catch(() => {});
  }, [score, industry, stage]);

  if (!result || result.sample_size < 5) return null;

  const color = result.percentile >= 75 ? "text-green-400" :
                result.percentile >= 50 ? "text-blue-400" :
                result.percentile >= 25 ? "text-yellow-400" : "text-red-400";

  return (
    <div className={`text-xs font-medium ${color} mt-1`}>
      📊 {result.label}
    </div>
  );
}
```

---

## Step 4 — `CohortChart.tsx`

```typescript
// frontend/src/features/benchmark/CohortChart.tsx
import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, Cell } from "recharts";
import { getCohortStats, getPercentile, CohortStats } from "./api";

interface Props {
  score: number;
  industry?: string;
  stage?: string;
}

export function CohortChart({ score, industry, stage }: Props) {
  const [stats, setStats] = useState<CohortStats | null>(null);

  useEffect(() => {
    getCohortStats(industry, stage).then(setStats).catch(() => {});
  }, [industry, stage]);

  if (!stats || stats.sample_size < 5) {
    return <p className="text-slate-500 text-xs">Not enough peer data yet (need 5+ runs).</p>;
  }

  const data = [
    { label: "P25", value: stats.resilience_score_p25 },
    { label: "P50", value: stats.resilience_score_p50 },
    { label: "P75", value: stats.resilience_score_p75 },
    { label: "You", value: score },
  ];

  return (
    <div className="space-y-1">
      <p className="text-slate-400 text-xs">Cohort: {stats.sample_size} simulations</p>
      <div className="h-36">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <XAxis dataKey="label" stroke="#94a3b8" tick={{ fontSize: 10 }} />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 10 }} domain={[0, 100]} />
            <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0" }} />
            <ReferenceLine y={50} stroke="#6366f1" strokeDasharray="3 3" />
            <Bar dataKey="value" radius={[3, 3, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={index} fill={entry.label === "You" ? "#3b82f6" : "#334155"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

---

## Step 5 — Add BenchmarkBadge to Dashboard resilience gauge

In `frontend/src/features/dashboard/ResilienceGauge.tsx` (or wherever the score is displayed):

```tsx
import { BenchmarkBadge } from "@/features/benchmark/BenchmarkBadge";

// Below the score display:
<BenchmarkBadge score={resilienceScore} industry={workspace.industry} stage={workspace.stage} />
```

---

## Step 6 — Add CohortChart to ReportPage

In `frontend/src/features/reports/ReportPage.tsx`:

```tsx
import { CohortChart } from "@/features/benchmark/CohortChart";

// In the report sections, add a "Peer Comparison" card:
<CohortChart score={report.resilience_score} industry={workspace.industry} stage={workspace.stage} />
```

---

## Step 7 — Opt-in toggle in workspace settings

In `frontend/src/features/settings/WorkspaceSettingsPage.tsx`:
```tsx
<label className="flex items-center gap-2 text-slate-300 text-sm">
  <input type="checkbox" checked={benchmarkOptIn} onChange={handleToggle} className="rounded" />
  Share anonymized simulation data to improve cohort benchmarks
</label>
```

---

## Integration Tests

`backend/tests/integration/test_benchmark_api.py`:
```python
@pytest.mark.asyncio
async def test_get_percentile_returns_result(auth_headers):
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/benchmarks/percentile?score=64&industry=saas",
                                headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert 0 <= data["percentile"] <= 100

@pytest.mark.asyncio
async def test_get_cohort_returns_none_when_insufficient(auth_headers):
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/benchmarks/cohort?industry=nonexistent", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() is None
```

---

## Verification Commands
```bash
cd backend && pytest tests/integration/test_benchmark_api.py -v
cd frontend && npm run build && npm run lint
```

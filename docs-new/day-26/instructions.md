# Day 26 — F-10: Portfolio Dashboard + Cohort Comparison UI

## Feature
F-10: Portfolio & Cohort Mode

## Goal
Build the portfolio API endpoints and frontend dashboard showing all companies ranked by resilience score with drift badges and cohort ranking.

---

## Step 1 — Portfolio API

`backend/app/api/v1/endpoints/portfolio.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.services.portfolio.portfolio_service import (
    create_portfolio, add_workspace, remove_workspace, get_portfolio_summary
)
from app.services.portfolio.schemas import PortfolioCreate

router = APIRouter(prefix="/portfolios", tags=["portfolio"])


@router.post("/", status_code=201)
async def create(body: PortfolioCreate, db: AsyncSession = Depends(get_db),
                 current_user=Depends(get_current_user)):
    pf = await create_portfolio(body.name, current_user.id, db)
    return {"portfolio_id": pf.id, "name": pf.name}


@router.get("/{portfolio_id}/summary")
async def summary(portfolio_id: str, db: AsyncSession = Depends(get_db),
                  current_user=Depends(get_current_user)):
    result = await get_portfolio_summary(portfolio_id, db)
    if not result:
        raise HTTPException(404, "Portfolio not found")
    return result


@router.post("/{portfolio_id}/workspaces", status_code=201)
async def add_ws(portfolio_id: str, workspace_id: str, label: str = "",
                 db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await add_workspace(portfolio_id, workspace_id, label, db)
    return {"added": workspace_id}


@router.delete("/{portfolio_id}/workspaces/{workspace_id}")
async def remove_ws(portfolio_id: str, workspace_id: str,
                    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    await remove_workspace(portfolio_id, workspace_id, db)
    return {"removed": workspace_id}
```

---

## Step 2 — Frontend `frontend/src/features/portfolio/api.ts`

```typescript
import { apiClient } from "@/lib/api";

export interface WorkspaceSummary {
  workspace_id: string;
  label: string;
  resilience_score: number | null;
  survival_rate: number | null;
  drift_alert: boolean;
  last_run_at: string | null;
}

export interface PortfolioSummary {
  portfolio_id: string;
  name: string;
  member_count: number;
  workspaces: WorkspaceSummary[];
  avg_resilience_score: number | null;
}

export async function getPortfolioSummary(portfolioId: string): Promise<PortfolioSummary> {
  const res = await apiClient.get<PortfolioSummary>(`/portfolios/${portfolioId}/summary`);
  return res.data;
}

export async function addWorkspace(portfolioId: string, workspaceId: string, label: string) {
  await apiClient.post(`/portfolios/${portfolioId}/workspaces`, null, { params: { workspace_id: workspaceId, label } });
}

export async function removeWorkspace(portfolioId: string, workspaceId: string) {
  await apiClient.delete(`/portfolios/${portfolioId}/workspaces/${workspaceId}`);
}
```

---

## Step 3 — `PortfolioDashboard.tsx`

```typescript
// frontend/src/features/portfolio/PortfolioDashboard.tsx
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getPortfolioSummary, PortfolioSummary, WorkspaceSummary } from "./api";

function ScoreBar({ score }: { score: number | null }) {
  if (score === null) return <span className="text-slate-500 text-sm">No runs yet</span>;
  const color = score >= 70 ? "bg-green-500" : score >= 50 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-white text-sm font-medium">{score.toFixed(1)}</span>
    </div>
  );
}

export function PortfolioDashboard({ portfolioId }: { portfolioId: string }) {
  const [data, setData] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPortfolioSummary(portfolioId).then(setData).finally(() => setLoading(false));
  }, [portfolioId]);

  if (loading) return <div className="text-slate-400 animate-pulse">Loading portfolio…</div>;
  if (!data) return <div className="text-slate-400">Portfolio not found.</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-white text-xl font-semibold">{data.name}</h2>
        <span className="text-slate-400 text-sm">{data.member_count} companies · Avg score: {data.avg_resilience_score?.toFixed(1) ?? "—"}</span>
      </div>

      <div className="space-y-2">
        {data.workspaces.map((ws, rank) => (
          <Card key={ws.workspace_id} className="bg-slate-800 border-slate-700">
            <CardContent className="py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-slate-500 text-sm w-6">#{rank + 1}</span>
                <div>
                  <div className="text-white text-sm font-medium">{ws.label}</div>
                  {ws.last_run_at && (
                    <div className="text-slate-500 text-xs">
                      Last run: {new Date(ws.last_run_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-4">
                {ws.drift_alert && (
                  <span className="text-red-400 text-xs font-medium">📉 Drift Alert</span>
                )}
                {ws.survival_rate !== null && (
                  <span className="text-slate-400 text-xs">{(ws.survival_rate * 100).toFixed(0)}% survival</span>
                )}
                <ScoreBar score={ws.resilience_score} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
```

---

## Step 4 — `CohortRankings.tsx`

```typescript
// frontend/src/features/portfolio/CohortRankings.tsx
import { useState } from "react";
import { WorkspaceSummary } from "./api";
import { Button } from "@/components/ui/button";

interface Props { workspaces: WorkspaceSummary[]; }

export function CohortRankings({ workspaces }: Props) {
  const [anonymized, setAnonymized] = useState(false);
  const sorted = [...workspaces].sort((a, b) => (b.resilience_score ?? 0) - (a.resilience_score ?? 0));

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-white font-semibold">Cohort Rankings</h3>
        <Button variant="outline" size="sm" onClick={() => setAnonymized(!anonymized)}
          className="border-slate-600 text-slate-300">
          {anonymized ? "Show Names" : "Anonymize"}
        </Button>
      </div>
      <div className="space-y-1">
        {sorted.map((ws, i) => (
          <div key={ws.workspace_id} className="flex items-center gap-3 text-sm">
            <span className="text-slate-500 w-6">#{i + 1}</span>
            <span className="text-white flex-1">{anonymized ? `Company ${i + 1}` : ws.label}</span>
            <span className="text-blue-400 font-medium">{ws.resilience_score?.toFixed(1) ?? "—"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Step 5 — Route + Navigation

```typescript
// router.tsx
{ path: "/portfolio/:portfolioId", element: <PortfolioPage /> }
```

Add "Portfolio" link in sidebar for Portfolio plan users.

---

## Verification Commands
```bash
cd backend && pytest tests/integration/ -k portfolio
cd frontend && npm run build && npm run lint
```

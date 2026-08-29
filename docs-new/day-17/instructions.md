# Day 17 — F-02: Advisory Board API + UI Panel

## Feature
F-02: AI Advisory Board & Copilot

## Goal
Expose the advisory board as a Celery-backed API endpoint. Build the frontend panel with 4 persona cards, conflict/agreement badges, and a synthesized summary section.

---

## Step 1 — Backend API

`backend/app/api/v1/endpoints/advisory.py`:
```python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, get_current_workspace
from app.agents.advisory_board import run_advisory_board
from app.services.deep_report.data_pack import _fetch_blueprint, _fetch_run, _extract_mc_aggregates, _fetch_tick_logs
import asyncio, uuid, json
import redis as redis_lib
from app.core.config import settings

router = APIRouter(prefix="/advisory", tags=["advisory"])

@router.post("/blueprints/{blueprint_id}/board-review", status_code=202)
async def request_board_review(
    blueprint_id: str,
    run_id: str | None = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    job_id = f"adv_{uuid.uuid4().hex[:12]}"
    background_tasks.add_task(_run_board_review, job_id, blueprint_id, run_id, db)
    return {"job_id": job_id, "status": "queued"}


async def _run_board_review(job_id: str, blueprint_id: str, run_id: str | None, db: AsyncSession):
    r = redis_lib.from_url(settings.REDIS_URL)
    try:
        r.set(f"advisory:{job_id}", json.dumps({"status": "running"}), ex=3600)
        blueprint_payload = await _fetch_blueprint(None, db) or {}
        run_summary = {}
        if run_id:
            run = await _fetch_run(run_id, db)
            mc = _extract_mc_aggregates(run) or {}
            run_summary = {"survival_rate": mc.get("survival_rate", 0), "median_lifespan": mc.get("median_lifespan", 0)}

        result = await run_advisory_board(blueprint_payload, run_summary)
        r.set(f"advisory:{job_id}", json.dumps({"status": "complete", "result": result}), ex=3600)
    except Exception as e:
        r.set(f"advisory:{job_id}", json.dumps({"status": "error", "error": str(e)}), ex=3600)


@router.get("/board-review/{job_id}")
async def get_board_review(job_id: str, current_user=Depends(get_current_user)):
    r = redis_lib.from_url(settings.REDIS_URL)
    raw = r.get(f"advisory:{job_id}")
    if not raw:
        from fastapi import HTTPException
        raise HTTPException(404, "Review job not found")
    return json.loads(raw)
```

---

## Step 2 — Frontend `frontend/src/features/advisory/api.ts`

```typescript
import { apiClient } from "@/lib/api";

export async function requestBoardReview(blueprintId: string, runId?: string) {
  const params = runId ? `?run_id=${runId}` : "";
  const res = await apiClient.post(`/advisory/blueprints/${blueprintId}/board-review${params}`);
  return res.data as { job_id: string; status: string };
}

export async function getBoardReview(jobId: string) {
  const res = await apiClient.get(`/advisory/board-review/${jobId}`);
  return res.data;
}
```

---

## Step 3 — `PersonaCard.tsx`

```typescript
// frontend/src/features/advisory/PersonaCard.tsx
const PERSONA_COLORS: Record<string, string> = {
  CFO: "border-blue-500",
  CMO: "border-green-500",
  RiskAuditor: "border-red-500",
  Operator: "border-amber-500",
};
const PERSONA_ICONS: Record<string, string> = {
  CFO: "💼", CMO: "📈", RiskAuditor: "🛡️", Operator: "⚙️",
};

export function PersonaCard({ review }: { review: any }) {
  const borderColor = PERSONA_COLORS[review.persona] ?? "border-slate-600";
  const icon = PERSONA_ICONS[review.persona] ?? "👤";
  const riskColor = review.confidence_level === "HIGH" ? "text-green-400" : review.confidence_level === "MEDIUM" ? "text-yellow-400" : "text-red-400";

  return (
    <div className={`bg-slate-800 border ${borderColor} rounded-lg p-4 space-y-3`}>
      <div className="flex items-center justify-between">
        <span className="font-semibold text-white">{icon} {review.persona}</span>
        <span className={`text-xs ${riskColor}`}>{review.confidence_level}</span>
      </div>
      <p className="text-slate-300 text-sm italic">"{review.verdict}"</p>
      <div>
        <p className="text-slate-400 text-xs font-semibold uppercase tracking-wide mb-1">Top Concerns</p>
        <ul className="space-y-1">
          {review.top_concerns.map((c: string, i: number) => (
            <li key={i} className="text-red-300 text-xs flex gap-1"><span>⚠️</span>{c}</li>
          ))}
        </ul>
      </div>
      {review.opportunities?.length > 0 && (
        <div>
          <p className="text-slate-400 text-xs font-semibold uppercase tracking-wide mb-1">Opportunities</p>
          <ul className="space-y-1">
            {review.opportunities.map((o: string, i: number) => (
              <li key={i} className="text-green-300 text-xs flex gap-1"><span>✅</span>{o}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

---

## Step 4 — `AdvisoryBoardPanel.tsx`

```typescript
// frontend/src/features/advisory/AdvisoryBoardPanel.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PersonaCard } from "./PersonaCard";
import { requestBoardReview, getBoardReview } from "./api";

interface Props { blueprintId: string; runId?: string; }

export function AdvisoryBoardPanel({ blueprintId, runId }: Props) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  async function handleRequest() {
    setLoading(true);
    try {
      const { job_id } = await requestBoardReview(blueprintId, runId);
      // Poll until complete
      for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 2000));
        const res = await getBoardReview(job_id);
        if (res.status === "complete") { setResult(res.result); break; }
        if (res.status === "error") { throw new Error(res.error); }
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      {!result && (
        <Button onClick={handleRequest} disabled={loading} className="bg-purple-600 hover:bg-purple-700">
          {loading ? "Running Board Review…" : "Get Advisory Board Review"}
        </Button>
      )}

      {result && (
        <>
          {/* 4 Persona Cards */}
          <div className="grid grid-cols-2 gap-4">
            {result.reviews.map((r: any) => <PersonaCard key={r.persona} review={r} />)}
          </div>

          {/* Summary */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader><CardTitle className="text-white">Board Summary</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <p className="text-slate-300 italic">"{result.summary.consensus_verdict}"</p>
              <div>
                <p className="text-slate-400 text-xs uppercase tracking-wide mb-2">Points of Agreement</p>
                {result.summary.points_of_agreement.map((p: string, i: number) => (
                  <div key={i} className="text-green-300 text-sm">🤝 {p}</div>
                ))}
              </div>
              {result.summary.points_of_conflict?.length > 0 && (
                <div>
                  <p className="text-slate-400 text-xs uppercase tracking-wide mb-2">Points of Conflict</p>
                  {result.summary.points_of_conflict.map((p: string, i: number) => (
                    <div key={i} className="text-orange-300 text-sm">⚡ {p}</div>
                  ))}
                </div>
              )}
              <div className="bg-blue-900/30 border border-blue-700 rounded p-3">
                <p className="text-blue-300 text-sm font-semibold">🎯 Top Priority</p>
                <p className="text-white text-sm">{result.summary.top_priority_action}</p>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
```

---

## Verification Commands
```bash
cd backend && pytest tests/integration/ -v -k advisory
cd frontend && npm run build && npm run lint
```

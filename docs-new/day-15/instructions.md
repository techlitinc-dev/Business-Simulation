# Day 15 — F-04: Rolling Forecast UI

## Feature
F-04: Living Blueprint & Plan-vs-Actuals

## Goal
Build the "Plan vs. Actuals" frontend section: CSV upload with column-mapping step, variance report page showing score delta + DeepSeek narrative, and a rolling history chart.

## Prerequisites
- Day 12–14 complete (backend actuals API needed)
- Need to create actuals REST endpoints first (include in this day)

---

## Step 1 — Backend: Actuals API endpoints

Create `backend/app/api/v1/endpoints/actuals.py`:

```python
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, get_current_workspace
from app.services.actuals.importer import import_actuals
from app.services.actuals.schemas import ActualsUploadRequest, ActualsUploadResult
from app.services.actuals.variance import compute_variance
from app.agents.variance_narrator import narrate_variance

router = APIRouter(prefix="/actuals", tags=["actuals"])


@router.post("/upload", response_model=ActualsUploadResult)
async def upload_actuals(
    blueprint_id: str,
    csv_content: str,
    column_mapping: dict = {},
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    req = ActualsUploadRequest(blueprint_id=blueprint_id, csv_content=csv_content,
                                column_mapping=column_mapping)
    return await import_actuals(req, workspace.id, db)


@router.get("/{blueprint_id}/variance")
async def get_variance(
    blueprint_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    delta = await compute_variance(blueprint_id, workspace.id, db)
    narrative = await narrate_variance(delta)
    return {"delta": delta.__dict__, "narrative": narrative.model_dump()}


@router.get("/{blueprint_id}/history")
async def get_actuals_history(
    blueprint_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
):
    from sqlalchemy import select
    from app.models.actuals import ActualsRecord
    result = await db.execute(
        select(ActualsRecord)
        .where(ActualsRecord.blueprint_id == blueprint_id,
               ActualsRecord.workspace_id == workspace.id)
        .order_by(ActualsRecord.month)
    )
    records = result.scalars().all()
    return [{"month": r.month, "period_label": r.period_label, **r.fields} for r in records]
```

Register: `api_router.include_router(actuals_router)`

---

## Step 2 — Frontend: `frontend/src/features/actuals/api.ts`

```typescript
import { apiClient } from "@/lib/api";

export async function uploadActuals(
  blueprintId: string,
  csvContent: string,
  columnMapping: Record<string, string> = {}
) {
  const res = await apiClient.post("/actuals/upload", {
    blueprint_id: blueprintId,
    csv_content: csvContent,
    column_mapping: columnMapping,
  });
  return res.data;
}

export async function getVarianceReport(blueprintId: string) {
  const res = await apiClient.get(`/actuals/${blueprintId}/variance`);
  return res.data;
}

export async function getActualsHistory(blueprintId: string) {
  const res = await apiClient.get(`/actuals/${blueprintId}/history`);
  return res.data as Array<{ month: number; [key: string]: number }>;
}
```

---

## Step 3 — `ActualsUploadPage.tsx`

```typescript
// frontend/src/features/actuals/ActualsUploadPage.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { uploadActuals } from "./api";

const KNOWN_FIELDS = ["month", "revenue", "costs", "cash", "customers", "churn_rate", "cac", "headcount", "mrr"];

interface Props { blueprintId: string; onSuccess: () => void; }

export function ActualsUploadPage({ blueprintId, onSuccess }: Props) {
  const [csv, setCsv] = useState("");
  const [headers, setHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [step, setStep] = useState<"paste" | "map" | "done">("paste");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  function handleParseCsv() {
    const firstLine = csv.split("\n")[0];
    const cols = firstLine.split(",").map(c => c.trim().replace(/^"|"$/g, ""));
    setHeaders(cols);
    const autoMap: Record<string, string> = {};
    cols.forEach(col => {
      const normalized = col.toLowerCase().replace(/\s+/g, "_");
      if (KNOWN_FIELDS.includes(normalized)) autoMap[col] = normalized;
    });
    setMapping(autoMap);
    setStep("map");
  }

  async function handleUpload() {
    try {
      const res = await uploadActuals(blueprintId, csv, mapping);
      setResult(res);
      setStep("done");
      onSuccess();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Upload failed");
    }
  }

  return (
    <div className="space-y-4">
      {step === "paste" && (
        <>
          <p className="text-slate-400 text-sm">Paste your CSV (first row = headers). Required column: <code>month</code>.</p>
          <Textarea
            className="bg-slate-700 border-slate-600 text-white font-mono text-xs h-48"
            placeholder="month,revenue,costs,cash,churn_rate&#10;1,12000,14000,86000,0.05"
            value={csv}
            onChange={e => setCsv(e.target.value)}
          />
          <Button onClick={handleParseCsv} disabled={!csv.trim()}>
            Parse Headers →
          </Button>
        </>
      )}

      {step === "map" && (
        <>
          <p className="text-slate-400 text-sm">Map CSV columns to blueprint fields:</p>
          <div className="space-y-2">
            {headers.map(col => (
              <div key={col} className="flex items-center gap-3">
                <span className="text-white font-mono text-sm w-40">{col}</span>
                <span className="text-slate-400">→</span>
                <select
                  className="bg-slate-700 border border-slate-600 text-white rounded px-2 py-1 text-sm"
                  value={mapping[col] ?? ""}
                  onChange={e => setMapping(prev => ({ ...prev, [col]: e.target.value }))}
                >
                  <option value="">-- skip --</option>
                  {KNOWN_FIELDS.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
            ))}
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <Button onClick={handleUpload} className="bg-blue-600 hover:bg-blue-700">
            Upload Actuals
          </Button>
        </>
      )}

      {step === "done" && result && (
        <div className="text-green-400 space-y-1">
          <p>✅ Upload complete</p>
          <p className="text-slate-300 text-sm">
            {result.records_created} created · {result.records_updated} updated
            {result.validation_warnings?.length > 0 && ` · ${result.validation_warnings.length} warnings`}
          </p>
        </div>
      )}
    </div>
  );
}
```

---

## Step 4 — `VarianceReportPage.tsx`

```typescript
// frontend/src/features/actuals/VarianceReportPage.tsx
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getVarianceReport } from "./api";

interface Props { blueprintId: string; }

export function VarianceReportPage({ blueprintId }: Props) {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getVarianceReport(blueprintId)
      .then(setReport)
      .catch(() => setReport(null))
      .finally(() => setLoading(false));
  }, [blueprintId]);

  if (loading) return <div className="text-slate-400 animate-pulse">Computing variance…</div>;
  if (!report) return <div className="text-slate-400">No variance data available. Import actuals first.</div>;

  const { delta, narrative } = report;
  const scoreColor = delta.score_delta < 0 ? "text-red-400" : "text-green-400";

  return (
    <div className="space-y-4">
      {/* Score delta cards */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Resilience Score", prior: delta.prior_resilience_score, current: delta.new_resilience_score, delta: delta.score_delta, unit: "pts" },
          { label: "Survival Rate", prior: `${(delta.prior_survival_rate*100).toFixed(0)}%`, current: `${(delta.new_survival_rate*100).toFixed(0)}%`, delta: `${(delta.survival_delta*100).toFixed(0)}pp` },
          { label: "Median Runway", prior: `${delta.prior_runway_median}mo`, current: `${delta.new_runway_median}mo`, delta: `${delta.runway_delta}mo` },
        ].map(card => (
          <Card key={card.label} className="bg-slate-800 border-slate-700">
            <CardContent className="py-4">
              <div className="text-slate-400 text-xs">{card.label}</div>
              <div className="text-white text-xl font-bold">{card.current}</div>
              <div className="text-slate-400 text-xs">Was: {card.prior}</div>
              <div className={`text-sm font-semibold ${scoreColor}`}>{String(card.delta)}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Narrative */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader><CardTitle className="text-white text-base">{narrative.headline}</CardTitle></CardHeader>
        <CardContent>
          <p className="text-slate-300 text-sm whitespace-pre-wrap">{narrative.explanation}</p>
          <div className="mt-3 text-slate-400 text-xs">Outlook: {narrative.outlook}</div>
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## Step 5 — `RollingForecastTimeline.tsx`

```typescript
// frontend/src/features/actuals/RollingForecastTimeline.tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

interface Props { history: Array<{ month: number; revenue?: number; cash?: number; churn_rate?: number }>; }

export function RollingForecastTimeline({ history }: Props) {
  if (!history.length) return <div className="text-slate-400 text-sm">No history yet.</div>;
  return (
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={history}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="month" stroke="#94a3b8" tick={{ fontSize: 11 }} />
          <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0" }} />
          <Line type="monotone" dataKey="revenue" stroke="#22c55e" dot={false} name="Revenue" />
          <Line type="monotone" dataKey="cash" stroke="#3b82f6" dot={false} name="Cash" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

## Step 6 — Add route and sidebar entry

```typescript
// router.tsx
{ path: "/blueprints/:blueprintId/actuals", element: <ActualsPage /> }
```

---

## Verification Commands
```bash
cd frontend && npm run build && npm run lint
cd backend && ruff check app/api/v1/endpoints/actuals.py
```

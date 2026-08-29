# Day 07 — F-01: Deep Report UI (Progress Screen + PDF Viewer)

## Feature
F-01: Deep-Dive Report Engine

## Goal
Build the frontend for the deep-dive report: a "Generate Deep-Dive Report" button on the existing ReportPage, a live section-by-section progress screen (WebSocket), and a PDF viewer/download page on completion. Apply tier gating — Free users see a paywall.

## Prerequisites
- Day 06 complete (API endpoints live)
- Existing `features/reports/` with `ReportPage.tsx`
- Existing `lib/ws.ts` WebSocket hook
- Existing billing/paywall components

---

## Step 1 — Create `frontend/src/features/reports/deep_report/api.ts`

```typescript
import { apiClient } from "@/lib/api";

export interface DeepReportJob {
  job_id: string;
  run_id: string;
  status: "queued" | "in_progress" | "completed" | "failed";
  tier: string;
  total_sections: number;
  pdf_url: string | null;
}

export async function requestDeepReport(runId: string): Promise<DeepReportJob> {
  const res = await apiClient.post<DeepReportJob>("/reports/deep-dive", { run_id: runId });
  return res.data;
}

export async function getReportStatus(jobId: string): Promise<DeepReportJob> {
  const res = await apiClient.get<DeepReportJob>(`/reports/deep-dive/${jobId}/status`);
  return res.data;
}

export function getDownloadUrl(jobId: string): string {
  return `/api/v1/reports/deep-dive/${jobId}/download`;
}
```

---

## Step 2 — Create `SectionProgressFeed.tsx`

```typescript
// frontend/src/features/reports/deep_report/SectionProgressFeed.tsx
import { useEffect, useState } from "react";
import { useWebSocket } from "@/lib/ws";

interface ProgressEvent {
  job_id: string;
  section: number;
  total: number;
  status: "writing" | "done" | "error";
  section_title: string;
}

interface Props {
  jobId: string;
  totalSections: number;
  onComplete: () => void;
}

export function SectionProgressFeed({ jobId, totalSections, onComplete }: Props) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [current, setCurrent] = useState<ProgressEvent | null>(null);

  const { lastMessage } = useWebSocket(`/ws/reports/${jobId}`);

  useEffect(() => {
    if (!lastMessage) return;
    try {
      const evt: ProgressEvent = JSON.parse(lastMessage);
      setCurrent(evt);
      setEvents(prev => {
        const exists = prev.find(e => e.section === evt.section && e.status === evt.status);
        return exists ? prev : [...prev, evt];
      });
      if (evt.status === "done" && evt.section === evt.total) {
        setTimeout(onComplete, 800);
      }
    } catch {}
  }, [lastMessage]);

  const doneCount = events.filter(e => e.status === "done").length;
  const pct = totalSections > 0 ? Math.round((doneCount / totalSections) * 100) : 0;

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm text-slate-400">
          <span>Writing report...</span>
          <span>{pct}%</span>
        </div>
        <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-500 rounded-full"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Current section */}
      {current && (
        <p className="text-slate-300 text-sm animate-pulse">
          {current.status === "writing" ? "✍️" : "✅"} Writing section {current.section} of {current.total}:{" "}
          <span className="text-white font-medium">{current.section_title}</span>
        </p>
      )}

      {/* Section list */}
      <div className="max-h-64 overflow-y-auto space-y-1">
        {events.map((evt, i) => (
          <div key={i} className={`flex items-center gap-2 text-sm ${
            evt.status === "done" ? "text-green-400" : "text-blue-400 animate-pulse"
          }`}>
            <span>{evt.status === "done" ? "✅" : "⏳"}</span>
            <span>{evt.section}. {evt.section_title}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Step 3 — Create `DeepReportPage.tsx`

```typescript
// frontend/src/features/reports/deep_report/DeepReportPage.tsx
import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SectionProgressFeed } from "./SectionProgressFeed";
import { requestDeepReport, getReportStatus, getDownloadUrl, DeepReportJob } from "./api";
import { useCurrentPlan } from "@/features/billing/hooks";

type Phase = "idle" | "generating" | "complete";

export function DeepReportPage({ runId }: { runId: string }) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [job, setJob] = useState<DeepReportJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const plan = useCurrentPlan();
  const isFree = plan === "free";

  async function handleGenerate() {
    if (isFree) return;
    try {
      setPhase("generating");
      setError(null);
      const newJob = await requestDeepReport(runId);
      setJob(newJob);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to start report generation");
      setPhase("idle");
    }
  }

  async function handleComplete() {
    if (!job) return;
    const updated = await getReportStatus(job.job_id);
    setJob(updated);
    setPhase("complete");
  }

  if (isFree) {
    return (
      <Card className="border-dashed border-slate-600 bg-slate-800/40">
        <CardContent className="py-12 text-center space-y-4">
          <div className="text-4xl">📊</div>
          <h3 className="text-xl font-semibold text-white">Deep-Dive Report</h3>
          <p className="text-slate-400 max-w-md mx-auto">
            Generate a board-grade 70-page simulation audit with investor-grade financials,
            kill-vector analysis, and prescriptive recommendations.
          </p>
          <Button variant="default" className="bg-blue-600 hover:bg-blue-700">
            Upgrade to Pro — $49/mo
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Deep-Dive Simulation Audit</CardTitle>
          <p className="text-slate-400 text-sm">
            AI-generated board-grade report grounded in your simulation data.
            {job && ` ${job.total_sections} sections · ${job.tier.toUpperCase()} tier`}
          </p>
        </CardHeader>
        <CardContent>
          {phase === "idle" && (
            <Button
              onClick={handleGenerate}
              className="bg-blue-600 hover:bg-blue-700"
              disabled={!!error}
            >
              Generate Deep-Dive Report
            </Button>
          )}
          {error && <p className="text-red-400 text-sm mt-2">{error}</p>}

          {phase === "generating" && job && (
            <SectionProgressFeed
              jobId={job.job_id}
              totalSections={job.total_sections}
              onComplete={handleComplete}
            />
          )}

          {phase === "complete" && job?.pdf_url && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-green-400 font-medium">
                ✅ Report ready — {job.total_sections} sections generated
              </div>
              <div className="flex gap-3">
                <a
                  href={getDownloadUrl(job.job_id)}
                  download
                  className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                >
                  ⬇️ Download PDF
                </a>
              </div>
              <ReportViewer pdfUrl={getDownloadUrl(job.job_id)} />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## Step 4 — Create `ReportViewer.tsx`

```typescript
// frontend/src/features/reports/deep_report/ReportViewer.tsx
interface Props { pdfUrl: string; }

export function ReportViewer({ pdfUrl }: Props) {
  return (
    <div className="rounded-lg overflow-hidden border border-slate-700" style={{ height: "70vh" }}>
      <iframe
        src={pdfUrl}
        className="w-full h-full"
        title="Deep-Dive Report"
      />
    </div>
  );
}
```

---

## Step 5 — Add `DeepReportPage` tab to existing `ReportPage.tsx`

In the existing `ReportPage.tsx`, add a new tab:

```tsx
import { DeepReportPage } from "./deep_report/DeepReportPage";

// In the Tabs component, add:
<TabsTrigger value="deep-dive">Deep-Dive Report</TabsTrigger>

// In TabsContent:
<TabsContent value="deep-dive">
  <DeepReportPage runId={runId} />
</TabsContent>
```

---

## Step 6 — Extend WebSocket hook for report channel

The existing `lib/ws.ts` should already support arbitrary channels. If not, ensure the hook accepts a channel path override:

```typescript
// In lib/ws.ts: ensure useWebSocket("/ws/reports/:jobId") works
// The backend needs a matching WebSocket route that forwards deep_report:jobId Redis channel
```

In `backend/app/api/v1/endpoints/ws.py`, add a route for report progress:

```python
@router.websocket("/ws/reports/{job_id}")
async def report_ws(websocket: WebSocket, job_id: str, token: str = Query(...)):
    # Authenticate, subscribe to Redis channel deep_report:{job_id}, forward messages
    ...
```

---

## Verification Commands

```bash
cd frontend && npm run build
cd frontend && npm run lint
```

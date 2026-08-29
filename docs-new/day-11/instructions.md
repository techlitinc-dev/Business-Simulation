# Day 11 — F-06: What-If Lab UI

## Feature
F-06: What-If Lab & Sensitivity Sweeps

## Goal
Build the "What-If Lab" frontend page: parameter picker, range slider, live heatmap/survival-line chart, break-even card, and "Save as Blueprint Version" button. Pro+ gated.

## Prerequisites
- Day 10 complete (API endpoints live)
- Existing `features/blueprint/` for blueprint selector
- Recharts available

---

## Step 1 — Create `frontend/src/features/whatif/api.ts`

```typescript
import { apiClient } from "@/lib/api";

export interface SweepGridPoint {
  param_value: number;
  survival_rate: number;
  median_runway: number;
  p25_runway: number;
  p75_runway: number;
}

export interface SweepResult {
  blueprint_id: string;
  param: string;
  grid: SweepGridPoint[];
}

export interface BreakevenResult {
  blueprint_id: string;
  param: string;
  breakeven_value: number;
  survival_at_breakeven: number;
  message: string;
}

export async function runSweep(
  blueprintId: string,
  param: string,
  minValue: number,
  maxValue: number,
  steps: number = 8
): Promise<SweepResult> {
  const res = await apiClient.post<SweepResult>("/whatif/sweep", {
    blueprint_id: blueprintId,
    param,
    min_value: minValue,
    max_value: maxValue,
    steps,
    mc_runs: 20,
  });
  return res.data;
}

export async function findBreakeven(
  blueprintId: string,
  param: string,
  searchMin: number,
  searchMax: number
): Promise<BreakevenResult> {
  const res = await apiClient.post<BreakevenResult>("/whatif/breakeven", {
    blueprint_id: blueprintId,
    param,
    search_min: searchMin,
    search_max: searchMax,
  });
  return res.data;
}

export async function saveVersion(
  blueprintId: string,
  param: string,
  value: number,
  label: string
): Promise<{ blueprint_version_id: string; label: string }> {
  const res = await apiClient.post("/whatif/save-version", {
    blueprint_id: blueprintId,
    param,
    value,
    version_label: label,
  });
  return res.data;
}
```

---

## Step 2 — Create `SweepHeatmap.tsx`

```typescript
// frontend/src/features/whatif/SweepHeatmap.tsx
import { SweepGridPoint } from "./api";

interface Props { grid: SweepGridPoint[]; param: string; }

function getColor(rate: number) {
  if (rate >= 0.8) return "#22c55e";
  if (rate >= 0.6) return "#84cc16";
  if (rate >= 0.4) return "#eab308";
  if (rate >= 0.2) return "#f97316";
  return "#ef4444";
}

export function SweepHeatmap({ grid, param }: Props) {
  return (
    <div className="space-y-2">
      <p className="text-slate-400 text-sm">
        Survival Rate vs <span className="text-white font-mono">{param}</span>
      </p>
      <div className="flex gap-1 overflow-x-auto">
        {grid.map((pt, i) => (
          <div key={i} className="flex flex-col items-center min-w-[60px]">
            <div
              className="w-full h-12 rounded flex items-center justify-center text-sm font-bold text-black"
              style={{ backgroundColor: getColor(pt.survival_rate) }}
            >
              {(pt.survival_rate * 100).toFixed(0)}%
            </div>
            <span className="text-xs text-slate-400 mt-1">
              {pt.param_value.toFixed(3)}
            </span>
          </div>
        ))}
      </div>
      {/* Legend */}
      <div className="flex gap-4 text-xs text-slate-400">
        <span><span className="inline-block w-3 h-3 bg-green-500 rounded-sm mr-1" />≥80%</span>
        <span><span className="inline-block w-3 h-3 bg-yellow-400 rounded-sm mr-1" />40–60%</span>
        <span><span className="inline-block w-3 h-3 bg-red-500 rounded-sm mr-1" />&lt;20%</span>
      </div>
    </div>
  );
}
```

---

## Step 3 — Create `BreakevenCard.tsx`

```typescript
// frontend/src/features/whatif/BreakevenCard.tsx
import { BreakevenResult } from "./api";
import { Card, CardContent } from "@/components/ui/card";

interface Props {
  result: BreakevenResult | null;
  loading: boolean;
}

export function BreakevenCard({ result, loading }: Props) {
  if (loading) return <div className="text-slate-400 animate-pulse">Calculating break-even…</div>;
  if (!result) return null;
  return (
    <Card className="bg-amber-950/30 border-amber-700">
      <CardContent className="py-4 space-y-1">
        <div className="text-amber-400 font-semibold text-sm">⚠️ Break-Even Threshold</div>
        <div className="text-white text-lg font-bold">
          {result.param.replace(/_/g, " ")} = {result.breakeven_value.toFixed(4)}
        </div>
        <p className="text-slate-300 text-sm">{result.message}</p>
        <div className="text-slate-400 text-xs">
          Survival at breakeven: {(result.survival_at_breakeven * 100).toFixed(1)}%
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## Step 4 — Create `WhatIfLabPage.tsx`

```typescript
// frontend/src/features/whatif/WhatIfLabPage.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SweepHeatmap } from "./SweepHeatmap";
import { BreakevenCard } from "./BreakevenCard";
import { runSweep, findBreakeven, saveVersion, SweepResult, BreakevenResult } from "./api";
import { useCurrentPlan } from "@/features/billing/hooks";

const PARAMS = [
  { key: "monthly_churn", label: "Monthly Churn", min: 0.01, max: 0.20, step: 0.01 },
  { key: "cac", label: "Customer Acquisition Cost", min: 100, max: 5000, step: 100 },
  { key: "price", label: "Monthly Price", min: 10, max: 500, step: 10 },
  { key: "fixed_monthly_costs", label: "Fixed Monthly Costs", min: 1000, max: 50000, step: 500 },
];

interface Props { blueprintId: string; }

export function WhatIfLabPage({ blueprintId }: Props) {
  const plan = useCurrentPlan();
  const [param, setParam] = useState(PARAMS[0]);
  const [range, setRange] = useState<[number, number]>([param.min, param.max]);
  const [sweepResult, setSweepResult] = useState<SweepResult | null>(null);
  const [breakevenResult, setBreakevenResult] = useState<BreakevenResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  if (plan === "free") {
    return (
      <Card className="border-dashed border-slate-600 bg-slate-800/40">
        <CardContent className="py-12 text-center space-y-3">
          <div className="text-4xl">🔬</div>
          <h3 className="text-xl font-semibold text-white">What-If Lab</h3>
          <p className="text-slate-400">Run sensitivity sweeps and find break-even thresholds. Pro+ required.</p>
          <Button className="bg-blue-600 hover:bg-blue-700">Upgrade to Pro</Button>
        </CardContent>
      </Card>
    );
  }

  async function handleRun() {
    setLoading(true);
    setSaveMsg(null);
    try {
      const [sweep, be] = await Promise.all([
        runSweep(blueprintId, param.key, range[0], range[1]),
        findBreakeven(blueprintId, param.key, range[0], range[1]),
      ]);
      setSweepResult(sweep);
      setBreakevenResult(be);
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveVersion(value: number) {
    const label = `${param.label} = ${value.toFixed(4)} (What-If)`;
    const res = await saveVersion(blueprintId, param.key, value, label);
    setSaveMsg(`✅ Saved as version: ${res.blueprint_version_id}`);
  }

  return (
    <div className="space-y-6">
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">🔬 What-If Lab</CardTitle>
          <p className="text-slate-400 text-sm">Sweep a parameter range. No LLM — pure engine, near-instant.</p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Parameter selector */}
          <div className="space-y-2">
            <Label className="text-slate-300">Parameter</Label>
            <Select value={param.key} onValueChange={k => {
              const p = PARAMS.find(x => x.key === k)!;
              setParam(p);
              setRange([p.min, p.max]);
            }}>
              <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                {PARAMS.map(p => <SelectItem key={p.key} value={p.key}>{p.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {/* Range display */}
          <div className="space-y-2">
            <Label className="text-slate-300">
              Range: <span className="text-white font-mono">{range[0]}</span> → <span className="text-white font-mono">{range[1]}</span>
            </Label>
          </div>

          <Button onClick={handleRun} disabled={loading} className="bg-blue-600 hover:bg-blue-700">
            {loading ? "Running sweeps…" : "Run Sweep"}
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {sweepResult && (
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="py-6 space-y-4">
            <SweepHeatmap grid={sweepResult.grid} param={sweepResult.param} />
            <BreakevenCard result={breakevenResult} loading={false} />

            {/* Save version buttons */}
            <div className="space-y-2">
              <p className="text-slate-400 text-sm">Save a grid point as a new blueprint version:</p>
              <div className="flex flex-wrap gap-2">
                {sweepResult.grid.map((pt, i) => (
                  <Button key={i} variant="outline" size="sm"
                    className="border-slate-600 text-slate-300 hover:bg-slate-700"
                    onClick={() => handleSaveVersion(pt.param_value)}>
                    {pt.param_value.toFixed(3)} ({(pt.survival_rate * 100).toFixed(0)}%)
                  </Button>
                ))}
              </div>
              {saveMsg && <p className="text-green-400 text-sm">{saveMsg}</p>}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

---

## Step 5 — Add route in `router.tsx`

```typescript
{ path: "/blueprints/:blueprintId/whatif", element: <WhatIfLabPage blueprintId={...} /> }
```

Also add "What-If Lab" button to the Blueprint detail page.

---

## Verification Commands
```bash
cd frontend && npm run build
cd frontend && npm run lint
```

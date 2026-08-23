import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useWorkspaceStore } from '@/stores/workspace-store'
import { BreakevenCard } from './BreakevenCard'
import { SweepHeatmap } from './SweepHeatmap'
import { findBreakeven, runSweep, saveVersion } from './api'
import type { BreakevenResult, SweepResult } from './api'

// Dot-notation paths into the Format A blueprint payload (see whatif sweep).
const PARAMS = [
  {
    key: 'revenue_engine.streams.0.churn_monthly',
    label: 'Monthly Churn',
    min: 0.01,
    max: 0.2,
  },
  {
    key: 'revenue_engine.streams.0.cac',
    label: 'Customer Acquisition Cost',
    min: 100,
    max: 5000,
  },
  {
    key: 'revenue_engine.streams.0.price_point',
    label: 'Monthly Price',
    min: 10,
    max: 500,
  },
  {
    key: 'cost_structure.fixed_monthly',
    label: 'Fixed Monthly Costs',
    min: 1000,
    max: 50000,
  },
]

interface Props {
  blueprintId: string
}

export function WhatIfLabPage({ blueprintId }: Props) {
  const workspaces = useWorkspaceStore((s) => s.workspaces)
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId)
  const planTier =
    workspaces.find((w) => w.id === activeWorkspaceId)?.plan_tier ?? 'free'
  const [param, setParam] = useState(PARAMS[0])
  const [range, setRange] = useState<[number, number]>([param.min, param.max])
  const [sweepResult, setSweepResult] = useState<SweepResult | null>(null)
  const [breakevenResult, setBreakevenResult] = useState<BreakevenResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)

  if (planTier === 'free') {
    return (
      <Card className="border-dashed border-slate-600 bg-slate-800/40">
        <CardContent className="py-12 text-center space-y-3">
          <div className="text-4xl">🔬</div>
          <h3 className="text-xl font-semibold text-white">What-If Lab</h3>
          <p className="text-slate-400">
            Run sensitivity sweeps and find break-even thresholds. Pro+ required.
          </p>
          <Button className="bg-blue-600 hover:bg-blue-700">Upgrade to Pro</Button>
        </CardContent>
      </Card>
    )
  }

  async function handleRun() {
    setLoading(true)
    setSaveMsg(null)
    try {
      const [sweep, be] = await Promise.all([
        runSweep(blueprintId, param.key, range[0], range[1]),
        findBreakeven(blueprintId, param.key, range[0], range[1]),
      ])
      setSweepResult(sweep)
      setBreakevenResult(be)
    } finally {
      setLoading(false)
    }
  }

  async function handleSaveVersion(value: number) {
    const label = `${param.label} = ${value.toFixed(4)} (What-If)`
    const res = await saveVersion(blueprintId, param.key, value, label)
    setSaveMsg(`✅ Saved as version: ${res.version}`)
  }

  return (
    <div className="space-y-6">
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">🔬 What-If Lab</CardTitle>
          <p className="text-slate-400 text-sm">
            Sweep a parameter range. No LLM — pure engine, near-instant.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Parameter selector */}
          <div className="space-y-2">
            <Label className="text-slate-300">Parameter</Label>
            <Select
              value={param.key}
              onValueChange={(key) => {
                const next = PARAMS.find((p) => p.key === key) ?? PARAMS[0]
                setParam(next)
                setRange([next.min, next.max])
              }}
            >
              <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                {PARAMS.map((p) => (
                  <SelectItem key={p.key} value={p.key}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Range display */}
          <div className="space-y-2">
            <Label className="text-slate-300">
              Range:{' '}
              <span className="text-white font-mono">{range[0]}</span> →{' '}
              <span className="text-white font-mono">{range[1]}</span>
            </Label>
          </div>

          <Button
            onClick={handleRun}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {loading ? 'Running sweeps…' : 'Run Sweep'}
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
              <p className="text-slate-400 text-sm">
                Save a grid point as a new blueprint version:
              </p>
              <div className="flex flex-wrap gap-2">
                {sweepResult.grid.map((pt, i) => (
                  <Button
                    key={i}
                    variant="outline"
                    size="sm"
                    className="border-slate-600 text-slate-300 hover:bg-slate-700"
                    onClick={() => handleSaveVersion(pt.param_value)}
                  >
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
  )
}

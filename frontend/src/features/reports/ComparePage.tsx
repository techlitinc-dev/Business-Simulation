import { useState } from 'react'
import { ArrowRight, GitCompareArrows } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCompare } from '@/features/reports/hooks'
import type { KillVectorChange, RunSummary } from '@/features/reports/hooks'

interface ComparePageProps {
  runs: { id: string; label: string }[]
}

const VERDICT_STYLES: Record<string, string> = {
  improved: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
  regressed: 'bg-red-500/15 text-red-300 border-red-500/40',
  unchanged: 'bg-slate-500/15 text-slate-300 border-slate-500/40',
}

function RunCard({ title, run }: { title: string; run?: RunSummary }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {!run ? (
          <p className="text-sm text-muted-foreground">Select a run…</p>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Survival</span>
              <span className="text-xl font-semibold">
                {Math.round(run.survival_rate * 100)}%
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Median lifespan</span>
              <span className="text-sm font-medium">{run.median_lifespan_months} mo</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Resilience</span>
              <span className="text-sm font-medium">{run.resilience_score}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Top kill vector</span>
              <span className="text-sm font-medium">{run.top_kill_vector}</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Blueprint v{run.blueprint_version} · {run.run_id}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}

export default function ComparePage({ runs }: ComparePageProps) {
  const [runA, setRunA] = useState<string>('')
  const [runB, setRunB] = useState<string>('')
  const { data, isFetching } = useCompare(runA, runB)

  const handleCompare = () => {
    if (!runA || !runB) return
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <GitCompareArrows className="h-6 w-6" /> Compare Runs
        </h1>
        <p className="text-sm text-muted-foreground">
          Blueprint V1 vs V2 — did the optimization help?
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-end gap-4 p-4">
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">Run A (baseline)</label>
            <Select value={runA} onValueChange={setRunA}>
              <SelectTrigger className="w-64">
                <SelectValue placeholder="Pick a run" />
              </SelectTrigger>
              <SelectContent>
                {runs.map((r) => (
                  <SelectItem key={r.id} value={r.id}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <ArrowRight className="mb-2 h-4 w-4 text-muted-foreground" />
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">Run B (optimized)</label>
            <Select value={runB} onValueChange={setRunB}>
              <SelectTrigger className="w-64">
                <SelectValue placeholder="Pick a run" />
              </SelectTrigger>
              <SelectContent>
                {runs.map((r) => (
                  <SelectItem key={r.id} value={r.id}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={handleCompare} disabled={!runA || !runB || isFetching}>
            Compare
          </Button>
        </CardContent>
      </Card>

      {data && (
        <>
          <div className="flex items-center justify-center">
            <Badge className={VERDICT_STYLES[data.verdict] ?? ''}>
              {data.verdict === 'improved'
                ? `V2 improves survival by +${data.deltas.survival_rate_pp}pp`
                : data.verdict === 'regressed'
                  ? `V2 regresses survival by ${data.deltas.survival_rate_pp}pp`
                  : 'No meaningful change'}
            </Badge>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <RunCard title="Run A — baseline" run={data.a} />
            <RunCard title="Run B — optimized" run={data.b} />
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Kill vector changes</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th className="pb-2 pr-4">Cause</th>
                    <th className="pb-2 pr-4">Run A %</th>
                    <th className="pb-2 pr-4">Run B %</th>
                    <th className="pb-2">Δpp</th>
                  </tr>
                </thead>
                <tbody>
                  {data.kill_vector_changes.map((kv: KillVectorChange) => (
                    <tr key={kv.cause} className="border-t border-border">
                      <td className="py-2 pr-4">{kv.cause}</td>
                      <td className="py-2 pr-4">{kv.pct_a}%</td>
                      <td className="py-2 pr-4">{kv.pct_b}%</td>
                      <td
                        className={`py-2 font-medium ${
                          kv.delta_pp <= 0 ? 'text-emerald-400' : 'text-red-400'
                        }`}
                      >
                        {kv.delta_pp >= 0 ? '+' : ''}
                        {kv.delta_pp}pp
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

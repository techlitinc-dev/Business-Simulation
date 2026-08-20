import { Link } from 'react-router-dom'
import { FlaskConical, Plus } from 'lucide-react'

import BurnChart from '@/components/charts/BurnChart'
import CashCurve from '@/components/charts/CashCurve'
import { ResilienceGauge } from '@/components/charts/ResilienceGauge'
import { BenchmarkBadge } from '@/features/benchmark/BenchmarkBadge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import KpiCard from './KpiCard'
import RecentRunsTable from './RecentRunsTable'
import { useRecentRuns, useReport, useTicks } from './hooks'

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}k`
  return `$${value.toFixed(0)}`
}

function deltaPercent(prev: number, curr: number): number | null {
  if (!Number.isFinite(prev) || !Number.isFinite(curr) || prev === 0) return null
  return ((curr - prev) / Math.abs(prev)) * 100
}

export default function DashboardPage() {
  const { data: runs = [], isLoading, isError } = useRecentRuns()

  const latestCompleted = runs.find((r) => r.status === 'completed') ?? null
  // Fall back to the most recent run (even dead/pending) so the dashboard
  // never shows a blank "No runs yet" when nothing has completed yet.
  const latestRun = latestCompleted ?? runs[0] ?? null
  const { data: ticks = [] } = useTicks(latestRun?.id)
  const { data: report } = useReport(latestRun?.id)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-7 w-48" />
            <Skeleton className="h-4 w-64" />
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-9 w-36" />
            <Skeleton className="h-9 w-36" />
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="mt-3 h-8 w-28" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-[1fr_1.5fr]">
          <Card>
            <CardHeader>
              <Skeleton className="h-5 w-36" />
            </CardHeader>
            <CardContent className="flex justify-center py-8">
              <Skeleton className="h-32 w-32 rounded-full" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <Skeleton className="h-5 w-36" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-72 w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (isError) {
    return <p className="text-sm text-destructive">Could not load dashboard data.</p>
  }

  if (runs.length === 0 || !latestRun) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Your business simulation overview
          </p>
        </div>
        <EmptyState
          icon={FlaskConical}
          title="No runs yet"
          description="Create your first blueprint, then run a baseline to see your numbers here."
          ctaLabel="Create your first blueprint"
          onCtaClick={() => {
            window.location.href = '/app/blueprints/new'
          }}
        />
      </div>
    )
  }

  const last = ticks[ticks.length - 1]
  const prev = ticks[ticks.length - 2]
  const latest = last?.kpis ?? {}
  const prevKpis = prev?.kpis ?? {}

  const kpis = [
    {
      label: 'Cash balance',
      value: formatCurrency(latest.cash_balance ?? 0),
      delta: prevKpis.cash_balance
        ? deltaPercent(prevKpis.cash_balance ?? 0, latest.cash_balance ?? 0)
        : null,
      sparkline: ticks.map((t) => t.kpis.cash_balance ?? 0),
    },
    {
      label: 'MRR',
      value: formatCurrency(latest.mrr ?? 0),
      delta: prevKpis.mrr
        ? deltaPercent(prevKpis.mrr ?? 0, latest.mrr ?? 0)
        : null,
      sparkline: ticks.map((t) => t.kpis.mrr ?? 0),
    },
    {
      label: 'Burn rate',
      value: formatCurrency(latest.burn_rate ?? 0),
      delta: prevKpis.burn_rate
        ? deltaPercent(prevKpis.burn_rate ?? 0, latest.burn_rate ?? 0)
        : null,
      sparkline: ticks.map((t) => t.kpis.burn_rate ?? 0),
    },
    {
      label: 'Runway',
      value: `${Math.round(latest.runway_months ?? 0)} mo`,
      delta: null,
      sparkline: ticks.map((t) => t.kpis.runway_months ?? 0),
    },
  ]

  const resilienceScore = report?.content_json.resilience_score ?? 0

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight">
            Dashboard
          </h1>
          <p className="text-sm text-muted-foreground">
            {latestRun
              ? `Latest run: ${latestRun.mode.replace('_', ' ')} · seed ${latestRun.seed} · ${latestRun.status}`
              : 'Your business simulation overview'}
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <Link to="/app/blueprints/new">
              <Plus className="h-4 w-4" /> New Blueprint
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/app/simulations">Run Baseline</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/app/simulations?mode=monte_carlo">Monte Carlo</Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi, i) => (
          <KpiCard
            key={kpi.label}
            label={kpi.label}
            value={kpi.value}
            deltaPercent={kpi.delta}
            sparkline={kpi.sparkline}
            index={i}
          />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.5fr]">
        <Card className="panel">
          <CardHeader>
            <CardTitle className="text-sm">Resilience score</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center py-6 flex-col items-center">
            <ResilienceGauge score={resilienceScore} />
            <BenchmarkBadge score={resilienceScore} />
          </CardContent>
        </Card>
        <Card className="panel">
          <CardHeader>
            <CardTitle className="text-sm">Cash curve</CardTitle>
          </CardHeader>
          <CardContent>
            {ticks.length === 0 ? (
              <Skeleton className="h-72 w-full" />
            ) : (
              <CashCurve ticks={ticks} />
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="panel">
        <CardHeader>
          <CardTitle className="text-sm">MRR vs burn</CardTitle>
        </CardHeader>
        <CardContent>
          {ticks.length === 0 ? (
            <Skeleton className="h-72 w-full" />
          ) : (
            <BurnChart ticks={ticks} />
          )}
        </CardContent>
      </Card>

      <div>
        <h2 className="mb-3 text-sm font-medium text-muted-foreground">
          Recent runs
        </h2>
        <RecentRunsTable runs={runs} />
      </div>
    </div>
  )
}

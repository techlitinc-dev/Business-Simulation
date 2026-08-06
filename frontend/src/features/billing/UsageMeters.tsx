import { useUsage } from './hooks'
import { Skeleton } from '@/components/ui/skeleton'

function MeterRow({
  label,
  used,
  limit,
}: {
  label: string
  used: number
  limit: number
}) {
  const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0
  const over = limit > 0 && used >= limit

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className={over ? 'font-medium text-destructive' : 'tabular-nums'}>
          {limit === -1 ? `${used} / unlimited` : `${used} / ${limit}`}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className={over ? 'h-full bg-destructive' : 'h-full bg-primary'}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export default function UsageMeters() {
  const { data, isLoading } = useUsage()

  if (isLoading || !data) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{data.tier} plan</span>
        <span className="text-xs text-muted-foreground">{data.period}</span>
      </div>
      <MeterRow
        label="Runs this month"
        used={data.usage.runs_used}
        limit={data.limits.runs_per_month}
      />
      <MeterRow
        label="Monte Carlo runs"
        used={data.usage.mc_ticks_used}
        limit={data.limits.monte_carlo_runs_per_batch}
      />
      <MeterRow
        label="LLM tokens"
        used={data.usage.llm_tokens_used}
        limit={data.limits.llm_tokens_per_month}
      />
    </div>
  )
}

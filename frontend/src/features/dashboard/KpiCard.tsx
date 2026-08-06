import { TrendingDown, TrendingUp } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface KpiCardProps {
  label: string
  value: string
  deltaPercent: number | null
  sparkline?: number[]
}

function Sparkline({ points }: { points: number[] }) {
  if (points.length < 2) return null
  const w = 120
  const h = 36
  const min = Math.min(...points)
  const max = Math.max(...points)
  const range = max - min || 1
  const step = w / (points.length - 1)
  const path = points
    .map((p, i) => {
      const x = i * step
      const y = h - ((p - min) / range) * (h - 4) - 2
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
  const positive = points[points.length - 1] >= points[0]
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="mt-2 w-full">
      <path
        d={path}
        fill="none"
        stroke={positive ? 'var(--success)' : 'var(--destructive)'}
        strokeWidth={1.5}
      />
    </svg>
  )
}

export default function KpiCard({ label, value, deltaPercent, sparkline }: KpiCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium text-muted-foreground">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-end justify-between">
          <div>
            <p className="text-2xl font-semibold tabular-nums">{value}</p>
            {deltaPercent !== null && (
              <p
                className={cn(
                  'mt-1 flex items-center gap-1 text-xs font-medium',
                  deltaPercent >= 0 ? 'text-success' : 'text-destructive',
                )}
              >
                {deltaPercent >= 0 ? (
                  <TrendingUp className="h-3 w-3" />
                ) : (
                  <TrendingDown className="h-3 w-3" />
                )}
                {deltaPercent >= 0 ? '+' : ''}
                {deltaPercent.toFixed(1)}% MoM
              </p>
            )}
          </div>
          <Sparkline points={sparkline ?? []} />
        </div>
      </CardContent>
    </Card>
  )
}

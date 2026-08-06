import { motion } from 'framer-motion'
import { TrendingDown, TrendingUp } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface KpiCardProps {
  label: string
  value: string
  deltaPercent: number | null
  sparkline?: number[]
  index?: number
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
  const color = positive ? 'var(--success)' : 'var(--destructive)'
  const gradientId = positive ? 'spark-up' : 'spark-down'
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="mt-2 w-full">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.25} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={`${path} L${w},${h} L0,${h} Z`} fill={`url(#${gradientId})`} />
      <path d={path} fill="none" stroke={color} strokeWidth={1.5} />
    </svg>
  )
}

export default function KpiCard({
  label,
  value,
  deltaPercent,
  sparkline,
  index = 0,
}: KpiCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.05, ease: 'easeOut' }}
    >
      <Card className="panel h-full overflow-hidden transition-transform hover:-translate-y-0.5">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
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
    </motion.div>
  )
}

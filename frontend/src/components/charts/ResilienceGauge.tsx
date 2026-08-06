import { motion } from 'framer-motion'

import { cn } from '@/lib/utils'

function thresholdColor(score: number): string {
  if (score < 40) return 'var(--danger, var(--destructive))'
  if (score <= 70) return 'var(--warning)'
  return 'var(--success)'
}

interface ResilienceGaugeProps {
  score: number
  className?: string
}

/** Radial 0–100 gauge colored by threshold, animated on mount. */
export function ResilienceGauge({ score, className }: ResilienceGaugeProps) {
  const clamped = Math.max(0, Math.min(100, score))
  const stroke = 10
  const radius = 44
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - clamped / 100)
  const color = thresholdColor(clamped)

  return (
    <div className={cn('flex flex-col items-center gap-3', className)}>
      <div className="relative h-32 w-32">
        <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="var(--muted)"
            strokeWidth={stroke}
          />
          <motion.circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 0.9, ease: 'easeOut' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-semibold text-foreground">
            {Math.round(clamped)}
          </span>
          <span className="text-xs text-muted-foreground">/ 100</span>
        </div>
      </div>
      <span
        className="text-xs font-medium uppercase tracking-wide"
        style={{ color }}
      >
        {clamped < 40 ? 'Fragile' : clamped <= 70 ? 'At risk' : 'Resilient'}
      </span>
    </div>
  )
}

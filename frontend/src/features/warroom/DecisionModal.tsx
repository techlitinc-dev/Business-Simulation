import { useMemo, useState } from 'react'
import { Swords } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'
import type { HurdleEvent, StrategicOption } from '@/features/simulation/types'

interface DecisionModalProps {
  open: boolean
  event: HurdleEvent | null
  onConfirm: (option: StrategicOption) => void
  submitting?: boolean
  onOpenChange: (open: boolean) => void
}

/** Inline 12-month cash projection sparkline for an option card. */
function ProjectionSparkline({ monthlyCash }: { monthlyCash: number[] }) {
  const points = useMemo(() => {
    if (monthlyCash.length === 0) return ''
    const w = 120
    const h = 32
    const min = Math.min(...monthlyCash, 0)
    const max = Math.max(...monthlyCash, 1)
    const range = max - min || 1
    return monthlyCash
      .map((v, i) => {
        const x = (i / (monthlyCash.length - 1)) * w
        const y = h - ((v - min) / range) * h
        return `${x.toFixed(1)},${y.toFixed(1)}`
      })
      .join(' ')
  }, [monthlyCash])

  if (monthlyCash.length === 0) return null

  return (
    <svg
      viewBox="0 0 120 32"
      className="h-8 w-full max-w-[120px]"
      preserveAspectRatio="none"
    >
      <polyline
        points={points}
        fill="none"
        stroke="var(--chart-2)"
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}

/** War Room decision modal — auto-opens when the run awaits a decision. */
export default function DecisionModal({
  open,
  event,
  onConfirm,
  submitting,
  onOpenChange,
}: DecisionModalProps) {
  const [selected, setSelected] = useState<StrategicOption | null>(null)

  const handleConfirm = () => {
    if (selected) onConfirm(selected)
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) setSelected(null) }}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Swords className="h-5 w-5 text-amber-400" /> The War Room
          </DialogTitle>
          <DialogDescription>
            {event?.narrative.title} — choose a strategic response.
          </DialogDescription>
        </DialogHeader>

        {event && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">{event.narrative.story}</p>
            <div className="space-y-2">
              {(event.strategic_options ?? []).map((option) => {
                const projection = event.options_projection?.find(
                  (p) => p.option_id === option.option_id,
                )
                const isSelected = selected?.option_id === option.option_id
                return (
                  <button
                    key={option.option_id}
                    type="button"
                    onClick={() => setSelected(option)}
                    className={cn(
                      'w-full rounded-md border p-3 text-left transition-all',
                      isSelected
                        ? 'border-primary bg-primary/10 ring-2 ring-primary/30'
                        : 'border-border hover:border-primary/50 hover:bg-accent',
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <span className="text-sm font-medium">
                          {option.option_id}. {option.name}
                        </span>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {option.description}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-3">
                        {projection && (
                          <div className="flex flex-col items-end">
                            <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                              12-mo projection
                            </span>
                            <ProjectionSparkline monthlyCash={projection.monthly_cash} />
                          </div>
                        )}
                        <span
                          className={cn(
                            'text-xs font-medium',
                            option.cash_impact_monthly > 0
                              ? 'text-emerald-400'
                              : option.cash_impact_monthly < 0
                                ? 'text-red-400'
                                : 'text-muted-foreground',
                          )}
                        >
                          {option.cash_impact_monthly === 0
                            ? 'No cash impact'
                            : `${option.cash_impact_monthly > 0 ? '+' : ''}$${option.cash_impact_monthly.toLocaleString()}/mo`}
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {Math.round(option.probability_success * 100)}% success ·{' '}
                        {option.required_execution}
                      </span>
                      {projection && (
                        <span className="ml-auto text-xs text-muted-foreground">
                          {projection.survives ? 'Survives' : 'Runs dry'} ·{' '}
                          {projection.runway_months?.toFixed(0)} mo runway
                        </span>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Defer
          </Button>
          <Button onClick={handleConfirm} disabled={!selected || submitting}>
            {submitting ? 'Applying…' : 'Confirm decision'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

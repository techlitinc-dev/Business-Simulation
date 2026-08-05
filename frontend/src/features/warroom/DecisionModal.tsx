import { useState } from 'react'
import { Swords } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { HurdleEvent, StrategicOption } from '@/features/simulation/types'

interface DecisionModalProps {
  open: boolean
  event: HurdleEvent | null
  onConfirm: (option: StrategicOption) => void
  submitting?: boolean
  onOpenChange: (open: boolean) => void
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
              {(event.strategic_options ?? []).map((option) => (
                <button
                  key={option.option_id}
                  onClick={() => setSelected(option)}
                  className={`w-full rounded-md border p-3 text-left transition-colors ${
                    selected?.option_id === option.option_id
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:bg-accent'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">
                      {option.option_id}. {option.name}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {option.cash_impact_monthly === 0
                        ? 'No cash impact'
                        : `${option.cash_impact_monthly > 0 ? '+' : ''}$${option.cash_impact_monthly.toLocaleString()}/mo`}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{option.description}</p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {Math.round(option.probability_success * 100)}% success ·{' '}
                    {option.required_execution}
                  </p>
                </button>
              ))}
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

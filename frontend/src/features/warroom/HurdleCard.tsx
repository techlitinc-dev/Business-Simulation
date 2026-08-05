import { AlertTriangle } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import type { HurdleEvent, StrategicOption } from '@/features/simulation/types'

interface HurdleCardProps {
  event: HurdleEvent
  onChoose: (option: StrategicOption) => void
  disabled?: boolean
}

/** A single hurdle with its strategic options (War Room). */
export default function HurdleCard({ event, onChoose, disabled }: HurdleCardProps) {
  return (
    <Card className="border-amber-500/40">
      <CardContent className="space-y-4 p-5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold">{event.narrative.title}</h3>
              <Badge className="text-muted-foreground">{event.category}</Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{event.narrative.story}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {event.trigger_timing} · {event.narrative.source_actor}
            </p>
          </div>
        </div>

        <div className="space-y-2">
          {(event.strategic_options ?? []).map((option) => (
            <button
              key={option.option_id}
              disabled={disabled}
              onClick={() => onChoose(option)}
              className="w-full rounded-md border border-border p-3 text-left transition-colors hover:border-primary/60 hover:bg-accent disabled:pointer-events-none disabled:opacity-50"
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
              <div className="mt-2 flex items-center gap-2">
                <Badge className="bg-secondary text-secondary-foreground">
                  {Math.round(option.probability_success * 100)}% success
                </Badge>
                <span className="text-xs text-muted-foreground">{option.required_execution}</span>
              </div>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

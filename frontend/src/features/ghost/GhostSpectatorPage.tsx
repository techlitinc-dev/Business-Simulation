import { useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Ghost, Radio } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import CashCurve from '@/components/charts/CashCurve'
import { useSimulation, useTicks } from '@/features/simulation/api'
import type { HurdleEvent } from '@/features/simulation/types'
import { useSimulationSocket } from '@/lib/ws'
import { useSimulationStore } from '@/stores/simulation'

const PERSONALITY_META: Record<string, { emoji: string; label: string }> = {
  aggressive: { emoji: '🦁', label: 'Aggressive' },
  conservative: { emoji: '🐢', label: 'Conservative' },
  opportunist: { emoji: '🦊', label: 'Opportunist' },
}

function DecisionFeed({ events }: { events: HurdleEvent[] }) {
  const decisions = events
    .filter((e) => e.chosen_option_id)
    .map((e) => {
      const option = e.strategic_options?.find(
        (o) => o.option_id === e.chosen_option_id,
      )
      const payload = (e as HurdleEvent & { ghost_decision?: { rationale?: string } })
        .ghost_decision
      return { event: e, option, payload }
    })

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Radio className="h-4 w-4" /> Ghost Decision Feed
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto pt-0">
        {decisions.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No decisions yet — the ghost is thinking.
          </p>
        ) : (
          <div className="space-y-3">
            {[...decisions].reverse().map(({ event, option }) => (
              <div key={event.event_id} className="rounded-lg border border-border p-3">
                <p className="text-sm font-medium">{event.narrative.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {event.trigger_timing}
                </p>
                <div className="mt-2 flex items-center gap-2 text-xs">
                  <Ghost className="h-3.5 w-3.5 text-primary" />
                  <span className="font-medium text-primary">
                    Ghost chose {option?.name ?? event.chosen_option_id}
                  </span>
                </div>
                {event.ai_game_master_note && (
                  <p className="mt-1 text-xs italic text-muted-foreground">
                    “{event.ai_game_master_note}”
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function GhostSpectatorPage() {
  const { runId } = useParams<{ runId: string }>()
  const store = useSimulationStore()

  const { data: runData } = useSimulation(runId)
  const { data: ticksData = [] } = useTicks(runId)
  useSimulationSocket(runId)

  const run = store.run ?? runData ?? null
  const ticks = store.ticks.length > 0 ? store.ticks : ticksData
  const events = store.events

  useEffect(() => {
    if (runData && !store.run) {
      store.hydrate(runData, ticksData)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runData])

  if (!run) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-72 w-full" />
      </div>
    )
  }

  const personality = (run.config?.personality as string | undefined) ?? 'ghost'
  const personalityMeta = PERSONALITY_META[personality] ?? {
    emoji: '👻',
    label: personality,
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Button variant="ghost" size="sm" asChild className="-ml-2">
            <Link to="/app/simulations">
              <ArrowLeft className="h-4 w-4" /> Back to runs
            </Link>
          </Button>
          <div className="mt-1 flex items-center gap-2">
            <h1 className="text-2xl font-semibold">Ghost Run</h1>
            <Badge className="border-primary/40 bg-primary/10 text-primary">
              <span className="mr-1">{personalityMeta.emoji}</span>
              {personalityMeta.label}
            </Badge>
            <Badge className="border-border bg-muted/40">{run.status}</Badge>
          </div>
        </div>
        <div className="text-sm text-muted-foreground">
          Month {run.current_month} · seed {run.seed}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <Card>
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
        <DecisionFeed events={events} />
      </div>
    </div>
  )
}

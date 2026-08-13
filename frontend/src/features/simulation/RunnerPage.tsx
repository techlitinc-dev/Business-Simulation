import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Pause, Play, X } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import CashCurve from '@/components/charts/CashCurve'
import LiveFeed from '@/features/simulation/LiveFeed'
import DecisionModal from '@/features/warroom/DecisionModal'
import { useControl, useDecide, useSimulation, useTicks } from '@/features/simulation/api'
import type { RunStatus, StrategicOption } from '@/features/simulation/types'
import { useSimulationSocket } from '@/lib/ws'
import { useSimulationStore } from '@/stores/simulation'

const STATUS_STYLES: Record<string, string> = {
  awaiting_decision: 'animate-pulse border-amber-500/50 bg-amber-500/10 text-amber-300',
  dead: 'bg-red-500/10 text-red-300 border-red-500/40',
  completed: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/40',
  running: 'bg-blue-500/10 text-blue-300 border-blue-500/40',
  paused: 'bg-slate-500/10 text-slate-300 border-slate-500/40',
  pending: 'bg-blue-500/10 text-blue-300 border-blue-500/40',
  cancelled: 'bg-slate-500/10 text-slate-300 border-slate-500/40',
  failed: 'bg-red-500/10 text-red-300 border-red-500/40',
}

const TERMINAL: RunStatus[] = ['completed', 'dead', 'cancelled', 'failed']

export default function RunnerPage() {
  const { runId } = useParams<{ runId: string }>()
  const store = useSimulationStore()

  const { data: runData } = useSimulation(runId)
  const { data: ticksData = [] } = useTicks(runId)
  const decide = useDecide(runId)
  const control = useControl(runId)

  const connectionStatus = useSimulationSocket(runId)

  const run = store.run ?? runData ?? null
  const ticks = store.ticks.length > 0 ? store.ticks : ticksData
  const events = store.events
  const [modalDismissed, setModalDismissed] = useState(false)

  // Hydrate from REST once when the socket hasn't delivered yet.
  useEffect(() => {
    if (runData && !store.run) {
      store.hydrate(runData, ticksData)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runData])

  const pendingEvent = events[events.length - 1] ?? null
  const awaiting = run?.status === 'awaiting_decision' && !modalDismissed

  // Re-arm the modal whenever a fresh hurdle arrives (new event_id).
  useEffect(() => {
    if (pendingEvent && run?.status === 'awaiting_decision') {
      setModalDismissed(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingEvent?.event_id])

  const handleConfirm = (option: StrategicOption) => {
    if (!pendingEvent) return
    decide.mutate(
      { event_id: pendingEvent.event_id, option_id: option.option_id },
      {
        onSuccess: (data) => {
          store.setStatus(data.run.status)
          store.setRun(data.run)
          setModalDismissed(false)
        },
      },
    )
  }

  const status = (run?.status ?? store.liveStatus ?? 'pending') as RunStatus
  const statusClass = STATUS_STYLES[status] ?? ''
  const isTerminal = TERMINAL.includes(status)

  const progress = run?.mode === 'monte_carlo' ? (store.progress ?? run.progress) : null
  const percent = progress?.percent ?? 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
            <Link to="/app/simulations">
              <ArrowLeft className="h-4 w-4" /> Back to runs
            </Link>
          </Button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">Simulation Run</h1>
            <Badge className={statusClass}>{status}</Badge>
            <Badge className="text-muted-foreground">{run?.mode ?? '…'}</Badge>
            {connectionStatus === 'open' ? (
              <span className="text-xs text-emerald-400">● live</span>
            ) : (
              <span className="text-xs text-amber-400">○ reconnecting</span>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Month {run?.current_month ?? 0} / {run?.config.months ?? 24} · seed {run?.seed ?? '—'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {status === 'completed' && (
            <Button variant="outline" asChild>
              <Link to={`/app/simulations/${runId}/report`}>View report</Link>
            </Button>
          )}
          {status === 'awaiting_decision' && (
            <Button
              variant="outline"
              onClick={() =>
                control.mutate('pause', { onSuccess: (data) => store.setRun(data) })
              }
              disabled={isTerminal}
            >
              <Pause className="h-4 w-4" /> Pause
            </Button>
          )}
          {status === 'paused' && (
            <Button
              variant="outline"
              onClick={() =>
                control.mutate('resume', { onSuccess: (data) => store.setRun(data) })
              }
              disabled={isTerminal}
            >
              <Play className="h-4 w-4" /> Resume
            </Button>
          )}
          <Button
            variant="ghost"
            className="text-destructive"
            onClick={() =>
              control.mutate('cancel', {
                onSuccess: (data) => {
                  store.setRun(data)
                  setModalDismissed(true)
                },
              })
            }
            disabled={isTerminal}
          >
            <X className="h-4 w-4" /> Cancel
          </Button>
        </div>
      </div>

      {progress && run?.mode === 'monte_carlo' && (
        <Card>
          <CardContent className="p-4">
            <div className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
              <span>Monte Carlo batch</span>
              <span>
                {progress.completed}/{progress.total} ({percent}%)
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${percent}%` }}
              />
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Cash curve</CardTitle>
          </CardHeader>
          <CardContent>
            <CashCurve ticks={ticks} />
          </CardContent>
        </Card>
        <LiveFeed events={events} />
      </div>

      <DecisionModal
        open={awaiting}
        event={pendingEvent}
        submitting={decide.isPending}
        onConfirm={handleConfirm}
        onOpenChange={(open) => {
          // Defer — close the modal but leave the run awaiting a decision.
          if (!open) setModalDismissed(true)
        }}
      />
    </div>
  )
}

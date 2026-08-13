import { useEffect, useRef } from 'react'
import { Swords } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { HurdleEvent, TickLog } from '@/features/simulation/types'

interface LiveFeedProps {
  events: HurdleEvent[]
  ticks?: TickLog[]
}

const CATEGORY_STYLES: Record<string, string> = {
  market: 'border-blue-500/40 bg-blue-500/10 text-blue-300',
  operational: 'border-orange-500/40 bg-orange-500/10 text-orange-300',
  financial: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-300',
  black_swan: 'border-purple-500/40 bg-purple-500/10 text-purple-300',
  internal: 'border-pink-500/40 bg-pink-500/10 text-pink-300',
}

type FeedEntry =
  | { kind: 'tick'; month: number; cash: number }
  | { kind: 'event'; event: HurdleEvent }

/** Reverse-chronological feed of hurdles interleaved with monthly ticks. */
export default function LiveFeed({ events, ticks = [] }: LiveFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [events.length, ticks.length])

  const entries: FeedEntry[] = []
  for (const t of ticks) {
    entries.push({ kind: 'tick', month: t.month, cash: t.kpis.cash_balance ?? 0 })
  }
  for (const e of events) {
    const monthMatch = e.trigger_timing?.match(/\d+/)
    const month = monthMatch ? parseInt(monthMatch[0], 10) : null
    if (month) {
      const existing = entries.findIndex((en) => en.kind === 'tick' && en.month === month)
      if (existing >= 0) {
        entries.splice(existing, 0, { kind: 'event', event: e })
        continue
      }
    }
    entries.push({ kind: 'event', event: e })
  }
  entries.sort((a, b) => {
    const am = a.kind === 'tick' ? a.month : (a.event.trigger_timing?.match(/\d+/)?.[0] ?? 0)
    const bm = b.kind === 'tick' ? b.month : (b.event.trigger_timing?.match(/\d+/)?.[0] ?? 0)
    return Number(bm) - Number(am)
  })

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Swords className="h-4 w-4" /> War Room Feed
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto pt-0" ref={scrollRef}>
        {entries.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No activity yet — the market is quiet.
          </p>
        ) : (
          <div className="space-y-2">
            {entries.map((entry) =>
              entry.kind === 'tick' ? (
                <div
                  key={`tick-${entry.month}`}
                  className="flex items-center gap-2 rounded-md border border-border/50 bg-muted/20 px-3 py-1.5"
                >
                  <span className="text-xs font-medium text-muted-foreground">
                    Month {entry.month}: Tick
                  </span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    ${entry.cash.toLocaleString()}
                  </span>
                </div>
              ) : (
                <div
                  key={entry.event.event_id}
                  className="rounded-lg border border-border p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium">{entry.event.narrative.title}</p>
                    <Badge className={CATEGORY_STYLES[entry.event.category] ?? ''}>
                      {entry.event.category}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {entry.event.trigger_timing} · {entry.event.narrative.source_actor}
                  </p>
                  {entry.event.chosen_option_id ? (
                    <p className="mt-2 text-xs text-emerald-400">
                      Decided: option {entry.event.chosen_option_id}
                    </p>
                  ) : (
                    <p className="mt-2 text-xs text-amber-400">Awaiting decision…</p>
                  )}
                </div>
              ),
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

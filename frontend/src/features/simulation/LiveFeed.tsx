import { useEffect, useRef } from 'react'
import { Swords } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { HurdleEvent } from '@/features/simulation/types'

interface LiveFeedProps {
  events: HurdleEvent[]
}

const CATEGORY_STYLES: Record<string, string> = {
  market: 'border-blue-500/40 bg-blue-500/10 text-blue-300',
  operational: 'border-orange-500/40 bg-orange-500/10 text-orange-300',
  financial: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-300',
  black_swan: 'border-purple-500/40 bg-purple-500/10 text-purple-300',
  internal: 'border-pink-500/40 bg-pink-500/10 text-pink-300',
}

/** Reverse-chronological feed of hurdles interleaved with milestone ticks. */
export default function LiveFeed({ events }: LiveFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [events.length])

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Swords className="h-4 w-4" /> War Room Feed
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto pt-0" ref={scrollRef}>
        {events.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No hurdles yet — the market is quiet.
          </p>
        ) : (
          <div className="space-y-3">
            {[...events].reverse().map((event) => (
              <div
                key={event.event_id}
                className="rounded-lg border border-border p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{event.narrative.title}</p>
                  <Badge className={CATEGORY_STYLES[event.category] ?? ''}>
                    {event.category}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {event.trigger_timing} · {event.narrative.source_actor}
                </p>
                {event.chosen_option_id ? (
                  <p className="mt-2 text-xs text-emerald-400">
                    Decided: option {event.chosen_option_id}
                  </p>
                ) : (
                  <p className="mt-2 text-xs text-amber-400">Awaiting decision…</p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

import { create } from 'zustand'

import type { HurdleEvent, RunStatus, SimulationRun, TickLog } from '@/features/simulation/types'

interface SimulationState {
  run: SimulationRun | null
  ticks: TickLog[]
  events: HurdleEvent[]
  liveStatus: RunStatus | null
  progress: { completed: number; total: number; percent: number } | null
  hydrate: (run: SimulationRun, ticks: TickLog[]) => void
  appendTick: (t: { month: number; kpis: Record<string, number> }) => void
  appendEvent: (e: HurdleEvent) => void
  setStatus: (s: RunStatus) => void
  setProgress: (p: { completed: number; total: number; percent: number }) => void
  reset: () => void
}

export const useSimulationStore = create<SimulationState>((set, get) => ({
  run: null,
  ticks: [],
  events: [],
  liveStatus: null,
  progress: null,

  hydrate: (run, ticks) =>
    set({ run, ticks: [...ticks], liveStatus: run.status, events: [] }),

  appendTick: (t) => {
    const { ticks, run } = get()
    // Dedupe by month so reconnects never double-append.
    if (ticks.some((row) => row.month === t.month)) return
    const next: TickLog[] = [...ticks, { id: `ws-${t.month}`, run_id: run?.id ?? '', month: t.month, kpis: t.kpis }]
    set({ ticks: next })
  },

  appendEvent: (e) => {
    const { events } = get()
    if (events.some((ev) => ev.event_id === e.event_id)) return
    set({ events: [...events, e] })
  },

  setStatus: (s) => {
    const { run } = get()
    const updated = run ? { ...run, status: s } : run
    set({ liveStatus: s, run: updated })
  },

  setProgress: (p) => set({ progress: p }),

  reset: () =>
    set({ run: null, ticks: [], events: [], liveStatus: null, progress: null }),
}))

import { useEffect, useMemo, useState } from 'react'

import { useChannelSocket } from '@/lib/ws'
import { useDeepReportStatus } from './api'

export interface ProgressEvent {
  job_id: string
  section: number
  total: number
  status: 'writing' | 'done' | 'error'
  section_title: string
}

interface Props {
  jobId: string
  totalSections: number
  onComplete: () => void
}

/**
 * Live section progress for a deep-dive report job.
 *
 * Streams per-section progress over `/ws/reports/{jobId}` (the backend
 * forwards the worker's `deep_report:{job_id}` Redis publishes) and falls
 * back to polling the status endpoint when the socket is unavailable.
 */
export function SectionProgressFeed({ jobId, totalSections, onComplete }: Props) {
  const [events, setEvents] = useState<ProgressEvent[]>([])
  const [current, setCurrent] = useState<ProgressEvent | null>(null)
  const { lastMessage, connectionStatus } = useChannelSocket(`/ws/reports/${jobId}`)
  const { data: job } = useDeepReportStatus(jobId)

  // Live events from the WebSocket channel.
  useEffect(() => {
    if (!lastMessage) return
    try {
      const evt = JSON.parse(lastMessage) as ProgressEvent
      setCurrent(evt)
      setEvents((prev) => {
        const exists = prev.find((e) => e.section === evt.section && e.status === evt.status)
        return exists ? prev : [...prev, evt]
      })
      if (evt.status === 'done' && evt.section === evt.total) {
        const t = setTimeout(onComplete, 800)
        return () => clearTimeout(t)
      }
    } catch {
      // Ignore malformed frames.
    }
    return undefined
  }, [lastMessage, onComplete])

  // Polled status: drives completion when the socket is closed/unavailable,
  // and backfills the final "done" event.
  useEffect(() => {
    if (!job || connectionStatus === 'open') return
    const total = job.total_sections || totalSections
    if (job.status === 'completed') {
      const evt: ProgressEvent = {
        job_id: job.job_id,
        section: total,
        total,
        status: 'done',
        section_title: 'Report complete',
      }
      setCurrent(evt)
      setEvents((prev) => {
        const exists = prev.some((e) => e.status === 'done' && e.section === total)
        return exists ? prev : [...prev, evt]
      })
      const t = setTimeout(onComplete, 800)
      return () => clearTimeout(t)
    }
    return undefined
  }, [job, connectionStatus, totalSections, onComplete])

  const doneCount = useMemo(
    () => events.filter((e) => e.status === 'done').length,
    [events],
  )
  const pct = totalSections > 0 ? Math.round((doneCount / totalSections) * 100) : 0

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm text-slate-400">
          <span>Writing report...</span>
          <span>{pct}%</span>
        </div>
        <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-500 rounded-full"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Current section */}
      {current && (
        <p className="text-slate-300 text-sm animate-pulse">
          {current.status === 'writing' ? '✍️' : '✅'} Writing section {current.section} of{' '}
          {current.total}: <span className="text-white font-medium">{current.section_title}</span>
        </p>
      )}

      {/* Section list */}
      <div className="max-h-64 overflow-y-auto space-y-1">
        {events.map((evt, i) => (
          <div
            key={i}
            className={`flex items-center gap-2 text-sm ${
              evt.status === 'done' ? 'text-green-400' : 'text-blue-400 animate-pulse'
            }`}
          >
            <span>{evt.status === 'done' ? '✅' : '⏳'}</span>
            <span>
              {evt.section}. {evt.section_title}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

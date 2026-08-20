import { useState } from 'react'

import { Button } from '@/components/ui/button'
import type { WorkspaceSummary } from './api'

interface Props {
  workspaces: WorkspaceSummary[]
}

export function CohortRankings({ workspaces }: Props) {
  const [anonymized, setAnonymized] = useState(false)
  const sorted = [...workspaces].sort(
    (a, b) => (b.resilience_score ?? 0) - (a.resilience_score ?? 0),
  )

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-white font-semibold">Cohort Rankings</h3>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setAnonymized(!anonymized)}
          className="border-slate-600 text-slate-300"
        >
          {anonymized ? 'Show Names' : 'Anonymize'}
        </Button>
      </div>
      <div className="space-y-1">
        {sorted.map((ws, i) => (
          <div key={ws.workspace_id} className="flex items-center gap-3 text-sm">
            <span className="text-slate-500 w-6">#{i + 1}</span>
            <span className="text-white flex-1">
              {anonymized ? `Company ${i + 1}` : ws.label}
            </span>
            <span className="text-blue-400 font-medium">
              {ws.resilience_score?.toFixed(1) ?? '—'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toastError } from '@/lib/toast'
import {
  getPlaybook,
  useJournalSummary,
  useRunJournal,
} from '@/features/journal/api'
import type { Playbook } from '@/features/journal/api'

export function DecisionJournalPage() {
  const { runId } = useParams<{ runId: string }>()
  const queryClient = useQueryClient()
  const { data: entries = [] } = useRunJournal(runId)
  const { data: summary } = useJournalSummary()

  const playbook = useMutation({
    mutationFn: () => {
      if (!runId) throw new Error('Run not found')
      return getPlaybook(runId)
    },
    onSuccess: (data: Playbook) => {
      queryClient.setQueryData(['journal', runId, 'playbook'], data)
    },
    onError: (err: unknown) => {
      toastError(
        err instanceof Error ? err.message : 'Failed to generate playbook',
        'Playbook generation failed',
      )
    },
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">Decision Journal</h1>
        <Button onClick={() => playbook.mutate()} disabled={playbook.isPending}>
          {playbook.isPending ? 'Generating…' : 'Generate Playbook'}
        </Button>
      </div>

      {summary && (
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white text-base">Workspace Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-white font-semibold">{summary.summary}</p>
            <p className="text-blue-400 text-sm">{summary.beat_ai_pct}% beat rate</p>
          </CardContent>
        </Card>
      )}

      {playbook.data && (
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white text-base">{playbook.data.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p className="text-slate-300">{playbook.data.situation}</p>
            <ol className="list-decimal pl-5 space-y-1 text-slate-300">
              {playbook.data.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            <p className="text-slate-400">
              Metrics to watch: {playbook.data.key_metrics_to_watch.join(', ')}
            </p>
          </CardContent>
        </Card>
      )}

      <div className="space-y-2">
        {entries.map((e) => (
          <div
            key={e.decision_id}
            className="flex items-center gap-3 text-sm bg-slate-800 border border-slate-700 rounded p-3"
          >
            <span className="text-slate-400 w-16">
              {e.month != null ? `Month ${e.month}` : '—'}
            </span>
            <span className="text-white flex-1">
              {e.option_name ?? e.option_chosen}
            </span>
            <span className={e.beat_ai ? 'text-green-400' : 'text-red-400'}>
              {e.beat_ai ? '✓ Beat AI' : '✗ Missed AI'}
            </span>
            <span className="text-slate-400">{(e.score * 100).toFixed(0)}pts</span>
          </div>
        ))}
        {entries.length === 0 && (
          <p className="text-slate-400 text-sm">No decisions recorded for this run yet.</p>
        )}
      </div>
    </div>
  )
}

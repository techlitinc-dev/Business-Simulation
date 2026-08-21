import { useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { useWorkspaceStore } from '@/stores/workspace-store'

export interface JournalEntry {
  decision_id: string
  run_id: string
  month: number | null
  option_chosen: string
  option_name: string | null
  beat_ai: boolean
  actual_outcome: Record<string, unknown>
  score: number
}

export interface JournalSummary {
  total_decisions: number
  beat_ai_count: number
  beat_ai_pct: number
  summary: string
}

export interface Playbook {
  title: string
  scenario_type: string
  situation: string
  steps: string[]
  key_metrics_to_watch: string[]
  expected_outcome: string
  source_run_summary: string
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export function useRunJournal(runId: string | undefined) {
  return useQuery({
    queryKey: ['journal', runId],
    queryFn: () =>
      apiFetch<JournalEntry[]>(`/api/v1/journal/simulations/${runId}`, {
        headers: workspaceHeaders(),
      }),
    enabled: Boolean(runId),
  })
}

export function useJournalSummary() {
  return useQuery({
    queryKey: ['journal', 'summary'],
    queryFn: () =>
      apiFetch<JournalSummary>('/api/v1/journal/summary', {
        headers: workspaceHeaders(),
      }),
  })
}

export async function getPlaybook(runId: string): Promise<Playbook> {
  return apiFetch<Playbook>(`/api/v1/journal/simulations/${runId}/playbook`, {
    method: 'POST',
    headers: workspaceHeaders(),
  })
}

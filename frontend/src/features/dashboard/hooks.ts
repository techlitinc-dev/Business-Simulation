import { useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import type { SimulationRun, TickLog } from '@/features/simulation/types'
import type { ReportOut } from '@/features/reports/hooks'
import { useWorkspaceStore } from '@/stores/workspace-store'

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export function useRecentRuns() {
  return useQuery({
    queryKey: ['runs', 'recent'],
    queryFn: () =>
      apiFetch<SimulationRun[]>('/api/v1/simulations', {
        headers: workspaceHeaders(),
      }),
  })
}

export function useTicks(runId: string | undefined) {
  return useQuery({
    queryKey: ['simulation', runId, 'ticks'],
    queryFn: () =>
      apiFetch<TickLog[]>(`/api/v1/simulations/${runId}/ticks`, {
        headers: workspaceHeaders(),
      }),
    enabled: Boolean(runId),
  })
}

export function useReport(runId: string | undefined) {
  return useQuery({
    queryKey: ['report', runId],
    queryFn: () =>
      apiFetch<ReportOut>(`/api/v1/reports/simulations/${runId}/report`, {
        headers: workspaceHeaders(),
      }),
    enabled: Boolean(runId),
  })
}

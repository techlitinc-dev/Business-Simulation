import { useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import type { SimulationRun, TickLog } from '@/features/simulation/types'
import type { ReportOut } from '@/features/reports/hooks'
import { useWorkspaceStore } from '@/stores/workspace-store'

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

/**
 * The active workspace id from the store. Returns undefined until the
 * Sidebar's useWorkspaces() query resolves and populates the store — the
 * dashboard queries are gated on this so they never fire without the
 * X-Workspace-Id header (which would 403).
 */
function useActiveWorkspaceId(): string | undefined {
  return useWorkspaceStore((s) => s.activeWorkspaceId ?? undefined)
}

export function useRecentRuns() {
  const workspaceId = useActiveWorkspaceId()
  return useQuery({
    queryKey: ['runs', 'recent', workspaceId],
    queryFn: () =>
      apiFetch<SimulationRun[]>('/api/v1/simulations', {
        headers: workspaceHeaders(),
      }),
    enabled: Boolean(workspaceId),
  })
}

export function useTicks(runId: string | undefined) {
  const workspaceId = useActiveWorkspaceId()
  return useQuery({
    queryKey: ['simulation', runId, 'ticks', workspaceId],
    queryFn: () =>
      apiFetch<TickLog[]>(`/api/v1/simulations/${runId}/ticks`, {
        headers: workspaceHeaders(),
      }),
    enabled: Boolean(runId && workspaceId),
  })
}

export function useReport(runId: string | undefined) {
  const workspaceId = useActiveWorkspaceId()
  return useQuery({
    queryKey: ['report', runId, workspaceId],
    queryFn: () =>
      apiFetch<ReportOut>(`/api/v1/reports/simulations/${runId}/report`, {
        headers: workspaceHeaders(),
      }),
    enabled: Boolean(runId && workspaceId),
  })
}

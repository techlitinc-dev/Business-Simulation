import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { toastSuccess, toastError } from '@/lib/toast'
import { useWorkspaceStore } from '@/stores/workspace-store'
import type { RunMode, SimulationRun, TickLog } from './types'

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export interface StartSimulationBody {
  blueprint_version_id: string
  mode: RunMode
  seed?: number | null
  config?: { months?: number; difficulty?: string; n_runs?: number }
}

export function useStartSimulation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: StartSimulationBody) =>
      apiFetch<SimulationRun>('/api/v1/simulations', {
        method: 'POST',
        headers: workspaceHeaders(),
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      toastSuccess('Simulation started', 'Your run is in the War Room')
      void queryClient.invalidateQueries({ queryKey: ['simulations'] })
    },
    onError: (err: unknown) => {
      toastError(
        err instanceof Error ? err.message : 'Failed to start simulation',
        'Simulation failed to start',
      )
    },
  })
}

export function useSimulation(runId: string | undefined) {
  return useQuery({
    queryKey: ['simulation', runId],
    queryFn: () =>
      apiFetch<SimulationRun>(`/api/v1/simulations/${runId}`, {
        headers: workspaceHeaders(),
      }),
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const run = query.state.data
      return run?.status === 'pending' ? 2000 : false
    },
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

export function useDecide(runId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { event_id: string; option_id: string }) =>
      apiFetch<{ decision_id: string; event_id: string; option_id: string; run: SimulationRun }>(
        `/api/v1/simulations/${runId}/decide`,
        {
          method: 'POST',
          headers: workspaceHeaders(),
          body: JSON.stringify(body),
        },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['simulation', runId] })
      void queryClient.invalidateQueries({ queryKey: ['simulation', runId, 'ticks'] })
    },
  })
}

export function useControl(runId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (action: 'pause' | 'resume' | 'cancel') =>
      apiFetch<SimulationRun>(`/api/v1/simulations/${runId}/control`, {
        method: 'POST',
        headers: workspaceHeaders(),
        body: JSON.stringify({ action }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['simulation', runId] })
      void queryClient.invalidateQueries({ queryKey: ['simulation', runId, 'ticks'] })
    },
  })
}

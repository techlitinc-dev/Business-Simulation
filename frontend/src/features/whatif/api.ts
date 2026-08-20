import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { useWorkspaceStore } from '@/stores/workspace-store'

export interface SweepGridPoint {
  param_value: number
  survival_rate: number
  median_runway: number
  p25_runway: number
  p75_runway: number
}

export interface SweepResult {
  blueprint_id: string
  param: string
  grid: SweepGridPoint[]
}

export interface BreakevenResult {
  blueprint_id: string
  param: string
  breakeven_value: number
  survival_at_breakeven: number
  message: string
}

export interface SavedVersion {
  id: string
  blueprint_id: string
  version: number
  created_at: string
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export async function runSweep(
  blueprintId: string,
  param: string,
  minValue: number,
  maxValue: number,
  steps = 8,
): Promise<SweepResult> {
  return apiFetch<SweepResult>('/api/v1/whatif/sweep', {
    method: 'POST',
    headers: workspaceHeaders(),
    body: JSON.stringify({
      workspace_id: useWorkspaceStore.getState().activeWorkspaceId,
      blueprint_id: blueprintId,
      param,
      min_value: minValue,
      max_value: maxValue,
      steps,
      mc_runs: 20,
    }),
  })
}

export async function findBreakeven(
  blueprintId: string,
  param: string,
  searchMin: number,
  searchMax: number,
): Promise<BreakevenResult> {
  return apiFetch<BreakevenResult>('/api/v1/whatif/breakeven', {
    method: 'POST',
    headers: workspaceHeaders(),
    body: JSON.stringify({
      workspace_id: useWorkspaceStore.getState().activeWorkspaceId,
      blueprint_id: blueprintId,
      param,
      search_min: searchMin,
      search_max: searchMax,
    }),
  })
}

export async function saveVersion(
  blueprintId: string,
  param: string,
  value: number,
  label: string,
): Promise<SavedVersion> {
  return apiFetch<SavedVersion>('/api/v1/whatif/save-version', {
    method: 'POST',
    headers: workspaceHeaders(),
    body: JSON.stringify({
      blueprint_id: blueprintId,
      param,
      value,
      version_label: label,
    }),
  })
}

/** Run a sweep and cache the grid under a stable query key. */
export function useSweep(
  blueprintId: string | undefined,
  param: string,
  minValue: number,
  maxValue: number,
  steps = 8,
) {
  return useQuery({
    queryKey: ['whatif', 'sweep', blueprintId, param, minValue, maxValue, steps],
    queryFn: () =>
      runSweep(blueprintId ?? '', param, minValue, maxValue, steps),
    enabled: Boolean(blueprintId),
  })
}

/** Fork a blueprint version with an override applied; refreshes versions. */
export function useSaveVersion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (args: { blueprintId: string; param: string; value: number; label: string }) =>
      saveVersion(args.blueprintId, args.param, args.value, args.label),
    onSuccess: (_saved, args) => {
      void queryClient.invalidateQueries({ queryKey: ['blueprint', args.blueprintId, 'versions'] })
    },
  })
}

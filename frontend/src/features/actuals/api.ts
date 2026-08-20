import { useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { useWorkspaceStore } from '@/stores/workspace-store'

export interface ActualsUploadResult {
  records_created: number
  records_updated: number
  validation_warnings: { row: number; errors: string[] }[]
  unmapped_columns: string[]
}

export interface VarianceReport {
  delta: {
    blueprint_id: string
    month: number
    prior_survival_rate: number
    new_survival_rate: number
    survival_delta: number
    prior_runway_median: number
    new_runway_median: number
    runway_delta: number
    prior_resilience_score: number
    new_resilience_score: number
    score_delta: number
    key_changes: string[]
  }
  narrative: {
    headline: string
    explanation: string
    primary_driver: string
    outlook: string
  }
}

export type ActualsHistoryRow = { month: number; period_label?: string | null } & Record<
  string,
  number
>

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export async function uploadActuals(
  blueprintId: string,
  csvContent: string,
  columnMapping: Record<string, string> = {},
): Promise<ActualsUploadResult> {
  return apiFetch<ActualsUploadResult>('/api/v1/actuals/upload', {
    method: 'POST',
    headers: workspaceHeaders(),
    body: JSON.stringify({
      blueprint_id: blueprintId,
      csv_content: csvContent,
      column_mapping: columnMapping,
    }),
  })
}

export async function getVarianceReport(blueprintId: string): Promise<VarianceReport> {
  return apiFetch<VarianceReport>(`/api/v1/actuals/${blueprintId}/variance`, {
    headers: workspaceHeaders(),
  })
}

export async function getActualsHistory(
  blueprintId: string,
): Promise<ActualsHistoryRow[]> {
  return apiFetch<ActualsHistoryRow[]>(`/api/v1/actuals/${blueprintId}/history`, {
    headers: workspaceHeaders(),
  })
}

export function useVarianceReport(blueprintId: string | undefined) {
  return useQuery({
    queryKey: ['actuals', blueprintId, 'variance'],
    queryFn: () => getVarianceReport(blueprintId ?? ''),
    enabled: Boolean(blueprintId),
  })
}

export function useActualsHistory(blueprintId: string | undefined) {
  return useQuery({
    queryKey: ['actuals', blueprintId, 'history'],
    queryFn: () => getActualsHistory(blueprintId ?? ''),
    enabled: Boolean(blueprintId),
  })
}

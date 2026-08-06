import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { useWorkspaceStore } from '@/stores/workspace-store'

export interface KillVector {
  cause: string
  count: number
  pct: number
}

export interface SurvivalMetrics {
  survival_rate: number
  runs_total: number
  runs_survived: number
  median_lifespan_months: number
  kill_vectors: KillVector[]
}

export interface Weakness {
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  title: string
  detail: string
}

export interface OptimizationEntry {
  tweak_key: string
  recommendation: string
  implementation_cost: string
  impact_on_survival_rate: number
  trade_off: string
}

export interface ReportContent {
  survival: SurvivalMetrics
  weaknesses: Weakness[]
  optimizations: OptimizationEntry[]
  counter_factual: { text: string; deltas: unknown[] }
  blueprint_version: number
  resilience_score: number
}

export interface ReportOut {
  id: string
  run_id: string
  type: string
  content_md: string
  content_json: ReportContent
  pdf_path: string | null
  created_at: string
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
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

export interface SharedReportOut {
  blueprint_name: string
  completed_at: string
  content_md: string
  content_json: ReportContent
}

export function useSharedReport(token: string | undefined) {
  return useQuery({
    queryKey: ['shared-report', token],
    queryFn: () =>
      apiFetch<SharedReportOut>(`/api/v1/reports/shared/${token}`),
    enabled: Boolean(token),
  })
}

export function useExportPdf(runId: string | undefined) {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ pdf_url: string }>(
        `/api/v1/reports/simulations/${runId}/report/export`,
        {
          method: 'POST',
          headers: workspaceHeaders(),
        },
      ),
  })
}

export function useShareReport(runId: string | undefined) {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ share_url: string; token: string }>(
        `/api/v1/reports/simulations/${runId}/report/share`,
        {
          method: 'POST',
          headers: workspaceHeaders(),
        },
      ),
  })
}

export function useRevokeShare(runId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<void>(`/api/v1/reports/simulations/${runId}/report/share`, {
        method: 'DELETE',
        headers: workspaceHeaders(),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['report', runId] })
    },
  })
}

export interface RunSummary {
  run_id: string
  blueprint_version_id: string
  blueprint_version: number
  survival_rate: number
  median_lifespan_months: number
  resilience_score: number
  top_kill_vector: string
}

export interface KillVectorChange {
  cause: string
  pct_a: number
  pct_b: number
  delta_pp: number
}

export interface ComparisonResponse {
  a: RunSummary
  b: RunSummary
  deltas: {
    survival_rate_pp: number
    median_lifespan_months: number
    resilience_score_pp: number
  }
  kill_vector_changes: KillVectorChange[]
  verdict: 'improved' | 'regressed' | 'unchanged'
}

export function useCompare(runA: string, runB: string) {
  return useQuery({
    queryKey: ['compare', runA, runB],
    queryFn: () =>
      apiFetch<ComparisonResponse>(
        `/api/v1/reports/compare?a=${encodeURIComponent(runA)}&b=${encodeURIComponent(runB)}`,
        { headers: workspaceHeaders() },
      ),
    enabled: Boolean(runA) && Boolean(runB),
  })
}

export function useCompletedRuns() {
  return useQuery({
    queryKey: ['runs', 'completed'],
    queryFn: () => apiFetch<SimulationRunOut[]>('/api/v1/simulations', {
      headers: workspaceHeaders(),
    }),
  })
}

interface SimulationRunOut {
  id: string
  mode: string
  status: string
  blueprint_version_id: string
  seed: number
  current_month: number
  created_at: string
}

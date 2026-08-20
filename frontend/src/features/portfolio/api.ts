import { useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { useWorkspaceStore } from '@/stores/workspace-store'

export interface WorkspaceSummary {
  workspace_id: string
  label: string
  resilience_score: number | null
  survival_rate: number | null
  drift_alert: boolean
  last_run_at: string | null
}

export interface PortfolioSummary {
  portfolio_id: string
  name: string
  member_count: number
  workspaces: WorkspaceSummary[]
  avg_resilience_score: number | null
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export async function getPortfolioSummary(portfolioId: string): Promise<PortfolioSummary> {
  return apiFetch<PortfolioSummary>(`/api/v1/portfolios/${portfolioId}/summary`, {
    headers: workspaceHeaders(),
  })
}

export async function addWorkspace(
  portfolioId: string,
  workspaceId: string,
  label: string,
): Promise<void> {
  await apiFetch<void>(
    `/api/v1/portfolios/${portfolioId}/workspaces?workspace_id=${encodeURIComponent(workspaceId)}&label=${encodeURIComponent(label)}`,
    { method: 'POST', headers: workspaceHeaders() },
  )
}

export async function removeWorkspace(portfolioId: string, workspaceId: string): Promise<void> {
  await apiFetch<void>(`/api/v1/portfolios/${portfolioId}/workspaces/${workspaceId}`, {
    method: 'DELETE',
    headers: workspaceHeaders(),
  })
}

export function usePortfolioSummary(portfolioId: string | undefined) {
  return useQuery({
    queryKey: ['portfolio', portfolioId, 'summary'],
    queryFn: () => getPortfolioSummary(portfolioId ?? ''),
    enabled: Boolean(portfolioId),
  })
}

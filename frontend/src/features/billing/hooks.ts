import { useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { useWorkspaceStore } from '@/stores/workspace-store'

export interface UsageOut {
  tier: string
  period: string
  usage: {
    runs_used: number
    mc_ticks_used: number
    llm_tokens_used: number
  }
  limits: {
    runs_per_month: number
    monte_carlo_runs_per_batch: number
    llm_tokens_per_month: number
    seats: number
  }
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export function useUsage() {
  return useQuery({
    queryKey: ['billing', 'usage'],
    queryFn: () =>
      apiFetch<UsageOut>('/api/v1/billing/usage', {
        headers: workspaceHeaders(),
      }),
  })
}

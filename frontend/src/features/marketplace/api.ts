import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { useWorkspaceStore } from '@/stores/workspace-store'

export interface ScenarioSummary {
  id: string
  title: string
  description: string
  category: string
  clones_count: number
  is_featured: boolean
  created_at: string
}

export interface ScenarioDetail extends ScenarioSummary {
  payload: Record<string, unknown>
  author_workspace_id: string
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export function useScenarios(category?: string, page = 1) {
  return useQuery({
    queryKey: ['scenarios', category, page],
    queryFn: () => {
      const params = new URLSearchParams()
      if (category) params.set('category', category)
      params.set('page', String(page))
      return apiFetch<{ items: ScenarioSummary[]; total: number; page: number }>(
        `/api/v1/scenarios?${params}`,
      )
    },
  })
}

export function useFeaturedScenarios() {
  return useQuery({
    queryKey: ['scenarios', 'featured'],
    queryFn: () => apiFetch<ScenarioSummary[]>('/api/v1/scenarios/featured'),
  })
}

export function useScenario(id: string | undefined) {
  return useQuery({
    queryKey: ['scenario', id],
    queryFn: () => apiFetch<ScenarioDetail>(`/api/v1/scenarios/${id}`),
    enabled: Boolean(id),
  })
}

export function usePublishScenario() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      title: string
      description: string
      category: string
      blueprint_version_id: string
    }) =>
      apiFetch<ScenarioDetail>('/api/v1/scenarios', {
        method: 'POST',
        headers: workspaceHeaders(),
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['scenarios'] })
    },
  })
}

export function useCloneScenario() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<{ blueprint_id: string; blueprint_version_id: string }>(
        `/api/v1/scenarios/${id}/clone`,
        { method: 'POST', headers: workspaceHeaders() },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['blueprints'] })
      void queryClient.invalidateQueries({ queryKey: ['scenarios'] })
    },
  })
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { useWorkspaceStore } from '@/stores/workspace-store'

export interface ApiKeyOut {
  id: string
  name: string
  prefix: string
  scopes: string[]
  rate_limit_rpm: number
  last_used_at: string | null
  revoked_at: string | null
  created_at: string
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export function useApiKeys() {
  return useQuery({
    queryKey: ['api-keys'],
    queryFn: () => apiFetch<ApiKeyOut[]>('/api/v1/api-keys', { headers: workspaceHeaders() }),
  })
}

export function useCreateApiKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      name: string
      scopes: string[]
      rate_limit_rpm?: number
    }) =>
      apiFetch<{ id: string; name: string; prefix: string; scopes: string[]; key: string }>(
        '/api/v1/api-keys',
        { method: 'POST', headers: workspaceHeaders(), body: JSON.stringify(body) },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['api-keys'] })
    },
  })
}

export function useRevokeApiKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/api-keys/${id}`, {
        method: 'DELETE',
        headers: workspaceHeaders(),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['api-keys'] })
    },
  })
}

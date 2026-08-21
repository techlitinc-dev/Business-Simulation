import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { useWorkspaceStore } from '@/stores/workspace-store'

export type WebhookEvent = 'run.completed' | 'report.ready' | 'score.dropped'

export interface WebhookOut {
  id: string
  name: string
  target_url: string
  events: string[]
  active: boolean
  created_at: string
}

export interface WebhookCreated {
  id: string
  name: string
  target_url: string
  events: string[]
  secret: string
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export function useWebhooks() {
  return useQuery({
    queryKey: ['webhooks'],
    queryFn: () =>
      apiFetch<WebhookOut[]>('/api/v1/integrations/webhooks', {
        headers: workspaceHeaders(),
      }),
  })
}

export function useCreateWebhook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; target_url: string; events: WebhookEvent[] }) =>
      apiFetch<WebhookCreated>('/api/v1/integrations/webhooks', {
        method: 'POST',
        headers: workspaceHeaders(),
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['webhooks'] })
    },
  })
}

export function useDeleteWebhook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/integrations/webhooks/${id}`, {
        method: 'DELETE',
        headers: workspaceHeaders(),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['webhooks'] })
    },
  })
}

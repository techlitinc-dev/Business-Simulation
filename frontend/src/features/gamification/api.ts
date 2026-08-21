import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { API_URL } from '@/lib/constants'
import { toastError, toastSuccess } from '@/lib/toast'
import { useAuthStore } from '@/stores/auth-store'
import { useWorkspaceStore } from '@/stores/workspace-store'

export interface Achievement {
  id: string
  title: string
  description: string
  icon: string
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export function useAchievements() {
  return useQuery({
    queryKey: ['achievements'],
    queryFn: () =>
      apiFetch<Achievement[]>('/api/v1/gamification/achievements', {
        headers: workspaceHeaders(),
      }),
  })
}

export function useCertification(runId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (): Promise<void> => {
      const token = useAuthStore.getState().getAccessToken()
      const resp = await fetch(`${API_URL}/api/v1/gamification/certification/${runId}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token ?? ''}`,
          'X-Workspace-Id': useWorkspaceStore.getState().activeWorkspaceId ?? '',
        },
      })
      if (!resp.ok) {
        throw new Error(`Certification failed (${resp.status})`)
      }
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `certification_${runId}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    },
    onSuccess: () => {
      toastSuccess('Certification downloaded')
      void queryClient.invalidateQueries({ queryKey: ['achievements'] })
    },
    onError: (err: unknown) => {
      toastError(
        err instanceof Error ? err.message : 'Download failed',
        'Certification unavailable',
      )
    },
  })
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { WorkspaceOut } from '@/stores/workspace-store'
import { useWorkspaceStore } from '@/stores/workspace-store'

export interface MemberOut {
  user_id: string
  email: string
  name: string
  role: string
  joined_at: string
}

export interface InviteOut {
  id: string
  email: string
  role: string
  invite_url: string
  expires_at: string
}

export function useWorkspaces() {
  const setWorkspaces = useWorkspaceStore((s) => s.setWorkspaces)
  return useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => {
      const data = await apiFetch<WorkspaceOut[]>('/api/v1/workspaces')
      setWorkspaces(data)
      return data
    },
  })
}

export function useMembers(workspaceId: string | undefined) {
  return useQuery({
    queryKey: ['members', workspaceId],
    queryFn: () => apiFetch<MemberOut[]>(`/api/v1/workspaces/${workspaceId}/members`),
    enabled: Boolean(workspaceId),
  })
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient()
  const setActive = useWorkspaceStore((s) => s.setActive)
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<WorkspaceOut>('/api/v1/workspaces', {
        method: 'POST',
        body: JSON.stringify({ name }),
      }),
    onSuccess: (ws) => {
      setActive(ws.id)
      void queryClient.invalidateQueries({ queryKey: ['workspaces'] })
    },
  })
}

export function useUpdateMemberRole(workspaceId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      apiFetch<MemberOut>(`/api/v1/workspaces/${workspaceId}/members/${userId}`, {
        method: 'PATCH',
        body: JSON.stringify({ role }),
      }),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ['members', workspaceId] }),
  })
}

export function useRemoveMember(workspaceId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) =>
      apiFetch<void>(`/api/v1/workspaces/${workspaceId}/members/${userId}`, {
        method: 'DELETE',
      }),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ['members', workspaceId] }),
  })
}

export function useCreateInvite(workspaceId: string | undefined) {
  return useMutation({
    mutationFn: ({ email, role }: { email: string; role: string }) =>
      apiFetch<InviteOut>(`/api/v1/workspaces/${workspaceId}/invites`, {
        method: 'POST',
        body: JSON.stringify({ email, role }),
      }),
  })
}

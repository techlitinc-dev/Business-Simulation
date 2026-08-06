import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { toastError, toastSuccess } from '@/lib/toast'
import { useAuthStore, type UserOut } from '@/stores/auth-store'
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

export function useUpdateWorkspace(workspaceId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<WorkspaceOut>(`/api/v1/workspaces/${workspaceId}`, {
        method: 'PATCH',
        body: JSON.stringify({ name }),
      }),
    onSuccess: () => {
      toastSuccess('Workspace updated')
      void queryClient.invalidateQueries({ queryKey: ['workspaces'] })
    },
    onError: (err: unknown) => {
      toastError(
        err instanceof Error ? err.message : 'Could not update workspace',
        'Workspace update failed',
      )
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
    onSuccess: () => {
      toastSuccess('Role updated')
      void queryClient.invalidateQueries({ queryKey: ['members', workspaceId] })
    },
    onError: (err: unknown) => {
      toastError(
        err instanceof Error ? err.message : 'Could not update role',
        'Role update failed',
      )
    },
  })
}

export function useRemoveMember(workspaceId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) =>
      apiFetch<void>(`/api/v1/workspaces/${workspaceId}/members/${userId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      toastSuccess('Member removed')
      void queryClient.invalidateQueries({ queryKey: ['members', workspaceId] })
    },
    onError: (err: unknown) => {
      toastError(
        err instanceof Error ? err.message : 'Could not remove member',
        'Member removal failed',
      )
    },
  })
}

export function useCreateInvite(workspaceId: string | undefined) {
  return useMutation({
    mutationFn: ({ email, role }: { email: string; role: string }) =>
      apiFetch<InviteOut>(`/api/v1/workspaces/${workspaceId}/invites`, {
        method: 'POST',
        body: JSON.stringify({ email, role }),
      }),
    onSuccess: () => {
      toastSuccess('Invite created')
    },
    onError: (err: unknown) => {
      toastError(
        err instanceof Error ? err.message : 'Could not create invite',
        'Invite failed',
      )
    },
  })
}

/** Profile update — PATCH /users/me (T36 onboarding fields + name). */
export function useUpdateProfile() {
  const queryClient = useQueryClient()
  const setUser = useAuthStore((s) => s.setUser)
  return useMutation({
    mutationFn: (body: Partial<UserOut>) =>
      apiFetch<UserOut>('/api/v1/users/me', {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: (user) => {
      setUser(user)
      toastSuccess('Profile updated')
      void queryClient.invalidateQueries({ queryKey: ['me'] })
    },
    onError: (err: unknown) => {
      toastError(
        err instanceof Error ? err.message : 'Could not update profile',
        'Profile update failed',
      )
    },
  })
}

/** Password change — POST /users/me/password (T38). */
export function useChangePassword() {
  return useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) =>
      apiFetch<void>('/api/v1/users/me/password', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      toastSuccess('Password changed')
    },
    onError: (err: unknown) => {
      toastError(
        err instanceof Error ? err.message : 'Could not change password',
        'Password change failed',
      )
    },
  })
}

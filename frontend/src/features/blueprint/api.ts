import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { useWorkspaceStore } from '@/stores/workspace-store'
import type { BlueprintPayload, ValidationReport } from './types'

export interface BlueprintOut {
  id: string
  workspace_id: string
  name: string
  industry: string
  stage: string
  current_version: number
  created_at: string
  updated_at: string
}

export interface BlueprintDetail extends BlueprintOut {
  payload: BlueprintPayload
  vulnerabilities: unknown[]
}

export interface BlueprintVersionOut {
  id: string
  blueprint_id: string
  version: number
  payload: BlueprintPayload
  vulnerabilities: unknown[]
  created_at: string
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export function useBlueprints() {
  return useQuery({
    queryKey: ['blueprints'],
    queryFn: () => apiFetch<BlueprintOut[]>('/api/v1/blueprints', { headers: workspaceHeaders() }),
  })
}

export function useBlueprint(id: string | undefined) {
  return useQuery({
    queryKey: ['blueprint', id],
    queryFn: () => apiFetch<BlueprintDetail>(`/api/v1/blueprints/${id}`, { headers: workspaceHeaders() }),
    enabled: Boolean(id),
  })
}

export function useBlueprintValidation(id: string | undefined) {
  return useQuery({
    queryKey: ['blueprint', id, 'validate'],
    queryFn: () =>
      apiFetch<ValidationReport>(`/api/v1/blueprints/${id}/validate`, {
        headers: workspaceHeaders(),
      }),
    enabled: Boolean(id),
  })
}

export function useCreateBlueprint() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      name: string
      industry: string
      stage: string
      payload: BlueprintPayload
    }) =>
      apiFetch<BlueprintDetail>('/api/v1/blueprints', {
        method: 'POST',
        headers: workspaceHeaders(),
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['blueprints'] })
    },
  })
}

export function useAddVersion(blueprintId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: BlueprintPayload) =>
      apiFetch<BlueprintVersionOut>(`/api/v1/blueprints/${blueprintId}/versions`, {
        method: 'POST',
        headers: workspaceHeaders(),
        body: JSON.stringify({ payload }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['blueprint', blueprintId] })
      void queryClient.invalidateQueries({ queryKey: ['blueprint', blueprintId, 'validate'] })
      void queryClient.invalidateQueries({ queryKey: ['blueprints'] })
    },
  })
}

export function useDeleteBlueprint() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/blueprints/${id}`, {
        method: 'DELETE',
        headers: workspaceHeaders(),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['blueprints'] })
    },
  })
}

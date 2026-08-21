import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { toastError } from '@/lib/toast'
import { useWorkspaceStore } from '@/stores/workspace-store'

export type CommentTargetType = 'blueprint' | 'run' | 'report' | 'section'

export interface Comment {
  id: string
  body: string
  author_user_id: string
  created_at: string
}

export interface CommentInput {
  target_type: CommentTargetType
  target_id: string
  body: string
  mentions?: string[]
  section_ref?: string | null
}

export interface ApprovalRecord {
  id: string
  status: string
  decided_at: string | null
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export function useComments(targetType: string, targetId: string) {
  return useQuery({
    queryKey: ['comments', targetType, targetId],
    queryFn: () =>
      apiFetch<Comment[]>(`/api/v1/comments/${targetType}/${targetId}`, {
        headers: workspaceHeaders(),
      }),
    enabled: Boolean(targetType && targetId),
  })
}

export function usePostComment(targetType: CommentTargetType, targetId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: string) =>
      apiFetch<Comment>(`/api/v1/comments`, {
        method: 'POST',
        headers: workspaceHeaders(),
        body: JSON.stringify({
          target_type: targetType,
          target_id: targetId,
          body,
          mentions: extractMentions(body),
        } satisfies CommentInput),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['comments', targetType, targetId] })
    },
    onError: (err: unknown) => {
      toastError(
        err instanceof Error ? err.message : 'Failed to post comment',
        'Comment failed',
      )
    },
  })
}

export function useSubmitApproval() {
  return useMutation({
    mutationFn: (input: { target_type: string; target_id: string }) =>
      apiFetch<ApprovalRecord>('/api/v1/comments/approvals', {
        method: 'POST',
        headers: workspaceHeaders(),
        body: JSON.stringify(input),
      }),
  })
}

export function useDecideApproval() {
  return useMutation({
    mutationFn: (input: { approval_id: string; decision: 'approved' | 'rejected'; note?: string }) =>
      apiFetch<ApprovalRecord>(`/api/v1/comments/approvals/${input.approval_id}/decide`, {
        method: 'POST',
        headers: workspaceHeaders(),
        body: JSON.stringify({
          decision: input.decision,
          note: input.note ?? '',
        }),
      }),
  })
}

export function extractMentions(body: string): string[] {
  return [...body.matchAll(/@(\w+)/g)].map((m) => m[1])
}

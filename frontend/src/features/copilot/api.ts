import { apiFetch } from '@/lib/api-client'
import { useWorkspaceStore } from '@/stores/workspace-store'

export interface ChatResponse {
  answer: string
  sources_used: string[]
  confidence: 'LOW' | 'MEDIUM' | 'HIGH'
  grounded: boolean
  flagged_claims: string[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export async function sendCopilotMessage(
  runId: string,
  question: string,
  history: ChatMessage[] = [],
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>(`/api/v1/simulations/${runId}/chat`, {
    method: 'POST',
    headers: workspaceHeaders(),
    body: JSON.stringify({ question, history }),
  })
}

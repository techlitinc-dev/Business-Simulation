import { apiFetch } from '@/lib/api-client'
import { useWorkspaceStore } from '@/stores/workspace-store'

export interface PersonaReview {
  persona: 'CFO' | 'CMO' | 'RiskAuditor' | 'Operator'
  verdict: string
  top_concerns: string[]
  opportunities: string[]
  questions_for_founder: string[]
  confidence_level: 'LOW' | 'MEDIUM' | 'HIGH'
}

export interface BoardSummary {
  consensus_verdict: string
  points_of_agreement: string[]
  points_of_conflict: string[]
  top_priority_action: string
  overall_risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
}

export interface BoardReviewResult {
  reviews: PersonaReview[]
  summary: BoardSummary
}

export interface BoardReviewJob {
  job_id: string
  status: 'queued' | 'running' | 'complete' | 'error'
  result?: BoardReviewResult
  error?: string
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export async function requestBoardReview(
  blueprintId: string,
  runId?: string,
): Promise<{ job_id: string; status: string }> {
  const query = runId ? `?run_id=${encodeURIComponent(runId)}` : ''
  return apiFetch<{ job_id: string; status: string }>(
    `/api/v1/advisory/blueprints/${blueprintId}/board-review${query}`,
    { method: 'POST', headers: workspaceHeaders() },
  )
}

export async function getBoardReview(jobId: string): Promise<BoardReviewJob> {
  return apiFetch<BoardReviewJob>(`/api/v1/advisory/board-review/${jobId}`, {
    headers: workspaceHeaders(),
  })
}

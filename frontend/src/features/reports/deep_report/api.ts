import { useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { useWorkspaceStore } from '@/stores/workspace-store'

export interface DeepReportJob {
  job_id: string
  run_id: string
  status: 'queued' | 'in_progress' | 'completed' | 'failed'
  tier: string
  total_sections: number
  pdf_url: string | null
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

export async function requestDeepReport(runId: string): Promise<DeepReportJob> {
  return apiFetch<DeepReportJob>('/api/v1/reports/deep-dive', {
    method: 'POST',
    headers: workspaceHeaders(),
    body: JSON.stringify({ run_id: runId }),
  })
}

export async function getReportStatus(jobId: string): Promise<DeepReportJob> {
  return apiFetch<DeepReportJob>(`/api/v1/reports/deep-dive/${jobId}/status`, {
    headers: workspaceHeaders(),
  })
}

export function getDownloadUrl(jobId: string): string {
  return `/api/v1/reports/deep-dive/${jobId}/download`
}

/** Poll the job status until it reaches a terminal state. */
export function useDeepReportStatus(jobId: string | undefined) {
  return useQuery({
    queryKey: ['deep-report', jobId, 'status'],
    queryFn: () => getReportStatus(jobId ?? ''),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'in_progress' || status === 'queued' ? 2000 : false
    },
  })
}

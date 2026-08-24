import { useQuery } from '@tanstack/react-query'

import { apiFetch, ApiError } from '@/lib/api-client'
import { API_URL } from '@/lib/constants'
import { useAuthStore } from '@/stores/auth-store'
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

/**
 * Fetch the report PDF bytes with the same Bearer + workspace auth the API
 * requires. A plain `<a href>/<iframe src>` navigation only sends cookies —
 * never the Authorization/X-Workspace-Id headers — so it gets a 401. We fetch
 * the bytes here and hand back a blob, which the download link and viewer
 * render via a same-origin object URL (also sidestepping the X-Frame-Options
 * header on the raw response).
 */
export async function fetchReportPdf(jobId: string): Promise<Blob> {
  const headers: Record<string, string> = workspaceHeaders()
  const token = useAuthStore.getState().getAccessToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const resp = await fetch(`${API_URL}${getDownloadUrl(jobId)}`, { headers })
  if (!resp.ok) {
    throw new ApiError(resp.status, resp.statusText)
  }
  return resp.blob()
}

/** Poll the job status until it reaches a terminal state. */
export function useDeepReportStatus(jobId: string | undefined) {
  return useQuery({
    queryKey: ['deep-report', jobId, 'status'],
    queryFn: () => getReportStatus(jobId ?? ''),
    enabled: Boolean(jobId),
    // A missing/failed job is expected and terminal — don't re-fetch and spam
    // the console with repeated 404s; the UI renders the error state instead.
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'in_progress' || status === 'queued' ? 2000 : false
    },
  })
}

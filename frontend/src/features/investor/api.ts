import { apiFetch } from '@/lib/api-client'
import { useAuthStore } from '@/stores/auth-store'
import { useWorkspaceStore } from '@/stores/workspace-store'
import { API_URL } from '@/lib/constants'

export interface DataRoom {
  token: string
  download_url: string
  expires_at: string
  label: string
}

function workspaceHeaders(): Record<string, string> {
  const id = useWorkspaceStore.getState().activeWorkspaceId
  return id ? { 'X-Workspace-Id': id } : {}
}

/** Fetch a binary (PDF/ZIP) with auth + workspace headers — apiFetch parses JSON. */
async function fetchBlob(path: string, init: RequestInit = {}): Promise<Blob> {
  const token = useAuthStore.getState().getAccessToken()
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string>),
    ...workspaceHeaders(),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const resp = await fetch(`${API_URL}${path}`, { ...init, headers })
  if (!resp.ok) throw new Error(`Request failed: ${resp.status}`)
  return resp.blob()
}

export async function generateTeaser(runId: string): Promise<Blob> {
  return fetchBlob(`/api/v1/investor/runs/${runId}/teaser`, { method: 'POST' })
}

export async function generatePitchDeck(runId: string): Promise<Blob> {
  return fetchBlob(`/api/v1/investor/runs/${runId}/pitch-deck`, { method: 'POST' })
}

export async function createDataRoom(
  runId: string,
  label: string,
  expiryDays = 7,
): Promise<DataRoom> {
  return apiFetch<DataRoom>('/api/v1/dataroom/', {
    method: 'POST',
    headers: workspaceHeaders(),
    body: JSON.stringify({ run_id: runId, label, expiry_days: expiryDays }),
  })
}

export async function revokeDataRoom(token: string): Promise<void> {
  await apiFetch<void>(`/api/v1/dataroom/${token}`, {
    method: 'DELETE',
    headers: workspaceHeaders(),
  })
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

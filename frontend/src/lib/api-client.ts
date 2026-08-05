import { API_URL } from './constants'
import { useAuthStore } from '@/stores/auth-store'

/**
 * Typed fetch wrapper with Bearer auth and a single transparent token-refresh
 * attempt on 401. Never sends the token to /auth/* endpoints.
 */
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

interface ApiRequestInit extends RequestInit {
  skipAuth?: boolean
}

const AUTH_PATHS = ['/api/v1/auth/login', '/api/v1/auth/register', '/api/v1/auth/refresh']

async function refreshTokens(): Promise<boolean> {
  const refreshToken = useAuthStore.getState().getRefreshToken()
  if (!refreshToken) return false
  try {
    const resp = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!resp.ok) return false
    const pair = (await resp.json()) as {
      access_token: string
      refresh_token: string
      token_type: string
    }
    useAuthStore.getState().setTokens(pair)
    return true
  } catch {
    return false
  }
}

async function doFetch<T>(path: string, init: RequestInit): Promise<T> {
  const resp = await fetch(`${API_URL}${path}`, init)

  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const body = (await resp.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new ApiError(resp.status, detail)
  }

  return (await resp.json()) as T
}

export async function apiFetch<T>(
  path: string,
  init: ApiRequestInit = {},
): Promise<T> {
  const skipAuth = init.skipAuth ?? AUTH_PATHS.includes(path)
  const token = useAuthStore.getState().getAccessToken()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((init.headers as Record<string, string>) ?? {}),
  }
  if (!skipAuth && token) headers['Authorization'] = `Bearer ${token}`

  const request: RequestInit = { ...init, headers }

  try {
    return await doFetch<T>(path, request)
  } catch (err) {
    // One transparent refresh attempt on 401 for non-auth endpoints.
    if (
      err instanceof ApiError &&
      err.status === 401 &&
      !skipAuth &&
      !path.includes('/api/v1/auth/')
    ) {
      const refreshed = await refreshTokens()
      if (refreshed) {
        const newToken = useAuthStore.getState().getAccessToken()
        request.headers = {
          ...request.headers,
          Authorization: `Bearer ${newToken}`,
        }
        return await doFetch<T>(path, request)
      }
      // Refresh failed — log out and redirect to /login.
      useAuthStore.getState().logout()
      if (typeof window !== 'undefined') {
        const from = window.location.pathname + window.location.search
        window.location.href = `/login?from=${encodeURIComponent(from)}`
      }
    }
    throw err
  }
}

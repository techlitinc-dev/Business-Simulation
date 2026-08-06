import { create } from 'zustand'

import { apiFetch } from '@/lib/api-client'

export interface UserOut {
  id: string
  email: string
  name: string
  is_verified: boolean
  industry: string | null
  stage: string | null
  primary_fear: string | null
  onboarding_completed: boolean
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

const ACCESS_KEY = 'forge.access_token'
const REFRESH_KEY = 'forge.refresh_token'
const USER_KEY = 'forge.user'

interface AuthState {
  user: UserOut | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  setTokens: (pair: TokenPair) => void
  setUser: (user: UserOut | null) => void
  login: (email: string, password: string) => Promise<void>
  register: (email: string, name: string, password: string) => Promise<void>
  loadMe: () => Promise<void>
  logout: () => void
  getAccessToken: () => string | null
  getRefreshToken: () => string | null
}

function readStoredUser(): UserOut | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as UserOut) : null
  } catch {
    return null
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: readStoredUser(),
  accessToken: localStorage.getItem(ACCESS_KEY),
  refreshToken: localStorage.getItem(REFRESH_KEY),
  isAuthenticated: Boolean(localStorage.getItem(ACCESS_KEY)),

  setTokens: (pair) => {
    localStorage.setItem(ACCESS_KEY, pair.access_token)
    localStorage.setItem(REFRESH_KEY, pair.refresh_token)
    set({
      accessToken: pair.access_token,
      refreshToken: pair.refresh_token,
      isAuthenticated: true,
    })
  },

  setUser: (user) => {
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
    else localStorage.removeItem(USER_KEY)
    set({ user })
  },

  login: async (email, password) => {
    const pair = await apiFetch<TokenPair>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
      skipAuth: true,
    } as RequestInit & { skipAuth?: boolean })
    get().setTokens(pair)
    await get().loadMe()
  },

  register: async (email, name, password) => {
    await apiFetch<UserOut>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, name, password }),
      skipAuth: true,
    } as RequestInit & { skipAuth?: boolean })
  },

  loadMe: async () => {
    const user = await apiFetch<UserOut>('/api/v1/users/me')
    get().setUser(user)
  },

  logout: () => {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(USER_KEY)
    set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
  },

  getAccessToken: () => get().accessToken,
  getRefreshToken: () => get().refreshToken,
}))

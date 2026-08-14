import { useEffect } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuthStore } from '@/stores/auth-store'

export default function ProtectedRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const user = useAuthStore((s) => s.user)
  const accessToken = useAuthStore((s) => s.accessToken)
  const loadMe = useAuthStore((s) => s.loadMe)
  const location = useLocation()

  // Revalidate the user from the API on every app entry (e.g. after reload),
  // so stale cached data (old is_admin, renames, plan changes) is corrected.
  useEffect(() => {
    if (isAuthenticated && accessToken) {
      void loadMe().catch(() => {
        useAuthStore.getState().logout()
      })
    }
  }, [isAuthenticated, accessToken, loadMe])

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }

  // Loading state while rehydrating the user from the API.
  if (!user && accessToken) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    )
  }

  return <Outlet />
}

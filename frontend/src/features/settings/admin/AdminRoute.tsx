import { Navigate } from 'react-router-dom'

import { useAuthStore } from '@/stores/auth-store'

/** Redirects non-admins away from the admin section (T46). */
export default function AdminRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (user && !user.is_admin) {
    return <Navigate to="/app" replace />
  }
  return <>{children}</>
}

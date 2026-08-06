import { Navigate } from 'react-router-dom'

import { useAuthStore } from '@/stores/auth-store'
import { hasSkippedOnboarding } from './OnboardingWizard'

interface RequireOnboardingProps {
  children: React.ReactNode
}

/** Redirects authenticated users who haven't finished onboarding to /onboarding. */
export default function RequireOnboarding({ children }: RequireOnboardingProps) {
  const user = useAuthStore((s) => s.user)

  if (user && !user.onboarding_completed && !hasSkippedOnboarding()) {
    return <Navigate to="/onboarding" replace />
  }

  return <>{children}</>
}

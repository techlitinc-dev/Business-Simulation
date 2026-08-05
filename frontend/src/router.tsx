import { createBrowserRouter } from 'react-router-dom'

import AppShell from '@/components/layout/AppShell'
import DashboardPage from '@/features/dashboard/DashboardPage'
import AcceptInvitePage from '@/features/auth/AcceptInvitePage'
import LoginPage from '@/features/auth/LoginPage'
import ProtectedRoute from '@/features/auth/ProtectedRoute'
import RegisterPage from '@/features/auth/RegisterPage'
import ComingSoonPage from '@/features/marketing/ComingSoonPage'
import LandingPage from '@/features/marketing/LandingPage'
import MembersPage from '@/features/settings/MembersPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <LandingPage />,
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/accept-invite',
        element: <AcceptInvitePage />,
      },
      {
        path: '/app',
        element: <AppShell />,
        children: [
          {
            index: true,
            element: <DashboardPage />,
          },
          {
            path: 'blueprints',
            element: <ComingSoonPage title="Blueprints" />,
          },
          {
            path: 'simulations',
            element: <ComingSoonPage title="Simulations" />,
          },
          {
            path: 'reports',
            element: <ComingSoonPage title="Reports" />,
          },
          {
            path: 'settings',
            element: <ComingSoonPage title="Settings" />,
          },
          {
            path: 'settings/members',
            element: <MembersPage />,
          },
          {
            path: '*',
            element: <ComingSoonPage title="Page not found" />,
          },
        ],
      },
    ],
  },
])

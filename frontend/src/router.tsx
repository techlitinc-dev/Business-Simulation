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
import BlueprintDetailPage from '@/features/blueprint/BlueprintDetailPage'
import BlueprintEditPage from '@/features/blueprint/BlueprintEditPage'
import BlueprintListPage from '@/features/blueprint/BlueprintListPage'
import BlueprintCanvasPage from '@/features/blueprint/CanvasView'
import BuilderWizard from '@/features/blueprint/BuilderWizard'
import SimulationListPage from '@/features/simulation/SimulationListPage'
import RunnerPage from '@/features/simulation/RunnerPage'

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
            element: <BlueprintListPage />,
          },
          {
            path: 'blueprints/new',
            element: <BuilderWizard />,
          },
          {
            path: 'blueprints/:blueprintId',
            element: <BlueprintDetailPage />,
          },
          {
            path: 'blueprints/:blueprintId/edit',
            element: <BlueprintEditPage />,
          },
          {
            path: 'blueprints/:blueprintId/canvas',
            element: <BlueprintCanvasPage />,
          },
          {
            path: 'simulations',
            element: <SimulationListPage />,
          },
          {
            path: 'simulations/:runId',
            element: <RunnerPage />,
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

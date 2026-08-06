import { createBrowserRouter } from 'react-router-dom'

import AppShell from '@/components/layout/AppShell'
import PageTransition from '@/components/layout/PageTransition'
import RequireOnboarding from '@/features/onboarding/RequireOnboarding'
import OnboardingWizard from '@/features/onboarding/OnboardingWizard'
import DashboardPage from '@/features/dashboard/DashboardPage'
import AcceptInvitePage from '@/features/auth/AcceptInvitePage'
import LoginPage from '@/features/auth/LoginPage'
import ProtectedRoute from '@/features/auth/ProtectedRoute'
import RegisterPage from '@/features/auth/RegisterPage'
import ComingSoonPage from '@/features/marketing/ComingSoonPage'
import LandingPage from '@/features/marketing/LandingPage'
import MarketingLayout from '@/features/marketing/MarketingLayout'
import PricingPage from '@/features/marketing/PricingPage'
import MembersPage from '@/features/settings/MembersPage'
import ProfilePage from '@/features/settings/ProfilePage'
import SecurityPage from '@/features/settings/SecurityPage'
import SettingsLayout from '@/features/settings/SettingsLayout'
import WorkspacePage from '@/features/settings/WorkspacePage'
import BlueprintDetailPage from '@/features/blueprint/BlueprintDetailPage'
import BlueprintEditPage from '@/features/blueprint/BlueprintEditPage'
import BlueprintListPage from '@/features/blueprint/BlueprintListPage'
import BlueprintCanvasPage from '@/features/blueprint/CanvasView'
import BuilderWizard from '@/features/blueprint/BuilderWizard'
import SimulationListPage from '@/features/simulation/SimulationListPage'
import RunnerPage from '@/features/simulation/RunnerPage'
import ReportPage from '@/features/reports/ReportPage'
import ReportsListPage from '@/features/reports/ReportsListPage'
import SharedReportPage from '@/features/reports/SharedReportPage'
import CompareRoute from '@/features/reports/CompareRoute'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <MarketingLayout />,
    children: [
      { index: true, element: <LandingPage /> },
      { path: 'pricing', element: <PricingPage /> },
    ],
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
    path: '/reports/shared/:token',
    element: <SharedReportPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/onboarding',
        element: <OnboardingWizard />,
      },
      {
        path: '/accept-invite',
        element: <AcceptInvitePage />,
      },
      {
        path: '/app',
        element: (
          <RequireOnboarding>
            <AppShell />
          </RequireOnboarding>
        ),
        children: [
          {
            path: '/app',
            element: <PageTransition />,
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
                path: 'simulations/:runId/report',
                element: <ReportPage />,
              },
              {
                path: 'reports',
                element: <ReportsListPage />,
              },
              {
                path: 'reports/compare',
                element: <CompareRoute />,
              },
              {
                path: 'settings',
                element: <SettingsLayout />,
                children: [
                  { index: true, element: <ProfilePage /> },
                  { path: 'profile', element: <ProfilePage /> },
                  { path: 'workspace', element: <WorkspacePage /> },
                  { path: 'members', element: <MembersPage /> },
                  { path: 'security', element: <SecurityPage /> },
                ],
              },
              {
                path: '*',
                element: <ComingSoonPage title="Page not found" />,
              },
            ],
          },
        ],
      },
    ],
  },
])

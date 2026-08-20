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
import MarketplacePage from '@/features/marketplace/MarketplacePage'
import ScenarioDetailPage from '@/features/marketplace/ScenarioDetailPage'
import LeaderboardPage from '@/features/leaderboard/LeaderboardPage'
import BillingPage from '@/features/billing/BillingPage'
import MembersPage from '@/features/settings/MembersPage'
import ProfilePage from '@/features/settings/ProfilePage'
import SecurityPage from '@/features/settings/SecurityPage'
import SettingsLayout from '@/features/settings/SettingsLayout'
import WorkspacePage from '@/features/settings/WorkspacePage'
import ApiKeysPanel from '@/features/settings/ApiKeysPanel'
import AdminRoute from '@/features/settings/admin/AdminRoute'
import AdminDashboardPage from '@/features/settings/admin/AdminDashboardPage'
import AdminUsersPage from '@/features/settings/admin/AdminUsersPage'
import AdminWorkspacesPage from '@/features/settings/admin/AdminWorkspacesPage'
import BlueprintDetailPage from '@/features/blueprint/BlueprintDetailPage'
import BlueprintEditPage from '@/features/blueprint/BlueprintEditPage'
import BlueprintListPage from '@/features/blueprint/BlueprintListPage'
import BlueprintCanvasPage from '@/features/blueprint/CanvasView'
import BuilderWizard from '@/features/blueprint/BuilderWizard'
import WhatIfLabRoute from '@/features/whatif/WhatIfLabRoute'
import ActualsRoute from '@/features/actuals/ActualsRoute'
import PortfolioRoute from '@/features/portfolio/PortfolioRoute'
import SimulationListPage from '@/features/simulation/SimulationListPage'
import RunnerPage from '@/features/simulation/RunnerPage'
import GhostSetupPage from '@/features/ghost/GhostSetupPage'
import GhostSpectatorPage from '@/features/ghost/GhostSpectatorPage'
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
      { path: 'marketplace', element: <MarketplacePage /> },
      { path: 'marketplace/:scenarioId', element: <ScenarioDetailPage /> },
      { path: 'leaderboard', element: <LeaderboardPage /> },
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
    path: '/shared/reports/:token',
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
                path: 'blueprints/:blueprintId/whatif',
                element: <WhatIfLabRoute />,
              },
              {
                path: 'blueprints/:blueprintId/actuals',
                element: <ActualsRoute />,
              },
              {
                path: 'portfolio/:portfolioId',
                element: <PortfolioRoute />,
              },
              {
                path: 'simulations',
                element: <SimulationListPage />,
              },
              {
                path: 'simulations/ghost',
                element: <GhostSetupPage />,
              },
              {
                path: 'simulations/ghost/:runId',
                element: <GhostSpectatorPage />,
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
                path: 'ghost',
                element: <GhostSetupPage />,
              },
              {
                path: 'marketplace',
                element: <MarketplacePage />,
              },
              {
                path: 'marketplace/:scenarioId',
                element: <ScenarioDetailPage />,
              },
              {
                path: 'leaderboard',
                element: <LeaderboardPage />,
              },
              {
                path: 'billing',
                element: <BillingPage />,
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
                  { path: 'api-keys', element: <ApiKeysPanel /> },
                ],
              },
              {
                path: 'admin',
                element: (
                  <AdminRoute>
                    <SettingsLayout />
                  </AdminRoute>
                ),
                children: [
                  { index: true, element: <AdminDashboardPage /> },
                  { path: 'users', element: <AdminUsersPage /> },
                  { path: 'workspaces', element: <AdminWorkspacesPage /> },
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

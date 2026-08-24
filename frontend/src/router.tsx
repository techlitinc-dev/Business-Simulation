import { Suspense, lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'

import AppShell from '@/components/layout/AppShell'
import PageTransition from '@/components/layout/PageTransition'
import RequireOnboarding from '@/features/onboarding/RequireOnboarding'
import ProtectedRoute from '@/features/auth/ProtectedRoute'
import ComingSoonPage from '@/features/marketing/ComingSoonPage'
import MarketingLayout from '@/features/marketing/MarketingLayout'
import SettingsLayout from '@/features/settings/SettingsLayout'
import AdminRoute from '@/features/settings/admin/AdminRoute'

// Route-level code splitting: each feature page is loaded on demand so the
// initial bundle stays small and heavy screens (canvas, charts, reports)
// only download when the user actually visits them.
function withSuspense(Component: React.LazyExoticComponent<React.ComponentType<unknown>>) {
  return (
    <Suspense fallback={<div className="p-8 text-slate-400 animate-pulse">Loading…</div>}>
      <Component />
    </Suspense>
  )
}

const LoginPage = lazy(() => import('@/features/auth/LoginPage'))
const RegisterPage = lazy(() => import('@/features/auth/RegisterPage'))
const AcceptInvitePage = lazy(() => import('@/features/auth/AcceptInvitePage'))
const OnboardingWizard = lazy(() => import('@/features/onboarding/OnboardingWizard'))
const DashboardPage = lazy(() => import('@/features/dashboard/DashboardPage'))
const BlueprintListPage = lazy(() => import('@/features/blueprint/BlueprintListPage'))
const BuilderWizard = lazy(() => import('@/features/blueprint/BuilderWizard'))
const BlueprintDetailPage = lazy(() => import('@/features/blueprint/BlueprintDetailPage'))
const BlueprintEditPage = lazy(() => import('@/features/blueprint/BlueprintEditPage'))
const BlueprintCanvasPage = lazy(() => import('@/features/blueprint/CanvasView'))
const WhatIfLabRoute = lazy(() => import('@/features/whatif/WhatIfLabRoute'))
const ActualsRoute = lazy(() => import('@/features/actuals/ActualsRoute'))
const PortfolioRoute = lazy(() => import('@/features/portfolio/PortfolioRoute'))
const SimulationListPage = lazy(() => import('@/features/simulation/SimulationListPage'))
const RunnerPage = lazy(() => import('@/features/simulation/RunnerPage'))
const DecisionJournalPage = lazy(() =>
  import('@/features/journal/DecisionJournalPage').then((m) => ({
    default: m.DecisionJournalPage,
  })),
)
const GhostSetupPage = lazy(() => import('@/features/ghost/GhostSetupPage'))
const GhostSpectatorPage = lazy(() => import('@/features/ghost/GhostSpectatorPage'))
const ReportPage = lazy(() => import('@/features/reports/ReportPage'))
const ReportsListPage = lazy(() => import('@/features/reports/ReportsListPage'))
const SharedReportPage = lazy(() => import('@/features/reports/SharedReportPage'))
const CompareRoute = lazy(() => import('@/features/reports/CompareRoute'))
const LandingPage = lazy(() => import('@/features/marketing/LandingPage'))
const PricingPage = lazy(() => import('@/features/marketing/PricingPage'))
const MarketplacePage = lazy(() => import('@/features/marketplace/MarketplacePage'))
const ScenarioDetailPage = lazy(() =>
  import('@/features/marketplace/ScenarioDetailPage'),
)
const LeaderboardPage = lazy(() => import('@/features/leaderboard/LeaderboardPage'))
const BillingPage = lazy(() => import('@/features/billing/BillingPage'))
const MembersPage = lazy(() => import('@/features/settings/MembersPage'))
const ProfilePage = lazy(() => import('@/features/settings/ProfilePage'))
const SecurityPage = lazy(() => import('@/features/settings/SecurityPage'))
const WorkspacePage = lazy(() => import('@/features/settings/WorkspacePage'))
const ApiKeysPanel = lazy(() => import('@/features/settings/ApiKeysPanel'))
const IntegrationsPage = lazy(() => import('@/features/settings/IntegrationsPage'))
const AdminDashboardPage = lazy(() =>
  import('@/features/settings/admin/AdminDashboardPage'),
)
const AdminUsersPage = lazy(() => import('@/features/settings/admin/AdminUsersPage'))
const AdminWorkspacesPage = lazy(() =>
  import('@/features/settings/admin/AdminWorkspacesPage'),
)

export const router = createBrowserRouter([
  {
    path: '/',
    element: <MarketingLayout />,
    children: [
      { index: true, element: withSuspense(LandingPage) },
      { path: 'pricing', element: withSuspense(PricingPage) },
      { path: 'marketplace', element: withSuspense(MarketplacePage) },
      { path: 'marketplace/:scenarioId', element: withSuspense(ScenarioDetailPage) },
      { path: 'leaderboard', element: withSuspense(LeaderboardPage) },
    ],
  },
  {
    path: '/login',
    element: withSuspense(LoginPage),
  },
  {
    path: '/register',
    element: withSuspense(RegisterPage),
  },
  {
    path: '/shared/reports/:token',
    element: withSuspense(SharedReportPage),
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/onboarding',
        element: withSuspense(OnboardingWizard),
      },
      {
        path: '/accept-invite',
        element: withSuspense(AcceptInvitePage),
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
                element: withSuspense(DashboardPage),
              },
              {
                path: 'blueprints',
                element: withSuspense(BlueprintListPage),
              },
              {
                path: 'blueprints/new',
                element: withSuspense(BuilderWizard),
              },
              {
                path: 'blueprints/:blueprintId',
                element: withSuspense(BlueprintDetailPage),
              },
              {
                path: 'blueprints/:blueprintId/edit',
                element: withSuspense(BlueprintEditPage),
              },
              {
                path: 'blueprints/:blueprintId/canvas',
                element: withSuspense(BlueprintCanvasPage),
              },
              {
                path: 'blueprints/:blueprintId/whatif',
                element: withSuspense(WhatIfLabRoute),
              },
              {
                path: 'blueprints/:blueprintId/actuals',
                element: withSuspense(ActualsRoute),
              },
              {
                path: 'portfolio/:portfolioId',
                element: withSuspense(PortfolioRoute),
              },
              {
                path: 'simulations',
                element: withSuspense(SimulationListPage),
              },
              {
                path: 'simulations/ghost',
                element: withSuspense(GhostSetupPage),
              },
              {
                path: 'simulations/ghost/:runId',
                element: withSuspense(GhostSpectatorPage),
              },
              {
                path: 'simulations/:runId',
                element: withSuspense(RunnerPage),
              },
              {
                path: 'simulations/:runId/report',
                element: withSuspense(ReportPage),
              },
              {
                path: 'simulations/:runId/journal',
                element: withSuspense(DecisionJournalPage),
              },
              {
                path: 'reports',
                element: withSuspense(ReportsListPage),
              },
              {
                path: 'reports/compare',
                element: withSuspense(CompareRoute),
              },
              {
                path: 'ghost',
                element: withSuspense(GhostSetupPage),
              },
              {
                path: 'marketplace',
                element: withSuspense(MarketplacePage),
              },
              {
                path: 'marketplace/:scenarioId',
                element: withSuspense(ScenarioDetailPage),
              },
              {
                path: 'leaderboard',
                element: withSuspense(LeaderboardPage),
              },
              {
                path: 'billing',
                element: withSuspense(BillingPage),
              },
              {
                path: 'settings',
                element: <SettingsLayout />,
                children: [
                  { index: true, element: withSuspense(ProfilePage) },
                  { path: 'profile', element: withSuspense(ProfilePage) },
                  { path: 'workspace', element: withSuspense(WorkspacePage) },
                  { path: 'members', element: withSuspense(MembersPage) },
                  { path: 'security', element: withSuspense(SecurityPage) },
                  { path: 'api-keys', element: withSuspense(ApiKeysPanel) },
                  { path: 'integrations', element: withSuspense(IntegrationsPage) },
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
                  { index: true, element: withSuspense(AdminDashboardPage) },
                  { path: 'users', element: withSuspense(AdminUsersPage) },
                  { path: 'workspaces', element: withSuspense(AdminWorkspacesPage) },
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

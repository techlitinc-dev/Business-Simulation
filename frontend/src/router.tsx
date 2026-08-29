import { Suspense } from 'react'
import { createBrowserRouter } from 'react-router-dom'

import { lazyWithRetry } from '@/lib/lazyWithRetry'
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

const LoginPage = lazyWithRetry(() => import('@/features/auth/LoginPage'))
const RegisterPage = lazyWithRetry(() => import('@/features/auth/RegisterPage'))
const AcceptInvitePage = lazyWithRetry(() => import('@/features/auth/AcceptInvitePage'))
const OnboardingWizard = lazyWithRetry(() => import('@/features/onboarding/OnboardingWizard'))
const DashboardPage = lazyWithRetry(() => import('@/features/dashboard/DashboardPage'))
const BlueprintListPage = lazyWithRetry(() => import('@/features/blueprint/BlueprintListPage'))
const BuilderWizard = lazyWithRetry(() => import('@/features/blueprint/BuilderWizard'))
const BlueprintDetailPage = lazyWithRetry(() => import('@/features/blueprint/BlueprintDetailPage'))
const BlueprintEditPage = lazyWithRetry(() => import('@/features/blueprint/BlueprintEditPage'))
const BlueprintCanvasPage = lazyWithRetry(() => import('@/features/blueprint/CanvasView'))
const WhatIfLabRoute = lazyWithRetry(() => import('@/features/whatif/WhatIfLabRoute'))
const ActualsRoute = lazyWithRetry(() => import('@/features/actuals/ActualsRoute'))
const PortfolioRoute = lazyWithRetry(() => import('@/features/portfolio/PortfolioRoute'))
const SimulationListPage = lazyWithRetry(() => import('@/features/simulation/SimulationListPage'))
const RunnerPage = lazyWithRetry(() => import('@/features/simulation/RunnerPage'))
const DecisionJournalPage = lazyWithRetry(() =>
  import('@/features/journal/DecisionJournalPage').then((m) => ({
    default: m.DecisionJournalPage,
  })),
)
const GhostSetupPage = lazyWithRetry(() => import('@/features/ghost/GhostSetupPage'))
const GhostSpectatorPage = lazyWithRetry(() => import('@/features/ghost/GhostSpectatorPage'))
const ReportPage = lazyWithRetry(() => import('@/features/reports/ReportPage'))
const ReportsListPage = lazyWithRetry(() => import('@/features/reports/ReportsListPage'))
const SharedReportPage = lazyWithRetry(() => import('@/features/reports/SharedReportPage'))
const CompareRoute = lazyWithRetry(() => import('@/features/reports/CompareRoute'))
const LandingPage = lazyWithRetry(() => import('@/features/marketing/LandingPage'))
const PricingPage = lazyWithRetry(() => import('@/features/marketing/PricingPage'))
const MarketplacePage = lazyWithRetry(() => import('@/features/marketplace/MarketplacePage'))
const ScenarioDetailPage = lazyWithRetry(() =>
  import('@/features/marketplace/ScenarioDetailPage'),
)
const LeaderboardPage = lazyWithRetry(() => import('@/features/leaderboard/LeaderboardPage'))
const BillingPage = lazyWithRetry(() => import('@/features/billing/BillingPage'))
const MembersPage = lazyWithRetry(() => import('@/features/settings/MembersPage'))
const ProfilePage = lazyWithRetry(() => import('@/features/settings/ProfilePage'))
const SecurityPage = lazyWithRetry(() => import('@/features/settings/SecurityPage'))
const WorkspacePage = lazyWithRetry(() => import('@/features/settings/WorkspacePage'))
const ApiKeysPanel = lazyWithRetry(() => import('@/features/settings/ApiKeysPanel'))
const IntegrationsPage = lazyWithRetry(() => import('@/features/settings/IntegrationsPage'))
const AdminDashboardPage = lazyWithRetry(() =>
  import('@/features/settings/admin/AdminDashboardPage'),
)
const AdminUsersPage = lazyWithRetry(() => import('@/features/settings/admin/AdminUsersPage'))
const AdminWorkspacesPage = lazyWithRetry(() =>
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

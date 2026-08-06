import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

import DashboardPage from '../DashboardPage'

const RUNS = [
  {
    id: 'run-1',
    workspace_id: 'ws-1',
    blueprint_version_id: 'bpv-1',
    mode: 'monte_carlo',
    status: 'completed',
    seed: 42,
    current_month: 12,
    config: {},
    result: {},
    progress: null,
    created_at: '2026-08-01T00:00:00Z',
    started_at: null,
    finished_at: '2026-08-01T00:01:00Z',
  },
  {
    id: 'run-2',
    workspace_id: 'ws-1',
    blueprint_version_id: 'bpv-1',
    mode: 'stress',
    status: 'completed',
    seed: 7,
    current_month: 8,
    config: {},
    result: {},
    progress: null,
    created_at: '2026-07-15T00:00:00Z',
    started_at: null,
    finished_at: '2026-07-15T00:01:00Z',
  },
]

const TICKS = [
  {
    id: 't1',
    run_id: 'run-1',
    month: 1,
    kpis: { cash_balance: 100000, mrr: 5000, burn_rate: 20000, runway_months: 5 },
  },
  {
    id: 't2',
    run_id: 'run-1',
    month: 2,
    kpis: { cash_balance: 90000, mrr: 6000, burn_rate: 18000, runway_months: 5 },
  },
]

const REPORT = {
  id: 'r1',
  run_id: 'run-1',
  type: 'resilience_audit',
  content_md: '# Report',
  content_json: {
    survival: {
      survival_rate: 0.8,
      runs_total: 100,
      runs_survived: 80,
      median_lifespan_months: 18,
      kill_vectors: [],
    },
    weaknesses: [],
    optimizations: [],
    counter_factual: { text: '', deltas: [] },
    blueprint_version: 1,
    resilience_score: 72,
  },
  pdf_path: null,
  created_at: '2026-08-01T00:01:00Z',
}

const handlers: Record<string, unknown> = {
  '/api/v1/simulations': RUNS,
  '/api/v1/simulations/run-1/ticks': TICKS,
  '/api/v1/reports/simulations/run-1/report': REPORT,
}

vi.mock('@/lib/api-client', () => ({
  apiFetch: vi.fn((path: string) => {
    const body = handlers[path]
    if (body === undefined) return Promise.reject(new Error('unexpected path: ' + path))
    return Promise.resolve(body)
  }),
}))

vi.mock('@/stores/workspace-store', () => ({
  useWorkspaceStore: Object.assign(
    () => ({
      activeWorkspaceId: 'ws-1',
      workspaces: [],
      activeWorkspace: () => null,
    }),
    { getState: () => ({ activeWorkspaceId: 'ws-1' }) },
  ),
}))

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DashboardPage', () => {
  it('renders KPI values from the latest tick', async () => {
    renderPage()
    expect(await screen.findByText('$90k')).toBeInTheDocument() // cash balance
    expect(screen.getByText('$6k')).toBeInTheDocument() // MRR
    expect(screen.getByText('$18k')).toBeInTheDocument() // burn rate
    expect(screen.getByText('5 mo')).toBeInTheDocument() // runway
  })

  it('renders the resilience gauge score from the report', async () => {
    renderPage()
    expect(await screen.findByText('72')).toBeInTheDocument()
    expect(screen.getByText('Resilient')).toBeInTheDocument()
  })

  it('renders recent runs table rows', async () => {
    renderPage()
    expect(await screen.findAllByText('Monte Carlo')).toHaveLength(2)
    expect(screen.getByText('Stress')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
  })

  it('shows the empty state when there are no runs', async () => {
    handlers['/api/v1/simulations'] = []
    renderPage()
    expect(
      await screen.findByText('Create your first blueprint'),
    ).toBeInTheDocument()
    handlers['/api/v1/simulations'] = RUNS
  })
})

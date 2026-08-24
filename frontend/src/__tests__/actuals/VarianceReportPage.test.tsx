import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { VarianceReportPage } from '@/features/actuals/VarianceReportPage'
import type { VarianceReport } from '@/features/actuals/api'

const { useVarianceReportMock } = vi.hoisted(() => ({
  useVarianceReportMock: vi.fn(),
}))

vi.mock('@/features/actuals/api', () => ({
  useVarianceReport: (...args: unknown[]) => useVarianceReportMock(...args),
}))

const REPORT: VarianceReport = {
  delta: {
    blueprint_id: 'bp_1',
    month: 3,
    prior_survival_rate: 0.6,
    new_survival_rate: 0.4,
    survival_delta: -0.2,
    prior_runway_median: 18,
    new_runway_median: 11,
    runway_delta: -7,
    prior_resilience_score: 62.0,
    new_resilience_score: 43.0,
    score_delta: -19.0,
    key_changes: ['churn_rate increased from 0.05 to 0.12'],
  },
  narrative: {
    headline: 'Resilience fell 19 points as churn doubled.',
    explanation:
      'After importing actuals through month 3, the re-baselined forecast worsened: survival went from 60% to 40% and median runway moved from 18.0 to 11.0 months. Resilience score changed from 62.0 to 43.0.',
    primary_driver: 'churn_rate increased from 0.05 to 0.12',
    outlook: 'Keep monitoring the same fields next month to confirm the trend.',
  },
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <VarianceReportPage blueprintId="bp_1" />
    </QueryClientProvider>,
  )
}

describe('VarianceReportPage', () => {
  beforeEach(() => {
    useVarianceReportMock.mockReset()
  })

  it('shows loading state', () => {
    useVarianceReportMock.mockReturnValue({ data: undefined, isLoading: true })
    renderPage()

    expect(screen.getByText(/Computing variance/)).toBeInTheDocument()
  })

  it('renders 3 metric cards on success', () => {
    useVarianceReportMock.mockReturnValue({ data: REPORT, isLoading: false })
    renderPage()

    expect(screen.getByText('Resilience Score')).toBeInTheDocument()
    expect(screen.getByText('Survival Rate')).toBeInTheDocument()
    expect(screen.getByText('Median Runway')).toBeInTheDocument()
    // Current values for each metric.
    expect(screen.getByText('43.0')).toBeInTheDocument()
    expect(screen.getByText('40%')).toBeInTheDocument()
    expect(screen.getByText('11mo')).toBeInTheDocument()
  })

  it('shows narrative headline', () => {
    useVarianceReportMock.mockReturnValue({ data: REPORT, isLoading: false })
    renderPage()

    expect(
      screen.getByText('Resilience fell 19 points as churn doubled.'),
    ).toBeInTheDocument()
    expect(screen.getByText(/After importing actuals through month 3/)).toBeInTheDocument()
    expect(screen.getByText(/Outlook: Keep monitoring/)).toBeInTheDocument()
  })

  it('shows "No variance data" when no actuals', () => {
    useVarianceReportMock.mockReturnValue({ data: undefined, isLoading: false })
    renderPage()

    expect(
      screen.getByText('No variance data available. Import actuals first.'),
    ).toBeInTheDocument()
  })
})

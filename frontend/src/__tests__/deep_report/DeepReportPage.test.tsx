import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { DeepReportPage } from '@/features/reports/deep_report/DeepReportPage'
import { useWorkspaceStore } from '@/stores/workspace-store'
import { ApiError } from '@/lib/api-client'

const { requestDeepReportMock, getReportStatusMock, fetchReportPdfMock } =
  vi.hoisted(() => ({
    requestDeepReportMock: vi.fn(),
    getReportStatusMock: vi.fn(),
    fetchReportPdfMock: vi.fn(),
  }))

vi.mock('@/features/reports/deep_report/api', () => ({
  requestDeepReport: (...args: unknown[]) => requestDeepReportMock(...args),
  getReportStatus: (...args: unknown[]) => getReportStatusMock(...args),
  getDownloadUrl: (jobId: string) => `/api/v1/reports/deep-dive/${jobId}/download`,
  fetchReportPdf: (...args: unknown[]) => fetchReportPdfMock(...args),
}))

vi.mock('@/features/reports/deep_report/SectionProgressFeed', () => ({
  SectionProgressFeed: (props: {
    jobId: string
    totalSections: number
    onComplete: () => void
  }) => (
    <div data-testid="progress-feed" data-job-id={props.jobId}>
      SectionProgressFeed ({props.totalSections} sections)
      <button onClick={props.onComplete}>complete-feed</button>
    </div>
  ),
}))

vi.mock('@/features/reports/deep_report/ReportViewer', () => ({
  ReportViewer: (props: { pdfUrl: string }) => (
    <iframe data-testid="report-viewer" src={props.pdfUrl} title="Deep-Dive Report" />
  ),
}))

const JOB = {
  job_id: 'dr_test123',
  run_id: 'run_1',
  status: 'queued',
  tier: 'pro',
  total_sections: 13,
  pdf_url: null,
} as const

const COMPLETE_JOB = { ...JOB, status: 'completed', pdf_url: '/download.pdf' } as const

function renderPage(runId = 'run_1') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <DeepReportPage runId={runId} />
    </QueryClientProvider>,
  )
}

function setPlanTier(tier: string) {
  useWorkspaceStore.getState().setWorkspaces([
    { id: 'ws_1', name: 'Test WS', slug: 'test-ws', plan_tier: tier, role: 'owner', benchmark_opt_in: true },
  ])
  useWorkspaceStore.getState().setActive('ws_1')
}

describe('DeepReportPage', () => {
  beforeEach(() => {
    requestDeepReportMock.mockReset()
    getReportStatusMock.mockReset()
    fetchReportPdfMock.mockReset()
    // jsdom doesn't implement object URLs; stub them so the blob path works.
    URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    URL.revokeObjectURL = vi.fn()
  })

  it('renders paywall for free plan', () => {
    setPlanTier('free')
    renderPage()

    expect(
      screen.getByRole('button', { name: 'Upgrade to Pro — $49/mo' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Generate Deep-Dive Report' }),
    ).not.toBeInTheDocument()
  })

  it('renders generate button for pro plan', () => {
    setPlanTier('pro')
    renderPage()

    expect(
      screen.getByRole('button', { name: 'Generate Deep-Dive Report' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Upgrade to Pro — $49/mo' }),
    ).not.toBeInTheDocument()
  })

  it('calls requestDeepReport on click', async () => {
    const user = userEvent.setup()
    setPlanTier('pro')
    requestDeepReportMock.mockResolvedValue(JOB)
    renderPage('run_abc123')

    await user.click(screen.getByRole('button', { name: 'Generate Deep-Dive Report' }))

    expect(requestDeepReportMock).toHaveBeenCalledWith('run_abc123')
  })

  it('shows error message on API failure', async () => {
    const user = userEvent.setup()
    setPlanTier('pro')
    requestDeepReportMock.mockRejectedValue(new ApiError(500, 'boom'))
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Generate Deep-Dive Report' }))

    expect(await screen.findByText('boom')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Generate Deep-Dive Report' }),
    ).toBeInTheDocument()
  })

  it('shows progress feed while generating', async () => {
    const user = userEvent.setup()
    setPlanTier('pro')
    requestDeepReportMock.mockResolvedValue(JOB)
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Generate Deep-Dive Report' }))

    const feed = await screen.findByTestId('progress-feed')
    expect(feed).toHaveAttribute('data-job-id', 'dr_test123')
    expect(
      screen.queryByRole('button', { name: 'Generate Deep-Dive Report' }),
    ).not.toBeInTheDocument()
  })

  it('shows download button on complete', async () => {
    const user = userEvent.setup()
    setPlanTier('pro')
    requestDeepReportMock.mockResolvedValue(JOB)
    getReportStatusMock.mockResolvedValue(COMPLETE_JOB)
    // The PDF is fetched with auth and rendered as a blob object URL (a raw
    // anchor/iframe navigation would get a 401 for the missing headers).
    fetchReportPdfMock.mockResolvedValue(
      new Blob(['%PDF-1.7'], { type: 'application/pdf' }),
    )
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Generate Deep-Dive Report' }))
    const feed = await screen.findByTestId('progress-feed')
    await user.click(within(feed).getByRole('button', { name: 'complete-feed' }))

    expect(await screen.findByText(/Report ready — 13 sections generated/)).toBeInTheDocument()
    expect(fetchReportPdfMock).toHaveBeenCalledWith('dr_test123')
    const link = screen.getByRole('link', { name: /Download PDF/ })
    expect(link).toHaveAttribute('href', expect.stringMatching(/^blob:/))
    expect(screen.getByTestId('report-viewer')).toHaveAttribute(
      'src',
      expect.stringMatching(/^blob:/),
    )
  })

  it('shows retry when the PDF blob fails to load', async () => {
    const user = userEvent.setup()
    setPlanTier('pro')
    requestDeepReportMock.mockResolvedValue(JOB)
    getReportStatusMock.mockResolvedValue(COMPLETE_JOB)
    fetchReportPdfMock.mockRejectedValue(new ApiError(401, 'Not authenticated'))
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Generate Deep-Dive Report' }))
    const feed = await screen.findByTestId('progress-feed')
    await user.click(within(feed).getByRole('button', { name: 'complete-feed' }))

    expect(
      await screen.findByRole('button', { name: 'Retry loading PDF' }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Download PDF/ })).not.toBeInTheDocument()
  })
})

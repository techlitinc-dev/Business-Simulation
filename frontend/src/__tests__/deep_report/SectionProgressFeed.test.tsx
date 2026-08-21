import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { SectionProgressFeed } from '@/features/reports/deep_report/SectionProgressFeed'

const { useChannelSocketMock, useDeepReportStatusMock } = vi.hoisted(() => ({
  useChannelSocketMock: vi.fn(),
  useDeepReportStatusMock: vi.fn(),
}))

vi.mock('@/lib/ws', () => ({
  useChannelSocket: (...args: unknown[]) => useChannelSocketMock(...args),
}))

vi.mock('@/features/reports/deep_report/api', () => ({
  useDeepReportStatus: (...args: unknown[]) => useDeepReportStatusMock(...args),
}))

function doneEvent(section: number) {
  return JSON.stringify({
    job_id: 'dr_test123',
    section,
    total: 13,
    status: 'done',
    section_title: `Section ${section}`,
  })
}

function Feed({ onComplete = vi.fn() }: { onComplete?: () => void }) {
  return (
    <SectionProgressFeed
      jobId="dr_test123"
      totalSections={13}
      onComplete={onComplete}
    />
  )
}

describe('SectionProgressFeed', () => {
  beforeEach(() => {
    useChannelSocketMock.mockReset()
    useDeepReportStatusMock.mockReset()
  })

  it('calculates progress percentage', async () => {
    // Simulate the socket delivering 5 "done" messages in sequence; the feed
    // accumulates them and shows 5/13 ≈ 38%.
    let lastMessage: string | null = null
    useChannelSocketMock.mockImplementation(() => ({
      lastMessage,
      connectionStatus: 'open',
    }))
    useDeepReportStatusMock.mockReturnValue({ data: undefined })
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const view = render(
      <QueryClientProvider client={qc}>
        <Feed />
      </QueryClientProvider>,
    )

    for (const section of [1, 2, 3, 4, 5]) {
      lastMessage = doneEvent(section)
      view.rerender(
        <QueryClientProvider client={qc}>
          <Feed />
        </QueryClientProvider>,
      )
    }

    expect(await screen.findByText('38%')).toBeInTheDocument()
  })

  it('calls onComplete when all sections done', async () => {
    const onComplete = vi.fn()
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    useChannelSocketMock.mockImplementation(() => ({
      lastMessage: doneEvent(13),
      connectionStatus: 'open',
    }))
    useDeepReportStatusMock.mockReturnValue({ data: undefined })
    render(
      <QueryClientProvider client={qc}>
        <Feed onComplete={onComplete} />
      </QueryClientProvider>,
    )

    const matches = await screen.findAllByText((_content, element) => {
      return element?.textContent?.includes('Writing section 13 of 13: Section 13') ?? false
    })
    expect(matches.length).toBeGreaterThan(0)
    // The component waits 800ms before firing onComplete.
    await vi.waitFor(() => expect(onComplete).toHaveBeenCalled(), { timeout: 3000 })
  })
})

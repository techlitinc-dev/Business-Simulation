import { act, fireEvent, render, screen } from '@testing-library/react'

import { AdvisoryBoardPanel } from '@/features/advisory/AdvisoryBoardPanel'
import { PersonaCard } from '@/features/advisory/PersonaCard'
import type { BoardReviewResult, PersonaReview } from '@/features/advisory/api'

const { requestBoardReviewMock, getBoardReviewMock } = vi.hoisted(() => ({
  requestBoardReviewMock: vi.fn(),
  getBoardReviewMock: vi.fn(),
}))

vi.mock('@/features/advisory/api', () => ({
  requestBoardReview: (...args: unknown[]) => requestBoardReviewMock(...args),
  getBoardReview: (...args: unknown[]) => getBoardReviewMock(...args),
}))

const REVIEW: PersonaReview = {
  persona: 'CFO',
  verdict: 'Runway is tight.',
  top_concerns: ['Cash burnout'],
  opportunities: ['Cut CAC'],
  questions_for_founder: ['What is the churn trend?'],
  confidence_level: 'MEDIUM',
}

const RESULT: BoardReviewResult = {
  reviews: [
    { ...REVIEW, persona: 'CFO' },
    { ...REVIEW, persona: 'CMO', verdict: 'Growth signals look weak.' },
    { ...REVIEW, persona: 'RiskAuditor', verdict: 'Concentration risk is high.' },
    { ...REVIEW, persona: 'Operator', verdict: 'Execution cadence is slowing.' },
  ],
  summary: {
    consensus_verdict: 'Runway is the binding constraint.',
    points_of_agreement: ['Extend runway', 'Fix unit economics'],
    points_of_conflict: ['Growth spend vs. profitability'],
    top_priority_action: 'Reduce burn before scaling',
    overall_risk_level: 'MEDIUM',
  },
}

describe('AdvisoryBoardPanel', () => {
  beforeEach(() => {
    requestBoardReviewMock.mockReset()
    getBoardReviewMock.mockReset()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows the "Get Advisory Board Review" button', () => {
    render(<AdvisoryBoardPanel blueprintId="bp_1" />)

    expect(
      screen.getByRole('button', { name: 'Get Advisory Board Review' }),
    ).toBeInTheDocument()
  })

  it('renders 4 persona cards after the result loads', async () => {
    requestBoardReviewMock.mockResolvedValue({ job_id: 'adv_test', status: 'queued' })
    getBoardReviewMock.mockResolvedValue({ status: 'complete', result: RESULT })
    render(<AdvisoryBoardPanel blueprintId="bp_1" />)

    fireEvent.click(
      screen.getByRole('button', { name: 'Get Advisory Board Review' }),
    )
    // Flush the panel's poll delay, which yields to the resolved getBoardReview.
    await act(() => vi.advanceTimersByTimeAsync(2000))

    expect(screen.getAllByTestId('persona-card')).toHaveLength(4)
    expect(
      screen.queryByRole('button', { name: 'Get Advisory Board Review' }),
    ).not.toBeInTheDocument()
  })
})

describe('PersonaCard', () => {
  it('renders the persona name in the heading', () => {
    render(<PersonaCard review={REVIEW} />)

    expect(screen.getByText('💼 CFO')).toBeInTheDocument()
  })
})
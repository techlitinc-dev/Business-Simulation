import * as React from 'react'
import { render, screen } from '@testing-library/react'

import { CohortChart } from '../CohortChart'

const { useCohortStatsMock } = vi.hoisted(() => ({ useCohortStatsMock: vi.fn() }))

vi.mock('../api', () => ({
  useCohortStats: (...args: unknown[]) => useCohortStatsMock(...args),
}))

// jsdom reports zero width/height for rendered SVG, so recharts'
// ResponsiveContainer measures 0px and renders nothing. Inject explicit
// dimensions into the chart the way ResponsiveContainer normally would.
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>()
  return {
    ...actual,
    ResponsiveContainer: ({
      children,
    }: {
      children: React.ReactElement
    }) => React.cloneElement(children, { width: 320, height: 144 }),
  }
})

beforeEach(() => {
  useCohortStatsMock.mockReset()
})

it('CohortChart renders the P25, P50, P75 and You bars', () => {
  useCohortStatsMock.mockReturnValue({
    data: {
      industry: 'saas',
      stage: 'b2b',
      sample_size: 42,
      survival_rate_p25: 40,
      survival_rate_p50: 55,
      survival_rate_p75: 70,
      resilience_score_p25: 35,
      resilience_score_p50: 52,
      resilience_score_p75: 68,
      median_lifespan_p50: 18,
      top_kill_vectors: ['churn'],
    },
  })
  render(<CohortChart score={61} industry="saas" stage="b2b" />)

  expect(screen.getByText('Cohort: 42 simulations')).toBeInTheDocument()
  for (const label of ['P25', 'P50', 'P75', 'You']) {
    expect(screen.getByText(label)).toBeInTheDocument()
  }
})
import { render, screen } from '@testing-library/react'

import { BenchmarkBadge } from '../BenchmarkBadge'

const { usePercentileMock } = vi.hoisted(() => ({ usePercentileMock: vi.fn() }))

vi.mock('../api', () => ({
  usePercentile: (...args: unknown[]) => usePercentileMock(...args),
}))

beforeEach(() => {
  usePercentileMock.mockReset()
})

it('BenchmarkBadge shows the percentile text when sample size is sufficient', () => {
  usePercentileMock.mockReturnValue({
    data: {
      score: 64,
      industry: 'saas',
      stage: 'b2b',
      percentile: 64,
      sample_size: 120,
      label: '64th percentile vs. B2B SaaS simulations',
    },
  })
  render(<BenchmarkBadge score={64} industry="saas" stage="b2b" />)

  expect(screen.getByText(/64th percentile/)).toBeInTheDocument()
  expect(screen.getByText(/B2B SaaS simulations/)).toBeInTheDocument()
})

it('BenchmarkBadge is hidden when the sample size is too small', () => {
  usePercentileMock.mockReturnValue({
    data: {
      score: 64,
      industry: 'saas',
      stage: null,
      percentile: 64,
      sample_size: 3,
      label: '64th percentile vs. saas simulations',
    },
  })
  render(<BenchmarkBadge score={64} industry="saas" />)

  expect(screen.queryByText(/percentile/)).not.toBeInTheDocument()
})
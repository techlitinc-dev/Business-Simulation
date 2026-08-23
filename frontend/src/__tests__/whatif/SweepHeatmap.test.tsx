import { render, screen } from '@testing-library/react'

import { SweepHeatmap } from '@/features/whatif/SweepHeatmap'
import type { SweepGridPoint } from '@/features/whatif/api'

const GRID: SweepGridPoint[] = [
  {
    param_value: 0.02,
    survival_rate: 0.9,
    median_runway: 24,
    p25_runway: 22,
    p75_runway: 24,
  },
  {
    param_value: 0.05,
    survival_rate: 0.65,
    median_runway: 20,
    p25_runway: 16,
    p75_runway: 24,
  },
  {
    param_value: 0.08,
    survival_rate: 0.4,
    median_runway: 15,
    p25_runway: 10,
    p75_runway: 20,
  },
  {
    param_value: 0.11,
    survival_rate: 0.15,
    median_runway: 10,
    p25_runway: 6,
    p75_runway: 16,
  },
]

describe('SweepHeatmap', () => {
  it('renders correct number of cells', () => {
    render(<SweepHeatmap grid={GRID} param="revenue_engine.streams.0.churn_monthly" />)

    // One cell per grid point, each showing its % label (legend items like
    // "≥80%" and "<20%" are excluded by anchoring on a bare percentage).
    const cells = screen.getAllByText(/^\d+%$/)
    expect(cells).toHaveLength(GRID.length)
    // Parameter name in the header.
    expect(screen.getByText(/Survival Rate vs/)).toBeInTheDocument()
    expect(screen.getByText(/revenue_engine\.streams\.0\.churn_monthly/)).toBeInTheDocument()
  })

  it('shows correct % labels', () => {
    render(<SweepHeatmap grid={GRID} param="price" />)

    expect(screen.getByText('90%')).toBeInTheDocument()
    expect(screen.getByText('65%')).toBeInTheDocument()
    expect(screen.getByText('40%')).toBeInTheDocument()
    expect(screen.getByText('15%')).toBeInTheDocument()
  })
})

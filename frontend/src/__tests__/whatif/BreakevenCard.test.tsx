import { render, screen } from '@testing-library/react'

import { BreakevenCard } from '@/features/whatif/BreakevenCard'
import type { BreakevenResult } from '@/features/whatif/api'

const RESULT: BreakevenResult = {
  blueprint_id: 'bp_1',
  param: 'revenue_engine.streams.0.churn_monthly',
  breakeven_value: 0.0616,
  survival_at_breakeven: 0.5,
  message:
    'Your model maintains ≥50% survival only if revenue_engine.streams.0.churn_monthly stays below 0.0616',
}

describe('BreakevenCard', () => {
  it('shows loading state', () => {
    render(<BreakevenCard result={null} loading />)

    expect(screen.getByText('Calculating break-even…')).toBeInTheDocument()
    expect(screen.queryByText('⚠️ Break-Even Threshold')).not.toBeInTheDocument()
  })

  it('shows threshold value and message', () => {
    render(<BreakevenCard result={RESULT} loading={false} />)

    expect(screen.getByText('⚠️ Break-Even Threshold')).toBeInTheDocument()
    expect(
      screen.getByText('revenue engine.streams.0.churn monthly = 0.0616'),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        'Your model maintains ≥50% survival only if revenue_engine.streams.0.churn_monthly stays below 0.0616',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText('Survival at breakeven: 50.0%')).toBeInTheDocument()
  })
})

import { fireEvent, render, screen } from '@testing-library/react'

import { CohortRankings } from '../CohortRankings'

const WS = [
  {
    workspace_id: 'ws_low',
    label: 'Company Low',
    resilience_score: 40,
    survival_rate: 0.45,
    drift_alert: false,
    last_run_at: null,
  },
  {
    workspace_id: 'ws_high',
    label: 'Company High',
    resilience_score: 88,
    survival_rate: 0.8,
    drift_alert: false,
    last_run_at: null,
  },
]

describe('CohortRankings', () => {
  it('renders sorted list with #1 as highest score', () => {
    render(<CohortRankings workspaces={WS} />)

    const rows = screen.getAllByText(/Company (Low|High)/)
    expect(rows[0]).toHaveTextContent('Company High')
    expect(screen.getByText('#1')).toBeInTheDocument()
  })

  it('anonymize toggle hides real names', () => {
    render(<CohortRankings workspaces={WS} />)
    expect(screen.getByText('Company High')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Anonymize' }))

    expect(screen.getByText('Company 1')).toBeInTheDocument()
    expect(screen.queryByText('Company High')).not.toBeInTheDocument()
    expect(screen.queryByText('Company Low')).not.toBeInTheDocument()
  })
})
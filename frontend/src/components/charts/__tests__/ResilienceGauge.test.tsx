import { render, screen } from '@testing-library/react'

import { ResilienceGauge } from '../ResilienceGauge'

describe('ResilienceGauge', () => {
  it('renders the score value', () => {
    render(<ResilienceGauge score={62} />)
    expect(screen.getByText('62')).toBeInTheDocument()
  })

  it('labels low scores as Fragile', () => {
    render(<ResilienceGauge score={25} />)
    expect(screen.getByText('Fragile')).toBeInTheDocument()
  })

  it('labels mid scores as At risk', () => {
    render(<ResilienceGauge score={55} />)
    expect(screen.getByText('At risk')).toBeInTheDocument()
  })

  it('labels high scores as Resilient', () => {
    render(<ResilienceGauge score={85} />)
    expect(screen.getByText('Resilient')).toBeInTheDocument()
  })
})

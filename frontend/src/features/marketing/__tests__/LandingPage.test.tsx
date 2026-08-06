import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import LandingPage from '../LandingPage'

function renderLanding() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/register" element={<div>Register Page</div>} />
        <Route path="/pricing" element={<div>Pricing Page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('LandingPage', () => {
  it('renders the hero headline and CTAs', () => {
    renderLanding()
    expect(
      screen.getByText(/digital wind tunnel/i),
    ).toBeInTheDocument()
    const startLinks = screen.getAllByRole('link', { name: /start simulating free/i })
    expect(startLinks.length).toBeGreaterThan(0)
    expect(startLinks[0]).toHaveAttribute('href', '/register')
    const pricing = screen.getByRole('link', { name: /see pricing/i })
    expect(pricing).toHaveAttribute('href', '/pricing')
  })

  it('renders the four how-it-works steps', () => {
    renderLanding()
    expect(screen.getByText('Build your blueprint')).toBeInTheDocument()
    expect(screen.getByText('Baseline run')).toBeInTheDocument()
    expect(screen.getByText('Stress test')).toBeInTheDocument()
    expect(screen.getByText('Resilience audit')).toBeInTheDocument()
  })

  it('renders feature cards', () => {
    renderLanding()
    expect(screen.getByText('Deterministic Engine')).toBeInTheDocument()
    expect(screen.getByText('AI Game Master')).toBeInTheDocument()
    expect(screen.getByText('Monte Carlo')).toBeInTheDocument()
    expect(screen.getByText('War Room')).toBeInTheDocument()
  })

  it('marks social proof as a placeholder', () => {
    renderLanding()
    expect(screen.getByTestId('social-proof-placeholder')).toBeInTheDocument()
  })
})

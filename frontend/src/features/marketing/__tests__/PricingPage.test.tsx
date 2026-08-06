import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { PLAN_TIERS } from '@/lib/constants'
import PricingPage from '../PricingPage'

function renderPricing() {
  return render(
    <MemoryRouter initialEntries={['/pricing']}>
      <Routes>
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/register" element={<div>Register Page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('PricingPage', () => {
  it('renders all tiers from PLAN_TIERS', () => {
    renderPricing()
    for (const tier of PLAN_TIERS) {
      expect(screen.getByText(tier.name)).toBeInTheDocument()
    }
  })

  it('tier CTA links carry the plan id', () => {
    renderPricing()
    const proCard = screen.getByText('Pro').closest('div') as HTMLElement
    const proCta = Array.from(proCard.querySelectorAll('a')).find((a) =>
      a.textContent?.includes('Get started'),
    )
    expect(proCta).toHaveAttribute('href', '/register?plan=pro')
  })

  it('marks the highlighted tier as most popular', () => {
    renderPricing()
    expect(screen.getByText('Most popular')).toBeInTheDocument()
  })

  it('toggles between monthly and yearly prices', async () => {
    const user = userEvent.setup()
    renderPricing()

    // Monthly default: Pro $49/mo.
    expect(screen.getByText('$49')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Yearly' }))
    expect(screen.getByText('$40')).toBeInTheDocument()
    expect(screen.queryByText('$49')).not.toBeInTheDocument()
  })
})

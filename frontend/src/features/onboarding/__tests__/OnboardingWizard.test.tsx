import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import OnboardingWizard from '../OnboardingWizard'

const { apiFetchMock } = vi.hoisted(() => ({
  apiFetchMock: vi.fn((path: string) => {
    if (path === '/api/v1/industry-packs') {
      return Promise.resolve([
        { id: 'saas', name: 'SaaS Pack', description: 'Pre-tuned for SaaS' },
      ])
    }
    return Promise.resolve({
      id: 'u1',
      email: 'a@b.co',
      name: 'A',
      is_verified: false,
      industry: 'saas',
      stage: 'Pre-Seed',
      primary_fear: 'My CAC is too high',
      onboarding_completed: true,
    })
  }),
}))

vi.mock('@/lib/api-client', () => ({
  apiFetch: (...args: Parameters<typeof apiFetchMock>) => apiFetchMock(...args),
}))

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: Object.assign(() => ({ setUser: vi.fn() }), {
    getState: () => ({ setUser: vi.fn() }),
  }),
}))

function renderWizard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/onboarding']}>
        <Routes>
          <Route path="/onboarding" element={<OnboardingWizard />} />
          <Route path="/" element={<div>Dashboard</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

async function goToStep2(user: ReturnType<typeof userEvent.setup>) {
  // Step 1: pack selector
  await screen.findByText('Pick a starting playbook')
  await user.click(await screen.findByText('SaaS Pack'))
  await user.click(screen.getByRole('button', { name: 'Next' }))
  await screen.findByText('What industry are you in?')
  await user.click(screen.getByText('SaaS'))
  await user.click(screen.getByRole('button', { name: 'Next' }))
  await screen.findByText('What stage are you at?')
}

async function goToStep3(user: ReturnType<typeof userEvent.setup>) {
  await goToStep2(user)
  await user.click(screen.getByText('Pre-Seed'))
  await user.click(screen.getByRole('button', { name: 'Next' }))
  await screen.findByText('What scares you most?')
}

describe('OnboardingWizard', () => {
  it('navigates through the four steps', async () => {
    const user = userEvent.setup()
    renderWizard()

    // Step 1: industry pack
    expect(await screen.findByText('Pick a starting playbook')).toBeInTheDocument()
    const next = screen.getByRole('button', { name: 'Next' })
    expect(next).toBeDisabled()
    await user.click(await screen.findByText('SaaS Pack'))
    expect(next).toBeEnabled()
    await user.click(next)

    // Step 2: industry
    expect(await screen.findByText('What industry are you in?')).toBeInTheDocument()
    const next2 = screen.getByRole('button', { name: 'Next' })
    expect(next2).toBeDisabled()
    await user.click(screen.getByText('SaaS'))
    await user.click(next2)

    // Step 3: stage
    expect(await screen.findByText('What stage are you at?')).toBeInTheDocument()
    const next3 = screen.getByRole('button', { name: 'Next' })
    expect(next3).toBeDisabled()
    await user.click(screen.getByText('Pre-Seed'))
    await user.click(next3)

    // Step 4: fear
    expect(await screen.findByText('What scares you most?')).toBeInTheDocument()
    const finish = screen.getByRole('button', { name: 'Finish' })
    expect(finish).toBeDisabled()
    await user.click(screen.getByText('CAC too high'))
    expect(finish).toBeEnabled()
  })

  it('blocks finish until the fear has 10+ characters', async () => {
    const user = userEvent.setup()
    renderWizard()
    await goToStep3(user)

    const finish = screen.getByRole('button', { name: 'Finish' })
    expect(finish).toBeDisabled()
    const textarea = screen.getByPlaceholderText(/worried my CAC/i)
    await user.type(textarea, 'short')
    expect(finish).toBeDisabled()
    await user.type(textarea, 'ter and longer')
    expect(finish).toBeEnabled()
  })

  it('submit calls api-client with the right body', async () => {
    const user = userEvent.setup()
    renderWizard()

    await goToStep3(user)
    await user.click(screen.getByText('CAC too high'))
    await user.click(screen.getByRole('button', { name: 'Finish' }))

    expect(apiFetchMock).toHaveBeenCalledWith(
      '/api/v1/users/me',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({
          industry: 'saas',
          stage: 'Pre-Seed',
          primary_fear: 'CAC too high',
        }),
      }),
    )
  })

  it('skip for now goes back to the dashboard', async () => {
    const user = userEvent.setup()
    renderWizard()
    await user.click(screen.getByRole('button', { name: 'Skip for now' }))
    expect(await screen.findByText('Dashboard')).toBeInTheDocument()
  })
})

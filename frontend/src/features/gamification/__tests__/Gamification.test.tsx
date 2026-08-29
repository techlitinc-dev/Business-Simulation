import { render, screen, waitFor } from '@testing-library/react'

import { AchievementToast } from '../AchievementToast'
import { CertificationBadge } from '../CertificationBadge'

const { useAchievementsMock, useCertificationMock, toastMock } = vi.hoisted(() => ({
  useAchievementsMock: vi.fn(),
  useCertificationMock: vi.fn(),
  toastMock: vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: { success: toastMock },
}))

vi.mock('../api', () => ({
  useAchievements: (...args: unknown[]) => useAchievementsMock(...args),
  useCertification: (...args: unknown[]) => useCertificationMock(...args),
}))

beforeEach(() => {
  useAchievementsMock.mockReset()
  useCertificationMock.mockReset()
  toastMock.mockReset()
  localStorage.clear()
})

describe('AchievementToast', () => {
  it('renders nothing and shows no toast when there are no achievements', () => {
    useAchievementsMock.mockReturnValue({ data: [] })
    render(<AchievementToast />)
    expect(toastMock).not.toHaveBeenCalled()
  })

  it('toasts a newly earned achievement once', async () => {
    useAchievementsMock.mockReturnValue({
      data: [
        {
          id: 'first_run',
          title: 'Simulation Pioneer',
          description: 'Completed your first simulation run',
          icon: '🚀',
        },
      ],
    })
    render(<AchievementToast />)

    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        '🚀 Simulation Pioneer',
        expect.objectContaining({
          description: 'Completed your first simulation run',
        }),
      )
    })
  })

  it('does not re-toast achievements already seen', async () => {
    localStorage.setItem(
      'forge:achievements-seen',
      JSON.stringify(['first_run']),
    )
    useAchievementsMock.mockReturnValue({
      data: [
        {
          id: 'first_run',
          title: 'Simulation Pioneer',
          description: 'Completed your first simulation run',
          icon: '🚀',
        },
      ],
    })
    render(<AchievementToast />)

    await waitFor(() => {
      expect(toastMock).not.toHaveBeenCalled()
    })
  })
})

describe('CertificationBadge', () => {
  it('shows the Forge-Validated Business badge with a download button', () => {
    useCertificationMock.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    })
    render(<CertificationBadge runId="run_123" />)

    expect(screen.getByText('Forge-Validated Business')).toBeInTheDocument()
    expect(screen.getByText(/Certificate PDF/)).toBeInTheDocument()
  })
})

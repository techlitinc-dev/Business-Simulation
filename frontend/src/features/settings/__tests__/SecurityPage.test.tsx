import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import SecurityPage from '../SecurityPage'

const apiFetch = vi.fn()

vi.mock('@/lib/api-client', () => ({
  apiFetch: (path: string, init?: RequestInit) => {
    apiFetch(path, init)
    return Promise.resolve()
  },
}))

vi.mock('@/lib/toast', () => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <SecurityPage />
    </QueryClientProvider>,
  )
}

describe('SecurityPage', () => {
  it('blocks submit when new password is too short or confirm mismatches', async () => {
    const user = userEvent.setup()
    renderPage()

    const submit = screen.getByRole('button', { name: 'Update password' })
    expect(submit).toBeDisabled()

    const current = screen.getByLabelText('Current password')
    const next = screen.getByLabelText('New password')
    const confirm = screen.getByLabelText('Confirm new password')

    await user.type(current, 'oldpassword')
    await user.type(next, 'short')
    expect(screen.getByText('At least 8 characters required.')).toBeInTheDocument()
    expect(submit).toBeDisabled()

    await user.clear(next)
    await user.type(next, 'newpassword9')
    await user.type(confirm, 'different1')
    expect(screen.getByText("Passwords don't match.")).toBeInTheDocument()
    expect(submit).toBeDisabled()

    await user.clear(confirm)
    await user.type(confirm, 'newpassword9')
    expect(submit).toBeEnabled()
  })

  it('submits the right body and clears the form on success', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByLabelText('Current password'), 'oldpassword')
    await user.type(screen.getByLabelText('New password'), 'newpassword9')
    await user.type(screen.getByLabelText('Confirm new password'), 'newpassword9')

    await user.click(screen.getByRole('button', { name: 'Update password' }))

    expect(apiFetch).toHaveBeenCalledWith(
      '/api/v1/users/me/password',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          current_password: 'oldpassword',
          new_password: 'newpassword9',
        }),
      }),
    )
    await screen.findByText('Update password')
    expect(
      (screen.getByLabelText('Current password') as HTMLInputElement).value,
    ).toBe('')
    expect(
      (screen.getByLabelText('New password') as HTMLInputElement).value,
    ).toBe('')
  })
})

import { render, screen } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { router } from '@/router'

vi.mock('@/lib/api-client', () => ({
  apiFetch: vi.fn(() => Promise.resolve([])),
}))

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: Object.assign(() => ({ user: null }), {
    getState: () => ({ user: null }),
  }),
}))

vi.mock('@/stores/workspace-store', () => ({
  useWorkspaceStore: Object.assign(
    () => ({
      workspaces: [],
      activeWorkspaceId: null,
      activeWorkspace: () => null,
    }),
    { getState: () => ({ activeWorkspaceId: null }) },
  ),
}))

function renderRoute(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const testRouter = createMemoryRouter(router.routes, { initialEntries: [path] })
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={testRouter} />
    </QueryClientProvider>,
  )
}

describe('route registration (T39)', () => {
  it('public marketing routes resolve without auth', async () => {
    renderRoute('/')
    expect(
      await screen.findByRole('link', { name: /start free/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /log in/i }),
    ).toBeInTheDocument()
  })

  it('pricing route resolves', async () => {
    renderRoute('/pricing')
    expect(
      await screen.findByText('Simple, honest pricing'),
    ).toBeInTheDocument()
  })
})

import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import { CommentThread } from '@/features/collaboration/CommentThread'

const { useCommentsMock, usePostCommentMock } = vi.hoisted(() => ({
  useCommentsMock: vi.fn(),
  usePostCommentMock: vi.fn(),
}))

vi.mock('@/features/collaboration/api', () => ({
  useComments: (...args: unknown[]) => useCommentsMock(...args),
  usePostComment: (...args: unknown[]) => usePostCommentMock(...args),
}))

const COMMENTS = [
  {
    id: 'cmt_1',
    body: 'This CAC looks high @alice',
    author_user_id: 'user_1',
    created_at: '2026-08-26T08:00:00Z',
  },
  {
    id: 'cmt_2',
    body: 'Agreed, let us revisit pricing.',
    author_user_id: 'user_2',
    created_at: '2026-08-26T08:05:00Z',
  },
]

describe('CommentThread', () => {
  beforeEach(() => {
    useCommentsMock.mockReset()
    usePostCommentMock.mockReset()
    useCommentsMock.mockReturnValue({ data: COMMENTS })
    usePostCommentMock.mockReturnValue({
      isPending: false,
      mutate: vi.fn(),
    })
  })

  it('renders the comment list', () => {
    render(<CommentThread targetType="blueprint" targetId="bp_1" />)

    expect(screen.getByText('This CAC looks high @alice')).toBeInTheDocument()
    expect(screen.getByText('Agreed, let us revisit pricing.')).toBeInTheDocument()
  })

  it('posts a comment from the input', async () => {
    const mutate = vi.fn()
    usePostCommentMock.mockReturnValue({ isPending: false, mutate })

    render(<CommentThread targetType="blueprint" targetId="bp_1" />)

    const input = screen.getByPlaceholderText('Add comment… @mention users')
    fireEvent.change(input, { target: { value: 'New comment @bob' } })
    fireEvent.click(screen.getByRole('button', { name: 'Post' }))

    await waitFor(() => {
      expect(mutate).toHaveBeenCalledWith(
        'New comment @bob',
        expect.objectContaining({ onSuccess: expect.any(Function) }),
      )
    })
  })
})

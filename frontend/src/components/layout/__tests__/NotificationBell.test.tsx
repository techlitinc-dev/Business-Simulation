import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import NotificationBell from '../NotificationBell'
import { useNotificationsStore } from '@/stores/notifications'

beforeEach(() => {
  useNotificationsStore.setState({ notifications: [] })
  localStorage.clear()
})

describe('NotificationBell', () => {
  it('shows the unread count badge and hides it at zero', () => {
    useNotificationsStore.getState().addNotification({ title: 'A', body: '', kind: 'info' })
    useNotificationsStore.getState().addNotification({ title: 'B', body: '', kind: 'error' })
    const { rerender } = render(<NotificationBell />)
    expect(screen.getByText('2')).toBeInTheDocument()

    useNotificationsStore.getState().markAllRead()
    rerender(<NotificationBell />)
    expect(screen.queryByText('2')).not.toBeInTheDocument()
  })

  it('opens the dropdown and marks all as read', async () => {
    const user = userEvent.setup()
    useNotificationsStore.getState().addNotification({ title: 'Task done', body: '', kind: 'success' })
    render(<NotificationBell />)

    await user.click(screen.getByRole('button', { name: /notifications/i }))
    expect(await screen.findByText('Task done')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /mark all read/i }))
    expect(useNotificationsStore.getState().unreadCount()).toBe(0)
    expect(screen.queryByText('1')).not.toBeInTheDocument()
  })

  it('shows the caught-up empty state when there are no notifications', async () => {
    const user = userEvent.setup()
    render(<NotificationBell />)
    await user.click(screen.getByRole('button', { name: /notifications/i }))
    expect(
      await screen.findByText("You're all caught up"),
    ).toBeInTheDocument()
  })
})

import { beforeEach, describe, expect, it } from 'vitest'

import { useNotificationsStore } from '../notifications'

beforeEach(() => {
  useNotificationsStore.setState({ notifications: [] })
  localStorage.clear()
})

describe('notifications store', () => {
  it('adds a notification and computes unread count', () => {
    const store = useNotificationsStore.getState()
    store.addNotification({ title: 'Hello', body: 'World', kind: 'info' })
    store.addNotification({ title: 'Second', body: '', kind: 'success' })

    const s = useNotificationsStore.getState()
    expect(s.notifications).toHaveLength(2)
    expect(s.unreadCount()).toBe(2)
  })

  it('marks a single notification read', () => {
    const store = useNotificationsStore.getState()
    store.addNotification({ title: 'A', body: '', kind: 'info' })
    const id = useNotificationsStore.getState().notifications[0].id

    useNotificationsStore.getState().markRead(id)
    expect(useNotificationsStore.getState().unreadCount()).toBe(0)
  })

  it('caps the list at 50 entries', () => {
    const store = useNotificationsStore.getState()
    for (let i = 0; i < 60; i++) {
      store.addNotification({ title: `N${i}`, body: '', kind: 'info' })
    }
    expect(useNotificationsStore.getState().notifications).toHaveLength(50)
    // Newest first.
    expect(useNotificationsStore.getState().notifications[0].title).toBe('N59')
  })

  it('persists and rehydrates from localStorage', () => {
    useNotificationsStore.getState().addNotification({
      title: 'Persisted',
      body: '',
      kind: 'warning',
    })
    // Simulate a fresh page load by re-reading from storage.
    const raw = localStorage.getItem('forge-notifications')
    expect(raw).toBeTruthy()
    const parsed = JSON.parse(raw as string) as {
      state: { notifications: unknown[] }
    }
    expect(parsed.state.notifications).toHaveLength(1)
    expect(parsed.state.notifications[0]).toMatchObject({ title: 'Persisted' })
  })
})

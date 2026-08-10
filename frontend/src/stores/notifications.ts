import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type NotificationKind = 'info' | 'success' | 'warning' | 'error'

/** crypto.randomUUID is only available on secure origins (HTTPS); fall back
 *  to a Math.random-based UUID for plain-HTTP local/dev deploys. */
function newId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

export interface NotificationEntry {
  id: string
  title: string
  body: string
  kind: NotificationKind
  created_at: string
  read: boolean
}

const MAX_ENTRIES = 50

interface NotificationsState {
  notifications: NotificationEntry[]
  addNotification: (n: Omit<NotificationEntry, 'id' | 'created_at' | 'read'>) => void
  markRead: (id: string) => void
  markAllRead: () => void
  clear: () => void
  unreadCount: () => number
}

export const useNotificationsStore = create<NotificationsState>()(
  persist(
    (set, get) => ({
      notifications: [],

      addNotification: (n) => {
        const entry: NotificationEntry = {
          ...n,
          id: newId(),
          created_at: new Date().toISOString(),
          read: false,
        }
        set((s) => ({
          notifications: [entry, ...s.notifications].slice(0, MAX_ENTRIES),
        }))
      },

      markRead: (id) => {
        set((s) => ({
          notifications: s.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n,
          ),
        }))
      },

      markAllRead: () => {
        set((s) => ({
          notifications: s.notifications.map((n) => ({ ...n, read: true })),
        }))
      },

      clear: () => set({ notifications: [] }),

      unreadCount: () =>
        get().notifications.filter((n) => !n.read).length,
    }),
    { name: 'forge-notifications' },
  ),
)

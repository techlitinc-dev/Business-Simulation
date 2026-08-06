import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type NotificationKind = 'info' | 'success' | 'warning' | 'error'

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
          id: crypto.randomUUID(),
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

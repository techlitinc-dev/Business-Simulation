import { Bell, CheckCheck, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import {
  type NotificationKind,
  useNotificationsStore,
} from '@/stores/notifications'

const KIND_DOT: Record<NotificationKind, string> = {
  info: 'bg-primary',
  success: 'bg-success',
  warning: 'bg-warning',
  error: 'bg-destructive',
}

export default function NotificationBell() {
  const notifications = useNotificationsStore((s) => s.notifications)
  const markRead = useNotificationsStore((s) => s.markRead)
  const markAllRead = useNotificationsStore((s) => s.markAllRead)
  const clear = useNotificationsStore((s) => s.clear)
  const unreadCount = useNotificationsStore((s) => s.unreadCount())

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground">
              {unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <div className="flex items-center justify-between border-b border-border px-4 py-2">
          <span className="text-sm font-medium">Notifications</span>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs"
              onClick={markAllRead}
              disabled={unreadCount === 0}
            >
              <CheckCheck className="h-3 w-3" /> Mark all read
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs text-muted-foreground"
              onClick={clear}
              disabled={notifications.length === 0}
            >
              <Trash2 className="h-3 w-3" /> Clear
            </Button>
          </div>
        </div>
        <div className="max-h-80 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="p-4">
              <EmptyState
                title="You're all caught up"
                description="Notifications and toasts will land here."
              />
            </div>
          ) : (
            notifications.map((n) => (
              <button
                key={n.id}
                type="button"
                onClick={() => markRead(n.id)}
                className={cn(
                  'flex w-full items-start gap-2 border-b border-border px-4 py-3 text-left transition-colors hover:bg-accent',
                  !n.read && 'bg-accent/40',
                )}
              >
                <span
                  className={cn('mt-1.5 h-2 w-2 shrink-0 rounded-full', KIND_DOT[n.kind])}
                />
                <span className="min-w-0">
                  <span
                    className={cn(
                      'block text-sm',
                      !n.read ? 'font-semibold' : 'text-muted-foreground',
                    )}
                  >
                    {n.title}
                  </span>
                  {n.body && (
                    <span className="block text-xs text-muted-foreground">
                      {n.body}
                    </span>
                  )}
                  <span className="mt-0.5 block text-[11px] text-muted-foreground/70">
                    {new Date(n.created_at).toLocaleString()}
                  </span>
                </span>
              </button>
            ))
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}

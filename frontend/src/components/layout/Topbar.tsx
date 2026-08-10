import { ChevronDown, CircleUserRound } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth-store'
import { useWorkspaceStore } from '@/stores/workspace-store'
import NotificationBell from './NotificationBell'

export default function Topbar() {
  const workspaces = useWorkspaceStore((s) => s.workspaces)
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId)
  const user = useAuthStore((s) => s.user)
  const active = workspaces.find((w) => w.id === activeWorkspaceId)

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-card/40 px-6 backdrop-blur">
      <div className="flex items-center gap-2 text-sm">
        <span className="font-medium text-foreground">
          {active?.name ?? 'Workspace'}
        </span>
        <span className="text-muted-foreground/50">/</span>
        <Link
          to="/app/simulations"
          className="text-muted-foreground transition-colors hover:text-foreground hover:underline"
        >
          War Room
        </Link>
      </div>
      <div className="flex items-center gap-3">
        <NotificationBell />
        <Button variant="ghost" size="sm" className="gap-2">
          <CircleUserRound className="h-4 w-4" />
          <span className="hidden max-w-32 truncate sm:inline">
            {user?.name ?? 'User'}
          </span>
          <ChevronDown className="h-4 w-4" />
        </Button>
      </div>
    </header>
  )
}

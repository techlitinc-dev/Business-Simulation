import { ChevronDown, CircleUserRound, LogOut, Settings } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useAuthStore } from '@/stores/auth-store'
import { useWorkspaceStore } from '@/stores/workspace-store'
import NotificationBell from './NotificationBell'

export default function Topbar() {
  const workspaces = useWorkspaceStore((s) => s.workspaces)
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId)
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()
  const active = workspaces.find((w) => w.id === activeWorkspaceId)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

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
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="ghost" size="sm" className="gap-2">
              <CircleUserRound className="h-4 w-4" />
              <span className="hidden max-w-32 truncate sm:inline">
                {user?.name ?? 'User'}
              </span>
              <ChevronDown className="h-4 w-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-56 p-1">
            <div className="border-b border-border px-3 py-2">
              <p className="truncate text-sm font-medium text-foreground">
                {user?.name ?? 'User'}
              </p>
              <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
            </div>
            <div className="p-1">
              <Link
                to="/app/settings"
                className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent"
              >
                <Settings className="h-4 w-4" /> Profile settings
              </Link>
              <button
                type="button"
                onClick={handleLogout}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-destructive transition-colors hover:bg-destructive/10"
              >
                <LogOut className="h-4 w-4" /> Log out
              </button>
            </div>
          </PopoverContent>
        </Popover>
      </div>
    </header>
  )
}

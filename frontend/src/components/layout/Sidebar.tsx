import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  Activity,
  BarChart3,
  Blocks,
  Boxes,
  Building2,
  FileText,
  FlaskConical,
  Flame,
  LayoutDashboard,
  Play,
  Plus,
  Settings,
  Users,
  Wallet,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { APP_NAME } from '@/lib/constants'
import { useAuthStore } from '@/stores/auth-store'
import { useWorkspaceStore } from '@/stores/workspace-store'
import { cn } from '@/lib/utils'
import { useCreateWorkspace, useWorkspaces } from '@/features/settings/hooks'

const NAV_SECTIONS: { label: string; items: { to: string; label: string; icon: typeof LayoutDashboard }[] }[] = [
  {
    label: 'Command',
    items: [
      { to: '/app', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/app/blueprints', label: 'Blueprints', icon: Blocks },
      { to: '/app/simulations', label: 'Simulations', icon: Play },
    ],
  },
  {
    label: 'Intel',
    items: [
      { to: '/app/reports', label: 'Reports', icon: FileText },
      { to: '/app/ghost', label: 'Ghost Mode', icon: Activity },
      { to: '/app/marketplace', label: 'Marketplace', icon: Boxes },
      { to: '/app/leaderboard', label: 'Leaderboard', icon: BarChart3 },
      { to: '/app/billing', label: 'Billing', icon: Wallet },
    ],
  },
  {
    label: 'Control',
    items: [{ to: '/app/settings', label: 'Settings', icon: Settings }],
  },
]

export default function Sidebar() {
  useWorkspaces()
  const workspaces = useWorkspaceStore((s) => s.workspaces)
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId)
  const setActive = useWorkspaceStore((s) => s.setActive)
  const user = useAuthStore((s) => s.user)
  const createWorkspace = useCreateWorkspace()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState('')

  const active = workspaces.find((w) => w.id === activeWorkspaceId) ?? null

  const handleCreate = () => {
    createWorkspace.mutate(newName, {
      onSuccess: () => {
        setNewName('')
        setDialogOpen(false)
      },
    })
  }

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      'group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground',
      isActive && 'bg-accent text-accent-foreground',
    )

  const renderChildren = (isActive: boolean, icon: React.ReactNode, label: string) => (
    <>
      <span
        className={cn(
          'absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-transparent',
          isActive && 'bg-primary shadow-[0_0_12px_hsl(var(--primary)/0.6)]',
        )}
      />
      {icon}
      {label}
    </>
  )

  return (
    <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-border bg-card/70 backdrop-blur">
      <div className="flex h-14 items-center gap-2.5 border-b border-border px-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-primary/30 bg-primary/10 shadow-[0_0_16px_hsl(var(--primary)/0.25)]">
          <Flame className="h-4 w-4 text-primary" />
        </div>
        <span className="font-display text-sm font-semibold tracking-wide">
          {APP_NAME}
        </span>
      </div>

      <div className="border-b border-border p-3">
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm" className="w-full justify-between">
              <span className="flex min-w-0 items-center gap-2">
                <Building2 className="h-3.5 w-3.5 shrink-0 text-primary" />
                <span className="truncate">{active?.name ?? 'No workspace'}</span>
              </span>
              <span className="text-muted-foreground">▾</span>
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Switch workspace</DialogTitle>
              <DialogDescription>
                Choose an active workspace or create a new one.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-1">
              {workspaces.map((ws) => (
                <button
                  key={ws.id}
                  type="button"
                  onClick={() => {
                    setActive(ws.id)
                    setDialogOpen(false)
                  }}
                  className={cn(
                    'flex w-full items-center justify-between rounded-md px-3 py-2 text-sm hover:bg-accent',
                    ws.id === activeWorkspaceId &&
                      'bg-accent text-accent-foreground',
                  )}
                >
                  <span className="truncate">{ws.name}</span>
                  {ws.id === activeWorkspaceId && <span>✓</span>}
                </button>
              ))}
              {workspaces.length === 0 && (
                <p className="px-3 py-2 text-sm text-muted-foreground">
                  No workspaces yet.
                </p>
              )}
            </div>
            <DialogFooter className="flex-col gap-3 sm:flex-col">
              <div className="flex items-end gap-2">
                <div className="flex-1 space-y-1">
                  <Label htmlFor="new-ws">New workspace</Label>
                  <Input
                    id="new-ws"
                    placeholder="Acme Inc."
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                  />
                </div>
                <Button
                  onClick={handleCreate}
                  disabled={createWorkspace.isPending || !newName.trim()}
                >
                  <Plus className="h-4 w-4" /> Create
                </Button>
              </div>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <nav className="flex-1 space-y-4 overflow-y-auto p-3">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            <p className="px-3 pb-1 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground/70">
              {section.label}
            </p>
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/app'}
                  className={navLinkClass}
                >
                  {({ isActive }) => renderChildren(isActive, <item.icon className="h-4 w-4 shrink-0 text-muted-foreground/80 transition-colors group-hover:text-foreground" />, item.label)}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
        {user?.is_admin && (
          <div>
            <p className="px-3 pb-1 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground/70">
              Admin
            </p>
            <div className="space-y-0.5">
              <NavLink to="/app/admin" end className={navLinkClass}>
                {({ isActive }) => renderChildren(isActive, <FlaskConical className="h-4 w-4 shrink-0 text-muted-foreground/80" />, 'Overview')}
              </NavLink>
              <NavLink to="/app/admin/users" className={navLinkClass}>
                {({ isActive }) => renderChildren(isActive, <Users className="h-4 w-4 shrink-0 text-muted-foreground/80" />, 'Users')}
              </NavLink>
              <NavLink to="/app/admin/workspaces" className={navLinkClass}>
                {({ isActive }) => renderChildren(isActive, <Building2 className="h-4 w-4 shrink-0 text-muted-foreground/80" />, 'Workspaces')}
              </NavLink>
            </div>
          </div>
        )}
      </nav>

      <div className="border-t border-border p-3">
        <div className="flex items-center gap-3 rounded-md px-2 py-1.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-accent text-xs font-semibold">
            {(user?.name ?? '?').slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-foreground">
              {user?.name}
            </p>
            <p className="truncate text-[11px] text-muted-foreground">
              {user?.email}
            </p>
          </div>
        </div>
      </div>
    </aside>
  )
}

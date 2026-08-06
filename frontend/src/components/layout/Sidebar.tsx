import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Flame, Plus } from 'lucide-react'

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
import { APP_NAME, NAV_ITEMS } from '@/lib/constants'
import { useAuthStore } from '@/stores/auth-store'
import { useWorkspaceStore } from '@/stores/workspace-store'
import { cn } from '@/lib/utils'
import { useCreateWorkspace, useWorkspaces } from '@/features/settings/hooks'

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

  return (
    <aside className="fixed inset-y-0 left-0 flex w-60 flex-col border-r border-border bg-card">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <Flame className="h-5 w-5 text-primary" />
        <span className="text-sm font-semibold tracking-wide">{APP_NAME}</span>
      </div>

      <div className="border-b border-border p-3">
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm" className="w-full justify-between">
              <span className="truncate">{active?.name ?? 'No workspace'}</span>
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

      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/app'}
            className={({ isActive }) =>
              cn(
                'block rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground',
                isActive && 'bg-accent text-accent-foreground',
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
        {user?.is_admin && (
          <div className="pt-2">
            <p className="px-3 pb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Admin
            </p>
            <NavLink
              to="/app/admin"
              end
              className={({ isActive }) =>
                cn(
                  'block rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground',
                  isActive && 'bg-accent text-accent-foreground',
                )
              }
            >
              Overview
            </NavLink>
            <NavLink
              to="/app/admin/users"
              className={({ isActive }) =>
                cn(
                  'block rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground',
                  isActive && 'bg-accent text-accent-foreground',
                )
              }
            >
              Users
            </NavLink>
            <NavLink
              to="/app/admin/workspaces"
              className={({ isActive }) =>
                cn(
                  'block rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground',
                  isActive && 'bg-accent text-accent-foreground',
                )
              }
            >
              Workspaces
            </NavLink>
          </div>
        )}
      </nav>

      <div className="border-t border-border p-3">
        <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
        <p className="truncate text-xs font-medium text-foreground">{user?.name}</p>
      </div>
    </aside>
  )
}

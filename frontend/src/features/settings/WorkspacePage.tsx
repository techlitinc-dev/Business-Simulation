import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { useWorkspaceStore } from '@/stores/workspace-store'
import { useUpdateWorkspace, useWorkspaces } from './hooks'

export default function WorkspacePage() {
  useWorkspaces()
  const workspaces = useWorkspaceStore((s) => s.workspaces)
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId)
  const active = workspaces.find((w) => w.id === activeWorkspaceId) ?? null

  const [name, setName] = useState(active?.name ?? '')
  // TODO: persist on the Workspace model — no benchmark_opt_in column yet.
  const [benchmarkOptIn, setBenchmarkOptIn] = useState(true)
  const updateWorkspace = useUpdateWorkspace(active?.id)

  if (!active) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  const canManage = active.role === 'owner' || active.role === 'admin'

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Workspace</h1>
        <p className="text-sm text-muted-foreground">
          Manage the active workspace.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Workspace name</CardTitle>
          <CardDescription>
            {canManage
              ? 'The name shown across the app.'
              : 'Only owners and admins can rename the workspace.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label htmlFor="ws-name">Name</Label>
            <Input
              id="ws-name"
              value={name}
              disabled={!canManage}
              onChange={(e) => setName(e.target.value)}
              placeholder={active.name}
            />
          </div>
          <div className="mt-4 flex items-center gap-3 text-sm text-muted-foreground">
            <span>Slug:</span>
            <span className="font-mono">{active.slug}</span>
          </div>
        </CardContent>
        <CardFooter>
          <Button
            onClick={() => updateWorkspace.mutate(name)}
            disabled={!canManage || !name.trim() || name === active.name}
          >
            {updateWorkspace.isPending ? 'Saving…' : 'Save'}
          </Button>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Benchmarks</CardTitle>
          <CardDescription>Help improve cohort comparisons for everyone.</CardDescription>
        </CardHeader>
        <CardContent>
          <label className="flex items-center gap-2 text-slate-300 text-sm">
            <input
              type="checkbox"
              checked={benchmarkOptIn}
              onChange={(e) => setBenchmarkOptIn(e.target.checked)}
              className="rounded"
            />
            Share anonymized simulation data to improve cohort benchmarks
          </label>
        </CardContent>
      </Card>
    </div>
  )
}

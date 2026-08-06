import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { apiFetch } from '@/lib/api-client'

interface AdminWorkspaceItem {
  id: string
  name: string
  slug: string
  plan_tier: string
  member_count: number
  runs_count: number
  created_at: string
}

function useAdminWorkspaces(page: number) {
  return useQuery({
    queryKey: ['admin', 'workspaces', page],
    queryFn: () =>
      apiFetch<{ items: AdminWorkspaceItem[]; total: number; page: number }>(
        `/api/v1/admin/workspaces?page=${page}`,
      ),
  })
}

export default function AdminWorkspacesPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useAdminWorkspaces(page)
  const totalPages = data ? Math.max(1, Math.ceil(data.total / 20)) : 1

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Workspaces</h1>
        <p className="text-sm text-muted-foreground">
          All workspaces and their plan tiers.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Slug</TableHead>
                <TableHead>Plan</TableHead>
                <TableHead>Members</TableHead>
                <TableHead>Runs</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data?.items ?? []).map((w) => (
                <TableRow key={w.id}>
                  <TableCell className="font-medium">{w.name}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {w.slug}
                  </TableCell>
                  <TableCell>
                    <Badge className="border-border bg-muted/40">{w.plan_tier}</Badge>
                  </TableCell>
                  <TableCell>{w.member_count}</TableCell>
                  <TableCell>{w.runs_count}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(w.created_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          Page {page} of {totalPages}
        </span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Prev
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}

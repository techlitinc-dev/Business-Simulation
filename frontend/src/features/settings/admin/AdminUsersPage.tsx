import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
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

interface AdminUserItem {
  id: string
  email: string
  name: string
  is_admin: boolean
  is_verified: boolean
  created_at: string
  workspace_count: number
}

function useAdminUsers(page: number, q: string) {
  return useQuery({
    queryKey: ['admin', 'users', page, q],
    queryFn: () =>
      apiFetch<{ items: AdminUserItem[]; total: number; page: number }>(
        `/api/v1/admin/users?page=${page}&q=${encodeURIComponent(q)}`,
      ),
  })
}

export default function AdminUsersPage() {
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const { data, isLoading } = useAdminUsers(page, q)
  const totalPages = data ? Math.max(1, Math.ceil(data.total / 20)) : 1

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Users</h1>
          <p className="text-sm text-muted-foreground">
            All registered accounts.
          </p>
        </div>
        <Input
          className="w-64"
          placeholder="Search by email…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setPage(1)
          }}
        />
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
                <TableHead>Email</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Workspaces</TableHead>
                <TableHead>Joined</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data?.items ?? []).map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="font-medium">{u.name}</TableCell>
                  <TableCell className="text-muted-foreground">{u.email}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {u.is_admin && (
                        <Badge className="border-primary/40 bg-primary/10 text-primary">
                          admin
                        </Badge>
                      )}
                      {u.is_verified ? (
                        <Badge className="border-success/40 bg-success/10 text-success">
                          verified
                        </Badge>
                      ) : (
                        <Badge className="border-border bg-muted/40">unverified</Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>{u.workspace_count}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(u.created_at).toLocaleDateString()}
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

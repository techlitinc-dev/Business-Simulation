import { useState } from 'react'
import { Check, Copy, UserPlus } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAuthStore } from '@/stores/auth-store'
import { useWorkspaceStore } from '@/stores/workspace-store'
import {
  useCreateInvite,
  useMembers,
  useRemoveMember,
  useUpdateMemberRole,
  useWorkspaces,
} from './hooks'

function roleBadgeClass(role: string): string {
  switch (role) {
    case 'owner':
      return 'border-primary/40 bg-primary/10 text-primary'
    case 'admin':
      return 'border-accent/40 bg-accent/10 text-accent-foreground'
    default:
      return 'border-border bg-muted/40 text-muted-foreground'
  }
}

export default function MembersPage() {
  useWorkspaces()
  const workspaces = useWorkspaceStore((s) => s.workspaces)
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId)
  const active = workspaces.find((w) => w.id === activeWorkspaceId) ?? null
  const user = useAuthStore((s) => s.user)

  const { data: members = [], isLoading } = useMembers(active?.id)
  const updateRole = useUpdateMemberRole(active?.id)
  const removeMember = useRemoveMember(active?.id)
  const createInvite = useCreateInvite(active?.id)

  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')
  const [inviteUrl, setInviteUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const canManage = active?.role === 'owner' || active?.role === 'admin'
  const canManageRoles = active?.role === 'owner'

  const handleInvite = () => {
    createInvite.mutate(
      { email: inviteEmail, role: inviteRole },
      {
        onSuccess: (invite) => {
          setInviteUrl(invite.invite_url)
          setInviteEmail('')
        },
      },
    )
  }

  const copyInviteUrl = () => {
    if (!inviteUrl) return
    void navigator.clipboard.writeText(inviteUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const handleRoleChange = (userId: string, role: string) => {
    updateRole.mutate({ userId, role })
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading members…</p>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Members</h1>
          <p className="text-sm text-muted-foreground">
            {active ? active.name : 'No workspace selected'}
          </p>
        </div>
        {canManage && (
          <Dialog
            onOpenChange={(open) => {
              if (!open) setInviteUrl(null)
            }}
          >
            <DialogTrigger asChild>
              <Button>
                <UserPlus className="h-4 w-4" /> Invite member
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Invite a member</DialogTitle>
                <DialogDescription>
                  They'll receive a link to join this workspace.
                </DialogDescription>
              </DialogHeader>
              {inviteUrl ? (
                <div className="space-y-2">
                  <Label htmlFor="invite-url">Invite link</Label>
                  <div className="flex gap-2">
                    <Input id="invite-url" readOnly value={inviteUrl} />
                    <Button variant="outline" size="icon" onClick={copyInviteUrl}>
                      {copied ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="invite-email">Email</Label>
                    <Input
                      id="invite-email"
                      type="email"
                      required
                      placeholder="teammate@example.com"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Role</Label>
                    <Select value={inviteRole} onValueChange={setInviteRole}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="member">Member</SelectItem>
                        <SelectItem value="admin">Admin</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {createInvite.isError && (
                    <p className="text-sm text-destructive">
                      {createInvite.error instanceof Error
                        ? createInvite.error.message
                        : 'Failed to create invite'}
                    </p>
                  )}
                </div>
              )}
              {!inviteUrl && (
                <DialogFooter>
                  <Button onClick={handleInvite} disabled={createInvite.isPending}>
                    {createInvite.isPending ? 'Creating…' : 'Create invite'}
                  </Button>
                </DialogFooter>
              )}
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="rounded-lg border border-border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Joined</TableHead>
              {canManage && <TableHead className="text-right">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {members.map((m) => {
              const isSelf = m.user_id === user?.id
              return (
                <TableRow key={m.user_id}>
                  <TableCell className="font-medium">{m.name}</TableCell>
                  <TableCell className="text-muted-foreground">{m.email}</TableCell>
                  <TableCell>
                    <Badge className={roleBadgeClass(m.role)}>{m.role}</Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(m.joined_at).toLocaleDateString()}
                  </TableCell>
                  {canManage && (
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {m.role !== 'owner' && (
                          <Select
                            value={m.role}
                            onValueChange={(v) => handleRoleChange(m.user_id, v)}
                            disabled={m.role === 'owner'}
                          >
                            <SelectTrigger className="h-8 w-32">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="member">Member</SelectItem>
                              {canManageRoles && (
                                <SelectItem value="admin">Admin</SelectItem>
                              )}
                              {canManageRoles && (
                                <SelectItem value="owner">Owner</SelectItem>
                              )}
                            </SelectContent>
                          </Select>
                        )}
                        {m.role !== 'owner' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive"
                            onClick={() => removeMember.mutate(m.user_id)}
                          >
                            Remove
                          </Button>
                        )}
                        {isSelf && m.role === 'owner' && (
                          <span className="text-xs text-muted-foreground">
                            You are the owner
                          </span>
                        )}
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

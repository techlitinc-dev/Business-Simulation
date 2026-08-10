import { useState } from 'react'
import { Check, Copy, KeyRound, Plus, Trash2 } from 'lucide-react'

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
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { toastError, toastSuccess } from '@/lib/toast'
import { copyToClipboard } from '@/lib/utils'
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from './api-keys'

const SCOPE_OPTIONS = [
  { value: 'runs:read', label: 'Runs (read)' },
  { value: 'runs:write', label: 'Runs (write)' },
  { value: 'reports:read', label: 'Reports (read)' },
  { value: 'blueprints:read', label: 'Blueprints (read)' },
]

export default function ApiKeysPanel() {
  const { data: keys = [], isLoading } = useApiKeys()
  const createKey = useCreateApiKey()
  const revokeKey = useRevokeApiKey()

  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [scopes, setScopes] = useState<string[]>(['runs:read'])
  const [newKey, setNewKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const toggleScope = (scope: string) => {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope],
    )
  }

  const handleCreate = () => {
    createKey.mutate(
      { name, scopes },
      {
        onSuccess: (key) => {
          setNewKey(key.key)
          toastSuccess('API key created', 'Copy it now — it won\'t be shown again')
        },
        onError: (err: unknown) => {
          toastError(
            err instanceof Error ? err.message : 'Create failed',
            'Could not create API key',
          )
        },
      },
    )
  }

  const handleRevoke = (id: string) => {
    revokeKey.mutate(id, {
      onSuccess: () => toastSuccess('API key revoked'),
    })
  }

  const copyKey = () => {
    if (!newKey) return
    void copyToClipboard(newKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">API keys</h1>
          <p className="text-sm text-muted-foreground">
            Programmatic access for enterprise integrations.
          </p>
        </div>
        <Dialog
          open={open}
          onOpenChange={(o) => {
            setOpen(o)
            if (!o) {
              setNewKey(null)
              setName('')
            }
          }}
        >
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4" /> New API key
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create an API key</DialogTitle>
              <DialogDescription>
                The full key is shown only once.
              </DialogDescription>
            </DialogHeader>
            {newKey ? (
              <div className="space-y-3">
                <Label>Your API key</Label>
                <div className="flex gap-2">
                  <Input readOnly value={newKey} className="font-mono" />
                  <Button variant="outline" size="icon" onClick={copyKey}>
                    {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Store it somewhere safe — you won't see it again.
                </p>
                <Button className="w-full" onClick={() => setOpen(false)}>
                  Done
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="key-name">Name</Label>
                  <Input
                    id="key-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="CI / production"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Scopes</Label>
                  <div className="flex flex-wrap gap-2">
                    {SCOPE_OPTIONS.map((s) => (
                      <button
                        key={s.value}
                        type="button"
                        onClick={() => toggleScope(s.value)}
                        className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                          scopes.includes(s.value)
                            ? 'border-primary bg-primary/10 text-primary'
                            : 'border-border text-muted-foreground'
                        }`}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>
                <DialogFooter>
                  <Button onClick={handleCreate} disabled={!name.trim() || scopes.length === 0}>
                    Create key
                  </Button>
                </DialogFooter>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : keys.length === 0 ? (
        <div className="flex flex-col items-center rounded-lg border border-dashed border-border p-10 text-center">
          <KeyRound className="h-8 w-8 text-muted-foreground" />
          <p className="mt-3 text-sm text-muted-foreground">
            No API keys yet. Create one for programmatic access.
          </p>
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Prefix</TableHead>
                <TableHead>Scopes</TableHead>
                <TableHead>Rate limit</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.map((k) => (
                <TableRow key={k.id}>
                  <TableCell className="font-medium">{k.name}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {k.prefix}…
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {k.scopes.map((s) => (
                        <Badge key={s} className="border-border bg-muted/40">
                          {s}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {k.rate_limit_rpm}/min
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive"
                      onClick={() => handleRevoke(k.id)}
                      disabled={Boolean(k.revoked_at)}
                    >
                      <Trash2 className="h-3 w-3" /> Revoke
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}

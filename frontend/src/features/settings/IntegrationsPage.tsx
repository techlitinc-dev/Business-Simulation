import { useState } from 'react'
import { Check, Copy, Plus, Trash2, Webhook } from 'lucide-react'

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
import { useCreateWebhook, useDeleteWebhook, useWebhooks } from './integrations'
import type { WebhookEvent } from './integrations'

const EVENT_OPTIONS: { value: WebhookEvent; label: string }[] = [
  { value: 'run.completed', label: 'Run completed' },
  { value: 'report.ready', label: 'Report ready' },
  { value: 'score.dropped', label: 'Score dropped' },
]

export default function IntegrationsPage() {
  const { data: webhooks = [], isLoading } = useWebhooks()
  const createWebhook = useCreateWebhook()
  const deleteWebhook = useDeleteWebhook()

  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [targetUrl, setTargetUrl] = useState('')
  const [events, setEvents] = useState<WebhookEvent[]>(['run.completed'])
  const [newSecret, setNewSecret] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const toggleEvent = (event: WebhookEvent) => {
    setEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event],
    )
  }

  const handleCreate = () => {
    createWebhook.mutate(
      { name, target_url: targetUrl, events },
      {
        onSuccess: (webhook) => {
          setNewSecret(webhook.secret)
          toastSuccess('Webhook created', 'Copy the secret — it won\'t be shown again')
        },
        onError: (err: unknown) => {
          toastError(
            err instanceof Error ? err.message : 'Create failed',
            'Could not create webhook',
          )
        },
      },
    )
  }

  const handleDelete = (id: string) => {
    deleteWebhook.mutate(id, {
      onSuccess: () => toastSuccess('Webhook deleted'),
    })
  }

  const copySecret = () => {
    if (!newSecret) return
    void copyToClipboard(newSecret)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Integrations</h1>
          <p className="text-sm text-muted-foreground">
            Outbound webhooks and Slack notifications for your workspace.
          </p>
        </div>
        <Dialog
          open={open}
          onOpenChange={(o) => {
            setOpen(o)
            if (!o) {
              setNewSecret(null)
              setName('')
              setTargetUrl('')
              setEvents(['run.completed'])
            }
          }}
        >
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4" /> New webhook
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Register a webhook</DialogTitle>
              <DialogDescription>
                Events will be delivered as signed POSTs to your endpoint.
              </DialogDescription>
            </DialogHeader>
            {newSecret ? (
              <div className="space-y-3">
                <Label>Signing secret</Label>
                <div className="flex gap-2">
                  <Input readOnly value={newSecret} className="font-mono" />
                  <Button variant="outline" size="icon" onClick={copySecret}>
                    {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Used to verify X-Forge-Signature on each delivery — shown once.
                </p>
                <Button className="w-full" onClick={() => setOpen(false)}>
                  Done
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="wh-name">Name</Label>
                  <Input
                    id="wh-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="CI / ops"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="wh-url">Target URL</Label>
                  <Input
                    id="wh-url"
                    value={targetUrl}
                    onChange={(e) => setTargetUrl(e.target.value)}
                    placeholder="https://hooks.example.com/forge"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Events</Label>
                  <div className="flex flex-wrap gap-2">
                    {EVENT_OPTIONS.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => toggleEvent(option.value)}
                        className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                          events.includes(option.value)
                            ? 'border-primary bg-primary/10 text-primary'
                            : 'border-border text-muted-foreground'
                        }`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
                <DialogFooter>
                  <Button
                    onClick={handleCreate}
                    disabled={!name.trim() || !targetUrl.trim() || events.length === 0}
                  >
                    Create webhook
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
      ) : webhooks.length === 0 ? (
        <div className="flex flex-col items-center rounded-lg border border-dashed border-border p-10 text-center">
          <Webhook className="h-8 w-8 text-muted-foreground" />
          <p className="mt-3 text-sm text-muted-foreground">
            No webhooks yet. Register one to receive run/report events.
          </p>
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Target URL</TableHead>
                <TableHead>Events</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {webhooks.map((wh) => (
                <TableRow key={wh.id}>
                  <TableCell className="font-medium">{wh.name}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {wh.target_url}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {wh.events.map((event) => (
                        <Badge key={event} className="border-border bg-muted/40">
                          {event}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive"
                      onClick={() => handleDelete(wh.id)}
                    >
                      <Trash2 className="h-3 w-3" /> Delete
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

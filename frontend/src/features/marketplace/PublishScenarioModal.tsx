import { useState } from 'react'

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
import { Textarea } from '@/components/ui/textarea'
import { toastError, toastSuccess } from '@/lib/toast'
import { useBlueprints, useBlueprintVersions } from '@/features/blueprint/api'
import { usePublishScenario } from './api'

const CATEGORIES = [
  { value: 'market_crash', label: 'Market crash' },
  { value: 'competitor_attack', label: 'Competitor attack' },
  { value: 'supply_chain', label: 'Supply chain' },
  { value: 'regulatory', label: 'Regulatory' },
  { value: 'pandemic', label: 'Pandemic' },
  { value: 'custom', label: 'Custom' },
]

export default function PublishScenarioModal() {
  const [open, setOpen] = useState(false)
  const [blueprintId, setBlueprintId] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('custom')

  const { data: blueprints = [] } = useBlueprints()
  const { data: versions = [] } = useBlueprintVersions(
    blueprintId || undefined,
  )
  const publish = usePublishScenario()

  const canSubmit = blueprintId && title.trim() && description.trim() && category

  const handlePublish = () => {
    const versionId = versions[0]?.id
    if (!versionId) return
    publish.mutate(
      { title, description, category, blueprint_version_id: versionId },
      {
        onSuccess: () => {
          toastSuccess('Scenario published to the marketplace')
          setOpen(false)
          setTitle('')
          setDescription('')
        },
        onError: (err: unknown) => {
          toastError(
            err instanceof Error ? err.message : 'Publish failed',
            'Could not publish scenario',
          )
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Publish a scenario</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Publish a scenario</DialogTitle>
          <DialogDescription>
            Share one of your blueprints as a reusable marketplace scenario.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Blueprint (current version)</Label>
            <Select value={blueprintId} onValueChange={setBlueprintId}>
              <SelectTrigger>
                <SelectValue placeholder="Select a blueprint" />
              </SelectTrigger>
              <SelectContent>
                {blueprints.map((bp) => (
                  <SelectItem key={bp.id} value={bp.id}>
                    {bp.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="sc-title">Title</Label>
            <Input
              id="sc-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="2008 Crash"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="sc-desc">Description</Label>
            <Textarea
              id="sc-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="A market-crash scenario based on the 2008 financial crisis."
            />
          </div>
          <div className="space-y-2">
            <Label>Category</Label>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CATEGORIES.map((c) => (
                  <SelectItem key={c.value} value={c.value}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handlePublish} disabled={!canSubmit || publish.isPending}>
            {publish.isPending ? 'Publishing…' : 'Publish'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

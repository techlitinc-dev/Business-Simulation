import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Ghost } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import { useBlueprints, useBlueprintVersions } from '@/features/blueprint/api'
import { useStartSimulation } from '@/features/simulation/api'
import { cn } from '@/lib/utils'

const PERSONALITIES = [
  {
    id: 'aggressive',
    title: 'Aggressive',
    desc: 'Plays to win — bold moves, accepts higher cash burn for breakthrough upside.',
  },
  {
    id: 'conservative',
    title: 'Conservative',
    desc: 'Protects the downside — favors the least cash-hungry option every time.',
  },
  {
    id: 'opportunist',
    title: 'Opportunist',
    desc: 'Hunts expected value — weighs success odds against cash impact.',
  },
]

export default function GhostSetupPage() {
  const [blueprintId, setBlueprintId] = useState('')
  const [personality, setPersonality] = useState<
    'aggressive' | 'conservative' | 'opportunist'
  >('conservative')

  const { data: blueprints = [], isLoading } = useBlueprints()
  const { data: versions = [] } = useBlueprintVersions(blueprintId || undefined)
  const startSimulation = useStartSimulation()
  const navigate = useNavigate()

  const blueprintVersionId = versions[0]?.id ?? ''
  const canStart = Boolean(blueprintVersionId && personality)

  const handleStart = () => {
    startSimulation.mutate(
      {
        blueprint_version_id: blueprintVersionId,
        mode: 'ghost',
        seed: Date.now() % 2 ** 31,
        config: { personality, months: 24 },
      },
      {
        onSuccess: (run) => navigate(`/app/simulations/ghost/${run.id}`),
      },
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Ghost Mode</h1>
        <p className="text-sm text-muted-foreground">
          Let an AI personality run your business autonomously. No decisions
          required from you.
        </p>
      </div>

      {blueprints.length === 0 ? (
        <EmptyState
          icon={Ghost}
          title="Build a blueprint first"
          description="Ghost Mode needs a blueprint to simulate."
          ctaLabel="Build a blueprint"
          onCtaClick={() => {
            window.location.href = '/app/blueprints/new'
          }}
        />
      ) : (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Blueprint</CardTitle>
              <CardDescription>
                Pick a blueprint to stress-test autonomously.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {blueprints.map((bp) => (
                  <button
                    key={bp.id}
                    type="button"
                    onClick={() => setBlueprintId(bp.id)}
                    className={cn(
                      'rounded-lg border border-border bg-card p-4 text-left text-sm transition-colors hover:border-primary/50',
                      blueprintId === bp.id &&
                        'border-primary bg-primary/10',
                    )}
                  >
                    <span className="font-medium">{bp.name}</span>
                    <span className="mt-1 block text-xs text-muted-foreground">
                      {bp.industry} · v{bp.current_version}
                    </span>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Personality</CardTitle>
              <CardDescription>
                Who should run the company?
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-3">
                {PERSONALITIES.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() =>
                      setPersonality(
                        p.id as 'aggressive' | 'conservative' | 'opportunist',
                      )
                    }
                    className={cn(
                      'rounded-lg border border-border bg-card p-4 text-left transition-colors hover:border-primary/50',
                      personality === p.id && 'border-primary bg-primary/10',
                    )}
                  >
                    <span className="font-semibold">{p.title}</span>
                    <span className="mt-1 block text-xs text-muted-foreground">
                      {p.desc}
                    </span>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          <Button onClick={handleStart} disabled={!canStart || startSimulation.isPending}>
            <Ghost className="h-4 w-4" />
            {startSimulation.isPending ? 'Starting…' : 'Watch ghost run'}
          </Button>
        </>
      )}
    </div>
  )
}

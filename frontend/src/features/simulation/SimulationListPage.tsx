import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { FlaskConical, Ghost, Play } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import { useBlueprints, useBlueprintVersions } from '@/features/blueprint/api'
import { useStartSimulation } from '@/features/simulation/api'
import type { RunMode } from '@/features/simulation/types'
import { useSimulationStore } from '@/stores/simulation'

const MODES: { id: RunMode; label: string; description: string }[] = [
  {
    id: 'stress',
    label: 'Stress test',
    description: 'Run a single path with AI hurdles — instant, interactive.',
  },
  {
    id: 'monte_carlo',
    label: 'Monte Carlo',
    description: 'Run hundreds of paths in the background and aggregate outcomes.',
  },
]

export default function SimulationListPage() {
  const [searchParams] = useSearchParams()
  const requestedMode = searchParams.get('mode')
  const initialMode: RunMode =
    requestedMode === 'monte_carlo' ? 'monte_carlo' : 'stress'
  const [mode, setMode] = useState<RunMode>(initialMode)

  const { data: blueprints = [], isLoading } = useBlueprints()
  const startSimulation = useStartSimulation()
  const reset = useSimulationStore((s) => s.reset)
  const [pendingBlueprintId, setPendingBlueprintId] = useState<string | null>(null)
  const { data: versions = [] } = useBlueprintVersions(pendingBlueprintId ?? undefined)
  const latestVersionId = versions[0]?.id ?? ''

  // Once the latest version is loaded for the pending blueprint, start the run.
  useEffect(() => {
    if (!pendingBlueprintId || !latestVersionId) return
    reset()
    startSimulation.mutate(
      {
        blueprint_version_id: latestVersionId,
        mode,
        seed: Date.now() % 2 ** 31,
      },
      {
        onSuccess: (run) => {
          window.location.href = `/app/simulations/${run.id}`
        },
      },
    )
    setPendingBlueprintId(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingBlueprintId, latestVersionId, reset, startSimulation])

  const activeMode = MODES.find((m) => m.id === mode) ?? MODES[0]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight">
            Simulations
          </h1>
          <p className="text-sm text-muted-foreground">
            {activeMode.description}
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link to="/app/simulations/ghost">
            <Ghost className="h-4 w-4" /> Watch Ghost Run
          </Link>
        </Button>
      </div>

      <div className="flex gap-1 rounded-md border border-border bg-card p-1">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => setMode(m.id)}
            className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              mode === m.id
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:bg-accent/50'
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div>
        <h2 className="mb-3 text-sm font-medium text-muted-foreground">
          {mode === 'monte_carlo'
            ? 'Start a Monte Carlo run from a blueprint'
            : 'Start a stress run from a blueprint'}
        </h2>
        {isLoading ? (
          <Card className="panel">
            <div className="divide-y divide-border">
              {[0, 1, 2].map((i) => (
                <div key={i} className="flex items-center gap-4 p-4">
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-5 w-1/3" />
                    <Skeleton className="h-4 w-1/4" />
                  </div>
                  <Skeleton className="h-8 w-36" />
                </div>
              ))}
            </div>
          </Card>
        ) : blueprints.length === 0 ? (
          <EmptyState
            icon={FlaskConical}
            title="Build a blueprint first"
            description="You'll test it here in the War Room once one exists."
            ctaLabel="Build a blueprint"
            onCtaClick={() => {
              window.location.href = '/app/blueprints/new'
            }}
          />
        ) : (
          <Card className="panel overflow-hidden">
            <ul className="divide-y divide-border">
              {blueprints.map((bp) => (
                <li key={bp.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:gap-6">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-base font-medium text-foreground">
                      {bp.name}
                    </p>
                    <p className="mt-0.5 truncate text-sm text-muted-foreground">
                      {bp.industry} · {bp.stage} · v{bp.current_version}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    onClick={() => setPendingBlueprintId(bp.id)}
                    disabled={startSimulation.isPending}
                    className="shrink-0 sm:self-center"
                  >
                    <Play className="h-4 w-4" /> Run {mode === 'monte_carlo' ? 'Monte Carlo' : 'stress test'}
                  </Button>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  )
}

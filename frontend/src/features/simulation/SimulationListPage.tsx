import { FlaskConical, Play } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import { useBlueprints } from '@/features/blueprint/api'
import { useStartSimulation } from '@/features/simulation/api'
import { useSimulationStore } from '@/stores/simulation'

export default function SimulationListPage() {
  const { data: blueprints = [], isLoading } = useBlueprints()
  const startSimulation = useStartSimulation()
  const reset = useSimulationStore((s) => s.reset)

  const handleStart = (blueprintVersionId: string) => {
    reset()
    startSimulation.mutate(
      { blueprint_version_id: blueprintVersionId, mode: 'stress', seed: Date.now() % 2 ** 31 },
      {
        onSuccess: (run) => {
          window.location.href = `/app/simulations/${run.id}`
        },
      },
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Simulations</h1>
          <p className="text-sm text-muted-foreground">
            Stress-test your blueprint in the War Room.
          </p>
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-sm font-medium text-muted-foreground">
          Start a stress run from a blueprint
        </h2>
        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Card key={i} className="h-full">
                <CardHeader>
                  <Skeleton className="h-5 w-3/4" />
                </CardHeader>
                <CardContent className="space-y-3">
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-8 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : blueprints.length === 0 ? (
          <EmptyState
            icon={FlaskConical}
            title="Build a blueprint first"
            description="You'll stress-test it here in the War Room once one exists."
            ctaLabel="Build a blueprint"
            onCtaClick={() => {
              window.location.href = '/app/blueprints/new'
            }}
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {blueprints.map((bp) => (
              <Card key={bp.id} className="h-full">
                <CardHeader>
                  <CardTitle className="text-base">{bp.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {bp.industry} · {bp.stage} · v{bp.current_version}
                  </p>
                  <Button
                    className="mt-4 w-full"
                    size="sm"
                    onClick={() => handleStart(bp.id)}
                    disabled={startSimulation.isPending}
                  >
                    <Play className="h-4 w-4" /> Run stress test
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

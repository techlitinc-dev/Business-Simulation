import { Link } from 'react-router-dom'
import { Play } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useBlueprints } from '@/features/blueprint/api'
import { useStartSimulation } from '@/features/simulation/api'
import { useSimulationStore } from '@/stores/simulation'

export default function SimulationListPage() {
  const { data: blueprints = [] } = useBlueprints()
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
        {blueprints.length === 0 ? (
          <Card>
            <CardContent className="p-10 text-center">
              <p className="text-sm text-muted-foreground">
                Build a blueprint first, then stress-test it here.
              </p>
              <Button className="mt-4" asChild>
                <Link to="/app/blueprints/new">Build a blueprint</Link>
              </Button>
            </CardContent>
          </Card>
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

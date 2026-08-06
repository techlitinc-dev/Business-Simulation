import { Link } from 'react-router-dom'
import { FilePlus2, Plus } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import { useBlueprints } from './api'

function BlueprintCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-3/4" />
      </CardHeader>
      <CardContent className="space-y-2">
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-3 w-2/3" />
      </CardContent>
    </Card>
  )
}

export default function BlueprintListPage() {
  const { data: blueprints = [], isLoading, isError } = useBlueprints()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-7 w-40" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Skeleton className="h-9 w-36" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <BlueprintCardSkeleton />
          <BlueprintCardSkeleton />
          <BlueprintCardSkeleton />
        </div>
      </div>
    )
  }

  if (isError) {
    return <p className="text-sm text-destructive">Could not load blueprints.</p>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Blueprints</h1>
          <p className="text-sm text-muted-foreground">
            Your business model documents — versioned and validated.
          </p>
        </div>
        <Button asChild>
          <Link to="/app/blueprints/new">
            <Plus className="h-4 w-4" /> New blueprint
          </Link>
        </Button>
      </div>

      {blueprints.length === 0 ? (
        <EmptyState
          icon={FilePlus2}
          title="No blueprints yet"
          description="Model your business to start stress-testing it in the War Room."
          ctaLabel="Build your first blueprint"
          onCtaClick={() => {
            window.location.href = '/app/blueprints/new'
          }}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {blueprints.map((bp) => (
            <Link key={bp.id} to={`/app/blueprints/${bp.id}`} className="block">
              <Card className="h-full transition-colors hover:border-primary/50">
                <CardHeader>
                  <CardTitle className="text-base">{bp.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {bp.industry} · {bp.stage}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Version {bp.current_version} · updated{' '}
                    {new Date(bp.updated_at).toLocaleDateString()}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

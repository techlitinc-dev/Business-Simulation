import { Link } from 'react-router-dom'
import { Plus } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useBlueprints } from './api'

export default function BlueprintListPage() {
  const { data: blueprints = [], isLoading, isError } = useBlueprints()

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading blueprints…</p>
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
        <Card>
          <CardContent className="p-10 text-center">
            <p className="text-sm text-muted-foreground">
              No blueprints yet. Start one to model your business.
            </p>
            <Button className="mt-4" asChild>
              <Link to="/app/blueprints/new">
                <Plus className="h-4 w-4" /> Build your first blueprint
              </Link>
            </Button>
          </CardContent>
        </Card>
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

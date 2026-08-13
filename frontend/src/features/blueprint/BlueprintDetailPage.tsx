import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Network, Pencil, Plus, Trash2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import PublishScenarioModal from '@/features/marketplace/PublishScenarioModal'
import ValidationPanel from './ValidationPanel'
import { useBlueprint, useBlueprints, useDeleteBlueprint } from './api'

export default function BlueprintDetailPage() {
  const { blueprintId } = useParams<{ blueprintId: string }>()
  const navigate = useNavigate()

  const { data: blueprint, isLoading, isError } = useBlueprint(blueprintId)
  const { data: blueprints = [] } = useBlueprints()
  const deleteBlueprint = useDeleteBlueprint()

  const handleDelete = () => {
    if (!blueprint) return
    deleteBlueprint.mutate(blueprint.id, {
      onSuccess: () => navigate('/app/blueprints'),
    })
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading blueprint…</p>
  }

  if (isError || !blueprint) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-destructive">Blueprint not found.</p>
          <Button variant="outline" className="mt-4" onClick={() => navigate('/app/blueprints')}>
            Back to blueprints
          </Button>
        </CardContent>
      </Card>
    )
  }

  const { payload } = blueprint
  const totalPayroll =
    payload.cost_structure.team.reduce((sum, m) => sum + m.salary_annual, 0) / 12

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to="/app/blueprints">
          <ArrowLeft className="h-4 w-4" /> Back to blueprints
        </Link>
      </Button>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold">{blueprint.name}</h1>
              <Badge className="text-muted-foreground">v{blueprint.current_version}</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {payload.business_profile.model_type} · {payload.business_profile.stage} ·{' '}
              {blueprint.industry}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <PublishScenarioModal defaultBlueprintId={blueprint.id} />
            <Button variant="outline" asChild>
              <Link to={`/app/blueprints/${blueprint.id}/edit`}>
                <Pencil className="h-4 w-4" /> Edit
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to={`/app/blueprints/${blueprint.id}/canvas`}>
                <Network className="h-4 w-4" /> Canvas
              </Link>
            </Button>
            <Button variant="ghost" size="icon" className="text-destructive" onClick={handleDelete}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm text-muted-foreground">Starting capital</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold">
              ${payload.financials.starting_capital.toLocaleString()}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm text-muted-foreground">Monthly burn</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold">
              ${payload.cost_structure.burn_rate_month_1.toLocaleString()}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm text-muted-foreground">Monthly payroll</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold">
              ${totalPayroll.toLocaleString()}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Revenue streams</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {payload.revenue_engine.streams.map((s, i) => {
              const ratio = s.cac > 0 ? s.ltv / s.cac : 0
              return (
                <div key={i} className="flex items-center justify-between rounded-md border border-border p-3">
                  <div>
                    <p className="font-medium">{s.name}</p>
                    <p className="text-xs text-muted-foreground">
                      ${s.price_point}/mo · {s.projected_customers_month_12} customers at month 12
                    </p>
                  </div>
                  <Badge className={ratio < 3 ? 'border-destructive/40 bg-destructive/10 text-destructive' : ''}>
                    LTV:CAC {ratio.toFixed(1)}:1
                  </Badge>
                </div>
              )
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent blueprints</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {blueprints.slice(0, 5).map((bp) => (
              <Link
                key={bp.id}
                to={`/app/blueprints/${bp.id}`}
                className="flex items-center justify-between rounded-md px-3 py-2 text-sm hover:bg-accent"
              >
                <span>{bp.name}</span>
                <span className="text-muted-foreground">v{bp.current_version}</span>
              </Link>
            ))}
            <Button variant="outline" size="sm" className="mt-2" asChild>
              <Link to="/app/blueprints/new">
                <Plus className="h-4 w-4" /> New blueprint
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      <aside>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Validation</CardTitle>
          </CardHeader>
          <CardContent>
            <ValidationPanel blueprintId={blueprint.id} />
          </CardContent>
        </Card>
      </aside>
      </div>
    </div>
  )
}

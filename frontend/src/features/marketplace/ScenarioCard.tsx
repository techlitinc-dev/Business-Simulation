import { Link } from 'react-router-dom'
import { Copy, GitFork } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth-store'
import type { ScenarioSummary } from './api'

const CATEGORY_LABELS: Record<string, string> = {
  market_crash: 'Market crash',
  competitor_attack: 'Competitor attack',
  supply_chain: 'Supply chain',
  regulatory: 'Regulatory',
  pandemic: 'Pandemic',
  custom: 'Custom',
}

interface ScenarioCardProps {
  scenario: ScenarioSummary
  onClone?: (id: string) => void
}

export default function ScenarioCard({ scenario, onClone }: ScenarioCardProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const detailPath = isAuthenticated
    ? `/app/marketplace/${scenario.id}`
    : `/marketplace/${scenario.id}`

  return (
    <Card className="flex h-full flex-col transition-colors hover:border-primary/50">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{scenario.title}</CardTitle>
          {scenario.is_featured && (
            <Badge className="border-warning/40 bg-warning/10 text-warning">
              Featured
            </Badge>
          )}
        </div>
        <Badge className="w-fit border-border bg-muted/40 text-muted-foreground">
          {CATEGORY_LABELS[scenario.category] ?? scenario.category}
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col">
        <p className="line-clamp-3 flex-1 text-sm text-muted-foreground">
          {scenario.description}
        </p>
        <div className="mt-4 flex items-center justify-between">
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <GitFork className="h-3 w-3" /> {scenario.clones_count} clones
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link to={detailPath}>View</Link>
            </Button>
            {onClone && (
              <Button size="sm" onClick={() => onClone(scenario.id)}>
                <Copy className="h-3 w-3" /> Clone
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

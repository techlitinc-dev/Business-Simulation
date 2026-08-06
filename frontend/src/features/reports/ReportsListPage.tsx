import { Link } from 'react-router-dom'
import { FileText } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useCompletedRuns } from './hooks'

function modeLabel(mode: string): string {
  switch (mode) {
    case 'monte_carlo':
      return 'Monte Carlo'
    case 'stress':
      return 'Stress test'
    case 'baseline':
      return 'Baseline'
    default:
      return mode
  }
}

export default function ReportsListPage() {
  const { data: runs = [], isLoading, isError } = useCompletedRuns()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Card>
          <div className="space-y-3 p-6">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </Card>
      </div>
    )
  }

  const reportable = runs.filter(
    (r) => r.status === 'completed' && (r.mode === 'monte_carlo' || r.mode === 'stress'),
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Reports</h1>
        <p className="text-sm text-muted-foreground">
          Resilience audits from completed Monte Carlo and stress runs.
        </p>
      </div>

      {isError ? (
        <p className="text-sm text-destructive">Could not load reports.</p>
      ) : reportable.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No reports yet"
          description="Complete a Monte Carlo or stress run to generate a resilience audit."
          ctaLabel="Run a simulation"
          onCtaClick={() => {
            window.location.href = '/app/simulations'
          }}
        />
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Mode</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Seed</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Report</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reportable.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{modeLabel(r.mode)}</TableCell>
                  <TableCell>
                    <Badge className="border-success/40 bg-success/10 text-success">
                      {r.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{r.seed}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(r.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="outline" size="sm" asChild>
                      <Link to={`/app/simulations/${r.id}/report`}>View</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}

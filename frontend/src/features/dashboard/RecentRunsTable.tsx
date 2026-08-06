import { useNavigate } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { SimulationRun } from '@/features/simulation/types'

function statusClass(status: string): string {
  switch (status) {
    case 'completed':
      return 'border-success/40 bg-success/10 text-success'
    case 'dead':
    case 'failed':
    case 'cancelled':
      return 'border-destructive/40 bg-destructive/10 text-destructive'
    case 'running':
    case 'pending':
      return 'border-warning/40 bg-warning/10 text-warning'
    default:
      return 'border-border bg-muted/40 text-muted-foreground'
  }
}

function modeLabel(mode: string): string {
  switch (mode) {
    case 'monte_carlo':
      return 'Monte Carlo'
    case 'stress':
      return 'Stress'
    case 'baseline':
      return 'Baseline'
    default:
      return mode
  }
}

interface RecentRunsTableProps {
  runs: SimulationRun[]
}

export default function RecentRunsTable({ runs }: RecentRunsTableProps) {
  const navigate = useNavigate()
  const recent = runs.slice(0, 5)

  return (
    <Card>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Mode</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Seed</TableHead>
            <TableHead>Created</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {recent.map((r) => (
            <TableRow
              key={r.id}
              className="cursor-pointer"
              onClick={() => navigate(`/app/simulations/${r.id}`)}
            >
              <TableCell className="font-medium">{modeLabel(r.mode)}</TableCell>
              <TableCell>
                <Badge className={statusClass(r.status)}>{r.status}</Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">{r.seed}</TableCell>
              <TableCell className="text-muted-foreground">
                {new Date(r.created_at).toLocaleDateString()}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}

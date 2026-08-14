import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { Trophy } from 'lucide-react'

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
import { apiFetch } from '@/lib/api-client'
import { cn } from '@/lib/utils'

export interface LeaderboardEntry {
  rank: number
  run_id: string
  workspace_name: string
  blueprint_name: string
  resilience_score: number
  survival_rate: number
  median_lifespan_months: number
  completed_at: string
  /** Share token of the run's public report — null/absent when not shared. */
  share_token?: string | null
}

function useLeaderboard() {
  return useQuery({
    queryKey: ['leaderboard'],
    queryFn: () =>
      apiFetch<{ entries: LeaderboardEntry[] }>('/api/v1/leaderboard?limit=50'),
  })
}

const RANK_STYLES: Record<number, string> = {
  1: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
  2: 'bg-slate-400/20 text-slate-300 border-slate-400/40',
  3: 'bg-orange-500/20 text-orange-300 border-orange-500/40',
}

function rankMedal(rank: number) {
  if (rank <= 3) {
    return (
      <span
        className={cn(
          'inline-flex h-7 w-7 items-center justify-center rounded-full border text-sm font-bold',
          RANK_STYLES[rank],
        )}
      >
        {rank}
      </span>
    )
  }
  return <span className="text-sm text-muted-foreground">{rank}</span>
}

export default function LeaderboardPage() {
  const { data, isLoading, isError } = useLeaderboard()
  const entries = data?.entries ?? []
  const navigate = useNavigate()

  const openReport = (shareToken?: string | null) => {
    if (shareToken) navigate(`/shared/reports/${shareToken}`)
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-12">
      <div className="text-center">
        <Trophy className="mx-auto h-10 w-10 text-primary" />
        <h1 className="mt-3 font-display text-3xl font-semibold">
          Resilience Leaderboard
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          The most resilient businesses simulated on The Forge.
        </p>
      </div>

      {isLoading && (
        <Card>
          <div className="space-y-3 p-6">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </Card>
      )}

      {isError && (
        <p className="text-center text-sm text-destructive">
          Could not load the leaderboard.
        </p>
      )}

      {!isLoading && entries.length === 0 && (
        <EmptyState
          icon={Trophy}
          title="No public runs yet"
          description="Make a Monte Carlo run public from its report page to appear here."
        />
      )}

      {entries.length > 0 && (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">Rank</TableHead>
                <TableHead>Workspace</TableHead>
                <TableHead>Blueprint</TableHead>
                <TableHead className="text-right">Resilience</TableHead>
                <TableHead className="text-right">Survival</TableHead>
                <TableHead className="text-right">Median lifespan</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map((e) => {
                const clickable = Boolean(e.share_token)
                return (
                  <TableRow
                    key={e.run_id}
                    onClick={() => openReport(e.share_token)}
                    onKeyDown={(ev) => {
                      if (clickable && (ev.key === 'Enter' || ev.key === ' ')) {
                        ev.preventDefault()
                        openReport(e.share_token)
                      }
                    }}
                    tabIndex={clickable ? 0 : -1}
                    aria-label={
                      clickable
                        ? `View shared report for ${e.blueprint_name}`
                        : undefined
                    }
                    className={
                      clickable
                        ? 'cursor-pointer transition-colors hover:bg-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                        : 'opacity-90'
                    }
                  >
                    <TableCell>{rankMedal(e.rank)}</TableCell>
                    <TableCell className="font-medium">
                      {e.workspace_name}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {e.blueprint_name}
                    </TableCell>
                    <TableCell className="text-right font-semibold text-primary">
                      {e.resilience_score}
                    </TableCell>
                    <TableCell className="text-right">
                      <Badge className="border-success/40 bg-success/10 text-success">
                        {Math.round(e.survival_rate * 100)}%
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {e.median_lifespan_months} mo
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </Card>
      )}

      <div className="text-center">
        <Button variant="outline" asChild>
          <Link to="/">Back to The Forge</Link>
        </Button>
      </div>
    </div>
  )
}

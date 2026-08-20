import { Card, CardContent } from '@/components/ui/card'
import { usePortfolioSummary } from './api'

function ScoreBar({ score }: { score: number | null }) {
  if (score === null) return <span className="text-slate-500 text-sm">No runs yet</span>
  const color = score >= 70 ? 'bg-green-500' : score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-white text-sm font-medium">{score.toFixed(1)}</span>
    </div>
  )
}

export function PortfolioDashboard({ portfolioId }: { portfolioId: string }) {
  const { data, isLoading } = usePortfolioSummary(portfolioId)

  if (isLoading) return <div className="text-slate-400 animate-pulse">Loading portfolio…</div>
  if (!data) return <div className="text-slate-400">Portfolio not found.</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-white text-xl font-semibold">{data.name}</h2>
        <span className="text-slate-400 text-sm">
          {data.member_count} companies · Avg score: {data.avg_resilience_score?.toFixed(1) ?? '—'}
        </span>
      </div>

      <div className="space-y-2">
        {data.workspaces.map((ws, rank) => (
          <Card key={ws.workspace_id} className="bg-slate-800 border-slate-700">
            <CardContent className="py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-slate-500 text-sm w-6">#{rank + 1}</span>
                <div>
                  <div className="text-white text-sm font-medium">{ws.label}</div>
                  {ws.last_run_at && (
                    <div className="text-slate-500 text-xs">
                      Last run: {new Date(ws.last_run_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-4">
                {ws.drift_alert && (
                  <span className="text-red-400 text-xs font-medium">📉 Drift Alert</span>
                )}
                {ws.survival_rate !== null && (
                  <span className="text-slate-400 text-xs">
                    {(ws.survival_rate * 100).toFixed(0)}% survival
                  </span>
                )}
                <ScoreBar score={ws.resilience_score} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

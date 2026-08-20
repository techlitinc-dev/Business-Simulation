import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useVarianceReport } from './api'

interface Props {
  blueprintId: string
}

export function VarianceReportPage({ blueprintId }: Props) {
  const { data: report, isLoading } = useVarianceReport(blueprintId)

  if (isLoading) return <div className="text-slate-400 animate-pulse">Computing variance…</div>
  if (!report) {
    return <div className="text-slate-400">No variance data available. Import actuals first.</div>
  }

  const { delta, narrative } = report
  const scoreColor = delta.score_delta < 0 ? 'text-red-400' : 'text-green-400'

  const cards = [
    {
      label: 'Resilience Score',
      prior: delta.prior_resilience_score.toFixed(1),
      current: delta.new_resilience_score.toFixed(1),
      delta: `${delta.score_delta >= 0 ? '+' : ''}${delta.score_delta.toFixed(1)} pts`,
    },
    {
      label: 'Survival Rate',
      prior: `${(delta.prior_survival_rate * 100).toFixed(0)}%`,
      current: `${(delta.new_survival_rate * 100).toFixed(0)}%`,
      delta: `${(delta.survival_delta * 100).toFixed(0)}pp`,
    },
    {
      label: 'Median Runway',
      prior: `${delta.prior_runway_median}mo`,
      current: `${delta.new_runway_median}mo`,
      delta: `${delta.runway_delta}mo`,
    },
  ]

  return (
    <div className="space-y-4">
      {/* Score delta cards */}
      <div className="grid grid-cols-3 gap-4">
        {cards.map((card) => (
          <Card key={card.label} className="bg-slate-800 border-slate-700">
            <CardContent className="py-4">
              <div className="text-slate-400 text-xs">{card.label}</div>
              <div className="text-white text-xl font-bold">{card.current}</div>
              <div className="text-slate-400 text-xs">Was: {card.prior}</div>
              <div className={`text-sm font-semibold ${scoreColor}`}>{card.delta}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Narrative */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white text-base">{narrative.headline}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-slate-300 text-sm whitespace-pre-wrap">{narrative.explanation}</p>
          <div className="mt-3 text-slate-400 text-xs">Outlook: {narrative.outlook}</div>
        </CardContent>
      </Card>
    </div>
  )
}

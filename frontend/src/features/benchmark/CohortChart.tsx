import {
  Bar,
  BarChart,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { useCohortStats } from './api'

interface Props {
  score: number
  industry?: string
  stage?: string
}

export function CohortChart({ score, industry, stage }: Props) {
  const { data: stats } = useCohortStats(industry, stage)

  if (!stats || stats.sample_size < 5) {
    return <p className="text-slate-500 text-xs">Not enough peer data yet (need 5+ runs).</p>
  }

  const data = [
    { label: 'P25', value: stats.resilience_score_p25 },
    { label: 'P50', value: stats.resilience_score_p50 },
    { label: 'P75', value: stats.resilience_score_p75 },
    { label: 'You', value: score },
  ]

  return (
    <div className="space-y-1">
      <p className="text-slate-400 text-xs">Cohort: {stats.sample_size} simulations</p>
      <div className="h-36">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <XAxis dataKey="label" stroke="#94a3b8" tick={{ fontSize: 10 }} />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 10 }} domain={[0, 100]} />
            <Tooltip
              contentStyle={{
                background: '#1e293b',
                border: '1px solid #334155',
                color: '#e2e8f0',
              }}
            />
            <ReferenceLine y={50} stroke="#6366f1" strokeDasharray="3 3" />
            <Bar dataKey="value" radius={[3, 3, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={index} fill={entry.label === 'You' ? '#3b82f6' : '#334155'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

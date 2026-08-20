import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

interface Props {
  history: Array<{ month: number; revenue?: number; cash?: number; churn_rate?: number }>
}

export function RollingForecastTimeline({ history }: Props) {
  if (!history.length) return <div className="text-slate-400 text-sm">No history yet.</div>
  return (
    <div className="h-48">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={history}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="month" stroke="#94a3b8" tick={{ fontSize: 11 }} />
          <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0' }}
          />
          <Line type="monotone" dataKey="revenue" stroke="#22c55e" dot={false} name="Revenue" />
          <Line type="monotone" dataKey="cash" stroke="#3b82f6" dot={false} name="Cash" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

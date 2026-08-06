import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { TickLog } from '@/features/simulation/types'

interface BurnChartProps {
  ticks: TickLog[]
}

/** MRR as line + burn as bars over months. */
export default function BurnChart({ ticks }: BurnChartProps) {
  const data = ticks.map((t) => ({
    month: t.month,
    mrr: t.kpis.mrr ?? 0,
    burn_rate: t.kpis.burn_rate ?? 0,
  }))

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
            tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
            width={64}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--background)',
              border: '1px solid var(--border)',
              borderRadius: 8,
            }}
            formatter={(value, name) => [
              `$${Number(value ?? 0).toLocaleString()}`,
              name === 'mrr' ? 'MRR' : 'Burn rate',
            ]}
          />
          <Bar
            dataKey="burn_rate"
            fill="var(--chart-3)"
            fillOpacity={0.55}
            radius={[3, 3, 0, 0]}
          />
          <Line
            type="monotone"
            dataKey="mrr"
            stroke="var(--chart-2)"
            strokeWidth={2}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

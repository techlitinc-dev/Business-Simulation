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

/** MRR as line + burn as bars over months, on a distinct chart surface. */
export default function BurnChart({ ticks }: BurnChartProps) {
  const data = ticks.map((t) => ({
    month: t.month,
    mrr: t.kpis.mrr ?? 0,
    burn_rate: t.kpis.burn_rate ?? 0,
  }))

  return (
    <div
      className="h-72 w-full rounded-lg border border-border"
      style={{ background: 'hsl(var(--chart-surface))' }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="hsl(var(--chart-grid))"
          />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 12, fill: 'hsl(var(--chart-axis))' }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: 'hsl(var(--chart-axis))' }}
            tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
            width={64}
          />
          <Tooltip
            contentStyle={{
              background: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: 8,
              color: 'hsl(var(--chart-text))',
            }}
            itemStyle={{ color: 'hsl(var(--chart-text))' }}
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

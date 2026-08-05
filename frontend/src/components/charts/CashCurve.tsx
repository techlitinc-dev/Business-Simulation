import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { TickLog } from '@/features/simulation/types'

interface CashCurveProps {
  ticks: TickLog[]
}

/** Live cash curve — cash_balance (primary) vs mrr (dashed) over months. */
export default function CashCurve({ ticks }: CashCurveProps) {
  const data = ticks.map((t) => ({
    month: t.month,
    cash_balance: t.kpis.cash_balance ?? 0,
    mrr: t.kpis.mrr ?? 0,
  }))

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 12, fill: 'var(--muted-foreground)' }}
            label={{ value: 'Month', position: 'insideBottom', offset: -4 }}
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
              name === 'cash_balance' ? 'Cash balance' : 'MRR',
            ]}
          />
          <ReferenceLine y={0} stroke="var(--destructive)" strokeDasharray="4 4" />
          <Line
            type="monotone"
            dataKey="cash_balance"
            stroke="var(--primary)"
            strokeWidth={2}
            dot={false}
            isAnimationActive
          />
          <Line
            type="monotone"
            dataKey="mrr"
            stroke="var(--chart-2, #4ade80)"
            strokeWidth={1.5}
            strokeDasharray="4 4"
            dot={false}
            isAnimationActive
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

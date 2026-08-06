import {
  Area,
  AreaChart,
  CartesianGrid,
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

/** Cash curve — cash_balance over months using the chart-1 token. */
export default function CashCurve({ ticks }: CashCurveProps) {
  const data = ticks.map((t) => ({
    month: t.month,
    cash_balance: t.kpis.cash_balance ?? 0,
  }))

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <defs>
            <linearGradient id="cashFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
            </linearGradient>
          </defs>
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
            formatter={(value) => [
              `$${Number(value ?? 0).toLocaleString()}`,
              'Cash balance',
            ]}
          />
          <ReferenceLine y={0} stroke="var(--destructive)" strokeDasharray="4 4" />
          <Area
            type="monotone"
            dataKey="cash_balance"
            stroke="var(--chart-1)"
            strokeWidth={2}
            fill="url(#cashFill)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

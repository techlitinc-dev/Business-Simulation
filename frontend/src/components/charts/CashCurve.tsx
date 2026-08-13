import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
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

/** Cash curve — cash_balance over months on a distinct chart surface. */
export default function CashCurve({ ticks }: CashCurveProps) {
  const data = ticks.map((t) => ({
    month: t.month,
    cash_balance: t.kpis.cash_balance ?? 0,
  }))

  return (
    <div
      className="h-72 w-full rounded-lg border border-border"
      style={{ background: 'hsl(var(--chart-surface))' }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <defs>
            <linearGradient id="cashFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="hsl(var(--chart-grid))"
          />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 12, fill: 'hsl(var(--chart-axis))' }}
            label={{
              value: 'Month',
              position: 'insideBottom',
              offset: -4,
              fill: 'hsl(var(--chart-axis))',
            }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: 'hsl(var(--chart-axis))' }}
            tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
            width={64}
          />
          <Tooltip
            contentStyle={{
              background: 'hsl(var(--chart-surface))',
              border: '1px solid hsl(var(--chart-grid))',
              borderRadius: 8,
              color: 'hsl(var(--chart-text))',
            }}
            itemStyle={{ color: 'hsl(var(--chart-text))' }}
            formatter={(value) => [
              `$${Number(value ?? 0).toLocaleString()}`,
              'Cash balance',
            ]}
          />
          <ReferenceLine
            y={0}
            stroke="hsl(var(--destructive))"
            strokeDasharray="4 4"
          />
          <Legend
            verticalAlign="top"
            height={36}
            wrapperStyle={{
              color: 'hsl(var(--chart-text))',
              fontSize: 13,
              fontWeight: 500,
            }}
            formatter={() => 'Cash balance'}
          />
          <Area
            type="monotone"
            dataKey="cash_balance"
            name="Cash balance"
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

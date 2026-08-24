import { render, screen } from '@testing-library/react'

import { RollingForecastTimeline } from '@/features/actuals/RollingForecastTimeline'

const { LineChartMock } = vi.hoisted(() => ({
  LineChartMock: vi.fn(),
}))

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: (props: { data?: unknown[]; children?: React.ReactNode }) =>
    LineChartMock(props),
  Line: ({ stroke, name }: { stroke?: string; name?: string }) => (
    <div data-testid="chart-line" data-stroke={stroke} data-name={name} />
  ),
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
}))

const HISTORY = [
  { month: 1, revenue: 12000, cash: 86000, churn_rate: 0.05 },
  { month: 2, revenue: 15000, cash: 91000, churn_rate: 0.04 },
  { month: 3, revenue: 14000, cash: 89000, churn_rate: 0.06 },
]

describe('RollingForecastTimeline', () => {
  beforeEach(() => {
    LineChartMock.mockReset()
    LineChartMock.mockImplementation(
      (props: { data?: unknown[]; children?: React.ReactNode }) => (
        <div data-testid="line-chart" data-points={props.data?.length ?? 0}>
          {props.children}
        </div>
      ),
    )
  })

  it('renders a line chart with revenue and cash lines', () => {
    render(<RollingForecastTimeline history={HISTORY} />)

    const chart = screen.getByTestId('line-chart')
    expect(chart).toBeInTheDocument()
    // All history rows are passed to the chart.
    expect(chart).toHaveAttribute('data-points', '3')
    expect(screen.getByTestId('x-axis')).toBeInTheDocument()

    // Revenue and cash lines, with the same strokes as the component.
    const lines = screen.getAllByTestId('chart-line')
    expect(lines).toHaveLength(2)
    expect(lines[0]).toHaveAttribute('data-name', 'Revenue')
    expect(lines[0]).toHaveAttribute('data-stroke', '#22c55e')
    expect(lines[1]).toHaveAttribute('data-name', 'Cash')
    expect(lines[1]).toHaveAttribute('data-stroke', '#3b82f6')
  })

  it('shows an empty state when there is no history', () => {
    render(<RollingForecastTimeline history={[]} />)

    expect(screen.getByText('No history yet.')).toBeInTheDocument()
    expect(screen.queryByTestId('line-chart')).not.toBeInTheDocument()
  })
})

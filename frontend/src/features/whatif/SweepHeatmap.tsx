import type { SweepGridPoint } from './api'

interface Props {
  grid: SweepGridPoint[]
  param: string
}

function getColor(rate: number) {
  if (rate >= 0.8) return '#22c55e'
  if (rate >= 0.6) return '#84cc16'
  if (rate >= 0.4) return '#eab308'
  if (rate >= 0.2) return '#f97316'
  return '#ef4444'
}

export function SweepHeatmap({ grid, param }: Props) {
  return (
    <div className="space-y-2">
      <p className="text-slate-400 text-sm">
        Survival Rate vs <span className="text-white font-mono">{param}</span>
      </p>
      <div className="flex gap-1 overflow-x-auto">
        {grid.map((pt, i) => (
          <div key={i} className="flex flex-col items-center min-w-[60px]">
            <div
              className="w-full h-12 rounded flex items-center justify-center text-sm font-bold text-black"
              style={{ backgroundColor: getColor(pt.survival_rate) }}
            >
              {(pt.survival_rate * 100).toFixed(0)}%
            </div>
            <span className="text-xs text-slate-400 mt-1">
              {pt.param_value.toFixed(3)}
            </span>
          </div>
        ))}
      </div>
      {/* Legend */}
      <div className="flex gap-4 text-xs text-slate-400">
        <span>
          <span className="inline-block w-3 h-3 bg-green-500 rounded-sm mr-1" />
          ≥80%
        </span>
        <span>
          <span className="inline-block w-3 h-3 bg-yellow-400 rounded-sm mr-1" />
          40–60%
        </span>
        <span>
          <span className="inline-block w-3 h-3 bg-red-500 rounded-sm mr-1" />
          &lt;20%
        </span>
      </div>
    </div>
  )
}

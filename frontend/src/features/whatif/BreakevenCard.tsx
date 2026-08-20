import { Card, CardContent } from '@/components/ui/card'
import type { BreakevenResult } from './api'

interface Props {
  result: BreakevenResult | null
  loading: boolean
}

export function BreakevenCard({ result, loading }: Props) {
  if (loading) return <div className="text-slate-400 animate-pulse">Calculating break-even…</div>
  if (!result) return null
  return (
    <Card className="bg-amber-950/30 border-amber-700">
      <CardContent className="py-4 space-y-1">
        <div className="text-amber-400 font-semibold text-sm">⚠️ Break-Even Threshold</div>
        <div className="text-white text-lg font-bold">
          {result.param.replace(/_/g, ' ')} = {result.breakeven_value.toFixed(4)}
        </div>
        <p className="text-slate-300 text-sm">{result.message}</p>
        <div className="text-slate-400 text-xs">
          Survival at breakeven: {(result.survival_at_breakeven * 100).toFixed(1)}%
        </div>
      </CardContent>
    </Card>
  )
}

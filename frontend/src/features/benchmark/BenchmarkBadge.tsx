import { usePercentile } from './api'

interface Props {
  score: number
  industry?: string
  stage?: string
}

export function BenchmarkBadge({ score, industry, stage }: Props) {
  const { data: result } = usePercentile(score, industry, stage)

  if (!result || result.sample_size < 5) return null

  const color =
    result.percentile >= 75
      ? 'text-green-400'
      : result.percentile >= 50
        ? 'text-blue-400'
        : result.percentile >= 25
          ? 'text-yellow-400'
          : 'text-red-400'

  return (
    <div className={`text-xs font-medium ${color} mt-1`}>📊 {result.label}</div>
  )
}

import { useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'

export interface PercentileResult {
  score: number
  industry: string | null
  stage: string | null
  percentile: number
  sample_size: number
  label: string
}

export interface CohortStats {
  industry: string | null
  stage: string | null
  sample_size: number
  survival_rate_p25: number
  survival_rate_p50: number
  survival_rate_p75: number
  resilience_score_p25: number
  resilience_score_p50: number
  resilience_score_p75: number
  median_lifespan_p50: number
  top_kill_vectors: string[]
}

export async function getPercentile(
  score: number,
  industry?: string,
  stage?: string,
): Promise<PercentileResult> {
  const params = new URLSearchParams({ score: String(score) })
  if (industry) params.set('industry', industry)
  if (stage) params.set('stage', stage)
  return apiFetch<PercentileResult>(`/api/v1/benchmarks/percentile?${params.toString()}`)
}

export async function getCohortStats(
  industry?: string,
  stage?: string,
): Promise<CohortStats | null> {
  const params = new URLSearchParams()
  if (industry) params.set('industry', industry)
  if (stage) params.set('stage', stage)
  return apiFetch<CohortStats | null>(`/api/v1/benchmarks/cohort?${params.toString()}`)
}

export function usePercentile(score: number | undefined, industry?: string, stage?: string) {
  return useQuery({
    queryKey: ['benchmark', 'percentile', score, industry, stage],
    queryFn: () => getPercentile(score ?? 0, industry, stage),
    enabled: score !== undefined,
  })
}

export function useCohortStats(industry?: string, stage?: string) {
  return useQuery({
    queryKey: ['benchmark', 'cohort', industry, stage],
    queryFn: () => getCohortStats(industry, stage),
  })
}

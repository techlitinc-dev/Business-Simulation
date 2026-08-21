import { useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'

export interface IndustryPackSummary {
  id: string
  name: string
  description: string
}

export interface IndustryPackDetail extends IndustryPackSummary {
  engine_params: Record<string, unknown>
  hurdle_library: {
    type: string
    title: string
    description: string
  }[]
  vertical_kpis: string[]
}

export function useIndustryPacks() {
  return useQuery({
    queryKey: ['industry-packs'],
    queryFn: () =>
      apiFetch<IndustryPackSummary[]>('/api/v1/industry-packs', { skipAuth: false }),
  })
}

export async function getIndustryPack(packId: string): Promise<IndustryPackDetail> {
  return apiFetch<IndustryPackDetail>(`/api/v1/industry-packs/${packId}`)
}

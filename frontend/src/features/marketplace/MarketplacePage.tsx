import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Compass } from 'lucide-react'

import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toastSuccess } from '@/lib/toast'
import { useAuthStore } from '@/stores/auth-store'
import ScenarioCard from './ScenarioCard'
import { useCloneScenario, useScenarios } from './api'

const CATEGORIES = [
  { value: '', label: 'All categories' },
  { value: 'market_crash', label: 'Market crash' },
  { value: 'competitor_attack', label: 'Competitor attack' },
  { value: 'supply_chain', label: 'Supply chain' },
  { value: 'regulatory', label: 'Regulatory' },
  { value: 'pandemic', label: 'Pandemic' },
  { value: 'custom', label: 'Custom' },
]

export default function MarketplacePage() {
  const [category, setCategory] = useState('')
  const { data, isLoading } = useScenarios(category)
  const clone = useCloneScenario()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const navigate = useNavigate()

  const handleClone = (id: string) => {
    if (!isAuthenticated) {
      navigate('/register')
      return
    }
    clone.mutate(id, {
      onSuccess: () => {
        toastSuccess('Scenario cloned into your blueprints')
      },
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Scenario Marketplace</h1>
          <p className="text-sm text-muted-foreground">
            Pre-built business models from real disasters — clone and stress-test.
          </p>
        </div>
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All categories" />
          </SelectTrigger>
          <SelectContent>
            {CATEGORIES.map((c) => (
              <SelectItem key={c.value} value={c.value}>
                {c.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="rounded-lg border border-border bg-card p-5">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="mt-3 h-16 w-full" />
              <Skeleton className="mt-4 h-8 w-full" />
            </div>
          ))}
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={Compass}
          title="No scenarios yet"
          description="Be the first to publish a scenario from a blueprint."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((scenario) => (
            <ScenarioCard
              key={scenario.id}
              scenario={scenario}
              onClone={handleClone}
            />
          ))}
        </div>
      )}
    </div>
  )
}

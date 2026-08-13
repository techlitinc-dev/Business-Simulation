import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Compass } from 'lucide-react'

import { Button } from '@/components/ui/button'
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

const PAGE_SIZE = 20

export default function MarketplacePage() {
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)
  const { data, isLoading } = useScenarios(category, page)
  const clone = useCloneScenario()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const navigate = useNavigate()

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

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
        <Select
          value={category}
          onValueChange={(v) => {
            setCategory(v)
            setPage(1)
          }}
        >
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
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((scenario) => (
              <ScenarioCard
                key={scenario.id}
                scenario={scenario}
                onClone={handleClone}
              />
            ))}
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="h-4 w-4" /> Prev
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages} · {data.total} scenarios
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

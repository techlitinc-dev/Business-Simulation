import { Plus, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useBlueprintDraftStore } from '@/stores/blueprint'
import type { FundingRound } from '@/features/blueprint/types'
import { Field, NumberInput } from './fields'

export default function FinancialsStep() {
  const financials = useBlueprintDraftStore((s) => s.draft.payload.financials)
  const updateSection = useBlueprintDraftStore((s) => s.updateSection)

  const patchFinancials = (patch: Partial<typeof financials>) =>
    updateSection('financials', { ...financials, ...patch })

  const patchRound = (index: number, patch: Partial<FundingRound>) => {
    const funding_rounds = financials.funding_rounds.map((r, i) =>
      i === index ? { ...r, ...patch } : r,
    )
    patchFinancials({ funding_rounds })
  }

  const addRound = () =>
    patchFinancials({ funding_rounds: [...financials.funding_rounds, { month: 0, amount: 0 }] })

  const removeRound = (index: number) =>
    patchFinancials({
      funding_rounds: financials.funding_rounds.filter((_, i) => i !== index),
    })

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Starting capital ($)">
          <NumberInput
            value={financials.starting_capital}
            onChange={(v) => patchFinancials({ starting_capital: v })}
          />
        </Field>
        <Field label="Target runway (months)">
          <NumberInput
            value={financials.target_runway_months}
            onChange={(v) => patchFinancials({ target_runway_months: v })}
            min={1}
            step={1}
          />
        </Field>
      </div>

      <div className="space-y-3">
        {financials.funding_rounds.map((round, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">Funding round {i + 1}</CardTitle>
              <Button
                variant="ghost"
                size="icon"
                className="text-destructive"
                onClick={() => removeRound(i)}
                aria-label={`Remove funding round ${i + 1}`}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <Field label="Month">
                <NumberInput
                  value={round.month}
                  onChange={(v) => patchRound(i, { month: v })}
                  step={1}
                />
              </Field>
              <Field label="Amount ($)">
                <NumberInput value={round.amount} onChange={(v) => patchRound(i, { amount: v })} />
              </Field>
            </CardContent>
          </Card>
        ))}
        <Button variant="outline" onClick={addRound}>
          <Plus className="h-4 w-4" /> Add funding round
        </Button>
      </div>
    </div>
  )
}

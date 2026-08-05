import { Plus, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useBlueprintDraftStore } from '@/stores/blueprint'
import { PRICING_MODELS, type RevenueStream } from '@/features/blueprint/types'
import { Field, NumberInput, SelectInput } from './fields'

function blankStream(): RevenueStream {
  return {
    name: '',
    pricing_model: 'Subscription',
    price_point: 0,
    projected_customers_month_12: 0,
    ltv: 0,
    cac: 0,
    churn_monthly: 0,
  }
}

export default function RevenueStep() {
  const streams = useBlueprintDraftStore((s) => s.draft.payload.revenue_engine.streams)
  const updateSection = useBlueprintDraftStore((s) => s.updateSection)

  const setStreams = (next: RevenueStream[]) =>
    updateSection('revenue_engine', { streams: next })

  const patchStream = (index: number, patch: Partial<RevenueStream>) => {
    const next = streams.map((s, i) => (i === index ? { ...s, ...patch } : s))
    setStreams(next)
  }

  const addStream = () => setStreams([...streams, blankStream()])
  const removeStream = (index: number) => setStreams(streams.filter((_, i) => i !== index))

  return (
    <div className="space-y-4">
      {streams.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No revenue streams yet — add your first one to model how you make money.
        </p>
      )}
      {streams.map((stream, i) => (
        <Card key={i}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base">
              Stream {i + 1}
              {stream.name ? ` — ${stream.name}` : ''}
            </CardTitle>
            <Button
              variant="ghost"
              size="icon"
              className="text-destructive"
              onClick={() => removeStream(i)}
              aria-label={`Remove stream ${i + 1}`}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <Field label="Name">
              <input
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                value={stream.name}
                placeholder="Primary Subscription"
                onChange={(e) => patchStream(i, { name: e.target.value })}
              />
            </Field>
            <Field label="Pricing model">
              <SelectInput
                value={stream.pricing_model}
                onChange={(v) => patchStream(i, { pricing_model: v })}
                options={PRICING_MODELS}
              />
            </Field>
            <Field label="Price point ($)">
              <NumberInput
                value={stream.price_point}
                onChange={(v) => patchStream(i, { price_point: v })}
                step={1}
              />
            </Field>
            <Field label="Projected customers, month 12">
              <NumberInput
                value={stream.projected_customers_month_12}
                onChange={(v) => patchStream(i, { projected_customers_month_12: v })}
                step={1}
              />
            </Field>
            <Field label="LTV ($)">
              <NumberInput value={stream.ltv} onChange={(v) => patchStream(i, { ltv: v })} />
            </Field>
            <Field label="CAC ($)">
              <NumberInput value={stream.cac} onChange={(v) => patchStream(i, { cac: v })} />
            </Field>
            <Field label="Monthly churn (%)" hint="Entered as a percentage; stored as a 0–1 fraction.">
              <NumberInput
                value={Math.round(stream.churn_monthly * 1000) / 10}
                onChange={(v) => patchStream(i, { churn_monthly: v / 100 })}
                step={0.1}
              />
            </Field>
          </CardContent>
        </Card>
      ))}
      <Button variant="outline" onClick={addStream}>
        <Plus className="h-4 w-4" /> Add revenue stream
      </Button>
    </div>
  )
}

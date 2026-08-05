import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useBlueprintDraftStore } from '@/stores/blueprint'
import ValidationPanel from './ValidationPanel'
import CostsTeamStep from './steps/CostsTeamStep'
import FinancialsStep from './steps/FinancialsStep'
import ProfileStep from './steps/ProfileStep'
import RevenueStep from './steps/RevenueStep'
import ReviewStep from './steps/ReviewStep'
import { useAddVersion, useBlueprintValidation, useCreateBlueprint } from './api'

const STEPS = ['Profile', 'Revenue Streams', 'Costs & Team', 'Financials', 'Review']

/** Debounce version saves so typing doesn't fire a request per keystroke. */
function useDebounced(value: unknown, delay: number): boolean {
  const [ready, setReady] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setReady(true), delay)
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [value, delay])

  return ready
}

export default function BuilderWizard() {
  const navigate = useNavigate()
  const draft = useBlueprintDraftStore((s) => s.draft)
  const step = useBlueprintDraftStore((s) => s.step)
  const setStep = useBlueprintDraftStore((s) => s.setStep)
  const setBlueprintId = useBlueprintDraftStore((s) => s.setBlueprintId)

  const createBlueprint = useCreateBlueprint()
  const addVersion = useAddVersion(draft.blueprintId ?? undefined)
  const { data: validation } = useBlueprintValidation(draft.blueprintId ?? undefined)

  const canFinish = Boolean(validation) && validation?.is_valid === true
  const needsCreate = !draft.blueprintId

  // Auto-create the draft blueprint once step 1 (profile) is complete.
  useEffect(() => {
    const profile = draft.payload.business_profile
    const metaReady = draft.name.trim().length > 0
    if (needsCreate && metaReady && profile.industry) {
      createBlueprint.mutate(
        {
          name: draft.name,
          industry: profile.industry,
          stage: profile.stage,
          payload: draft.payload,
        },
        {
          onSuccess: (bp) => setBlueprintId(bp.id),
        },
      )
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.name, draft.payload.business_profile.industry])

  // Debounced version save on every payload change after creation.
  const debounced = useDebounced(draft.payload, 800)
  useEffect(() => {
    if (!needsCreate && debounced) {
      addVersion.mutate(draft.payload)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced])

  const stepContent = useMemo(() => {
    switch (step) {
      case 0:
        return <ProfileStep />
      case 1:
        return <RevenueStep />
      case 2:
        return <CostsTeamStep />
      case 3:
        return <FinancialsStep />
      default:
        return <ReviewStep />
    }
  }, [step])

  const handleFinish = () => {
    if (!canFinish || !draft.blueprintId) return
    navigate(`/app/blueprints/${draft.blueprintId}`)
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Build a blueprint</h1>
          <p className="text-sm text-muted-foreground">
            Step {step + 1} of {STEPS.length} — {STEPS[step]}
          </p>
        </div>

        <div className="flex items-center gap-1">
          {STEPS.map((label, i) => (
            <button
              key={label}
              type="button"
              onClick={() => setStep(i)}
              className={`flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${
                i === step
                  ? 'bg-accent text-accent-foreground'
                  : i < step
                    ? 'text-primary hover:bg-accent/50'
                    : 'text-muted-foreground hover:bg-accent/50'
              }`}
            >
              {i + 1}. {label}
            </button>
          ))}
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{STEPS[step]}</CardTitle>
          </CardHeader>
          <CardContent>{stepContent}</CardContent>
        </Card>

        <div className="flex items-center justify-between">
          <Button variant="outline" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>
            Back
          </Button>
          {step < STEPS.length - 1 ? (
            <Button onClick={() => setStep(Math.min(STEPS.length - 1, step + 1))}>Next</Button>
          ) : (
            <Button onClick={handleFinish} disabled={!canFinish || !draft.blueprintId}>
              Finish
            </Button>
          )}
        </div>
      </div>

      <aside className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Validation</CardTitle>
          </CardHeader>
          <CardContent>
            <ValidationPanel blueprintId={draft.blueprintId ?? undefined} />
          </CardContent>
        </Card>
      </aside>
    </div>
  )
}

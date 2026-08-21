import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toastError } from '@/lib/toast'
import { useBlueprintDraftStore } from '@/stores/blueprint'
import ValidationPanel from './ValidationPanel'
import CostsTeamStep from './steps/CostsTeamStep'
import FinancialsStep from './steps/FinancialsStep'
import ProfileStep from './steps/ProfileStep'
import RevenueStep from './steps/RevenueStep'
import ReviewStep from './steps/ReviewStep'
import { useAddVersion, useCreateBlueprint } from './api'
import { validateDraft } from './types'

const STEPS = ['Profile', 'Revenue Streams', 'Costs & Team', 'Financials', 'Review']

/** Debounce version saves so typing doesn't fire a request per keystroke. */
function useDebounced<T>(value: T, delay: number): T | null {
  const [debounced, setDebounced] = useState<T | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setDebounced(value), delay)
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
  }, [value, delay])

  return debounced
}

export default function BuilderWizard() {
  const navigate = useNavigate()
  const draft = useBlueprintDraftStore((s) => s.draft)
  const step = useBlueprintDraftStore((s) => s.step)
  const setStep = useBlueprintDraftStore((s) => s.setStep)
  const setBlueprintId = useBlueprintDraftStore((s) => s.setBlueprintId)
  const [finishing, setFinishing] = useState(false)

  const createBlueprint = useCreateBlueprint()
  const addVersion = useAddVersion(draft.blueprintId ?? undefined)

  // Validate the *current* draft locally so the Finish button always reflects
  // what the user has typed (server validation of the last saved version lags
  // behind the debounced auto-save).
  const localReport = validateDraft(draft.payload)
  const localErrors = localReport.errors
  const hasErrors = localErrors.length > 0
  const needsCreate = !draft.blueprintId

  // Auto-create the draft blueprint once step 1 (profile) is complete.
  useEffect(() => {
    const profile = draft.payload.business_profile
    const metaReady = draft.name.trim().length > 0
    if (needsCreate && metaReady && profile.industry) {
      // The backend rejects payloads without revenue streams at creation, so
      // seed the initial POST with a minimal-valid payload. The debounced
      // version-save below replaces it with the real payload as the user types.
      const seedPayload = {
        ...draft.payload,
        revenue_engine: {
          streams:
            draft.payload.revenue_engine.streams.length > 0
              ? draft.payload.revenue_engine.streams
              : [
                  {
                    name: 'Seed stream',
                    pricing_model: 'Subscription',
                    price_point: 1,
                    projected_customers_month_12: 1,
                    ltv: 1,
                    cac: 1,
                    churn_monthly: 0.05,
                  },
                ],
        },
      }
      createBlueprint.mutate(
        {
          name: draft.name,
          industry: profile.industry,
          stage: profile.stage,
          payload: seedPayload,
        },
        {
          onSuccess: (bp) => setBlueprintId(bp.id),
        },
      )
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.name, draft.payload.business_profile.industry])

  // Debounced version save on every payload change after creation. Skip
  // payloads that fail local validation — the server would reject them with a
  // 422 anyway (schema or structural), and the rejection would be noise.
  const debouncedPayload = useDebounced(draft.payload, 800)
  useEffect(() => {
    if (!needsCreate && debouncedPayload && !hasErrors) {
      addVersion.mutate(debouncedPayload)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedPayload])

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

  // Persist the latest payload and navigate. If the auto-create effect never
  // ran (or failed), no blueprintId exists yet — create the blueprint here on
  // demand so Finish always works. Server rejections (422) surface via toast
  // and the user stays on the wizard with the ValidationPanel showing issues.
  const handleFinish = async () => {
    if (finishing || addVersion.isPending) return
    setFinishing(true)
    try {
      if (!draft.blueprintId) {
        const bp = await createBlueprint.mutateAsync({
          name: draft.name,
          industry: draft.payload.business_profile.industry,
          stage: draft.payload.business_profile.stage,
          payload: draft.payload,
        })
        setBlueprintId(bp.id)
        navigate(`/app/blueprints/${bp.id}`)
        return
      }
      await addVersion.mutateAsync(draft.payload)
      navigate(`/app/blueprints/${draft.blueprintId}`)
    } catch (err) {
      toastError(
        err instanceof Error
          ? err.message
          : 'The server rejected this blueprint. Check the validation panel.',
        'Could not finish blueprint',
      )
    } finally {
      setFinishing(false)
    }
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
            <div className="flex flex-col items-end gap-2">
              {hasErrors && (
                <p className="max-w-xs text-right text-xs text-destructive">
                  Fix the validation errors below before finishing:
                  {localErrors.map((e) => e.message).join(' ')}
                </p>
              )}
              <Button
                onClick={handleFinish}
                disabled={addVersion.isPending || createBlueprint.isPending || finishing}
                title={
                  addVersion.isPending || createBlueprint.isPending || finishing
                    ? 'Saving…'
                    : hasErrors
                      ? 'Fix the validation errors first'
                      : undefined
                }
              >
                {addVersion.isPending || createBlueprint.isPending || finishing
                  ? 'Saving…'
                  : 'Finish'}
              </Button>
            </div>
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

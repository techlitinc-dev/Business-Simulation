import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Flame } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card'
import { apiFetch } from '@/lib/api-client'
import { useAuthStore, type UserOut } from '@/stores/auth-store'
import { cn } from '@/lib/utils'
import FearStep from './FearStep'
import IndustryPackSelector from './IndustryPackSelector'
import IndustryStep from './IndustryStep'
import StageStep from './StageStep'

const SKIP_KEY = 'forge.onboarding_skipped'

export function skipOnboarding() {
  localStorage.setItem(SKIP_KEY, '1')
}

export function hasSkippedOnboarding(): boolean {
  return localStorage.getItem(SKIP_KEY) === '1'
}

export function clearOnboardingSkip() {
  localStorage.removeItem(SKIP_KEY)
}

const STEPS = [IndustryPackSelector, IndustryStep, StageStep, FearStep]

export default function OnboardingWizard() {
  const [step, setStep] = useState(0)
  const [packId, setPackId] = useState('')
  const [industry, setIndustry] = useState('')
  const [stage, setStage] = useState('')
  const [fear, setFear] = useState('')
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAuthStore((s) => s.setUser)

  const save = useMutation({
    mutationFn: () =>
      apiFetch<UserOut>('/api/v1/users/me', {
        method: 'PATCH',
        body: JSON.stringify({
          industry: packId || industry,
          stage,
          primary_fear: fear,
        }),
      }),
    onSuccess: (user) => {
      setUser(user)
      void queryClient.invalidateQueries({ queryKey: ['me'] })
      navigate('/', { replace: true })
    },
  })

  const canAdvance =
    (step === 0 && packId.length > 0) ||
    (step === 1 && industry.length > 0) ||
    (step === 2 && stage.length > 0) ||
    (step === 3 && fear.trim().length >= 10)

  const handleNext = () => {
    if (step < STEPS.length - 1) setStep(step + 1)
    else save.mutate()
  }

  const handleSkip = () => {
    skipOnboarding()
    navigate('/', { replace: true })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-lg">
        <CardHeader className="items-center text-center">
          <Flame className="h-8 w-8 text-primary" />
          <h1 className="text-xl font-semibold">Set up your Forge</h1>
        </CardHeader>
        <CardContent>
          {/* Progress dots */}
          <div className="mb-6 flex items-center justify-center gap-2">
            {STEPS.map((_, i) => (
              <span
                key={i}
                className={cn(
                  'h-1.5 rounded-full transition-all',
                  i === step ? 'w-6 bg-primary' : 'w-1.5 bg-muted',
                )}
              />
            ))}
          </div>
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
            >
              {step === 0 && <IndustryPackSelector value={packId} onChange={setPackId} />}
              {step === 1 && (
                <IndustryStep value={industry} onChange={setIndustry} />
              )}
              {step === 2 && <StageStep value={stage} onChange={setStage} />}
              {step === 3 && <FearStep value={fear} onChange={setFear} />}
            </motion.div>
          </AnimatePresence>
        </CardContent>
        <CardFooter className="justify-between">
          <Button
            variant="ghost"
            size="sm"
            onClick={step === 0 ? handleSkip : () => setStep(step - 1)}
          >
            {step === 0 ? 'Skip for now' : 'Back'}
          </Button>
          <Button onClick={handleNext} disabled={!canAdvance || save.isPending}>
            {step < STEPS.length - 1 ? 'Next' : save.isPending ? 'Saving…' : 'Finish'}
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}

import { Link } from 'react-router-dom'
import { Flame } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useBillingStore } from '@/stores/billing'

const METRIC_LABELS: Record<string, string> = {
  runs: 'simulation runs',
  mc_ticks: 'Monte Carlo runs',
  llm_tokens: 'AI tokens',
}

export default function PaywallModal() {
  const pendingLimit = useBillingStore((s) => s.pendingLimit)
  const closePaywall = useBillingStore((s) => s.closePaywall)

  if (!pendingLimit) return null
  const label = METRIC_LABELS[pendingLimit.metric] ?? pendingLimit.metric

  return (
    <Dialog open onOpenChange={(open) => !open && closePaywall()}>
      <DialogContent>
        <DialogHeader className="items-center text-center">
          <Flame className="h-8 w-8 text-primary" />
          <DialogTitle className="text-xl">You&apos;ve hit your {label} limit</DialogTitle>
          <DialogDescription>
            Your {pendingLimit.tier} plan allows {pendingLimit.limit} {label} per
            month and you&apos;ve used {pendingLimit.used}. Upgrade to keep
            stress-testing your business.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="flex-col gap-2 sm:flex-col">
          <Button asChild className="w-full">
            <Link to="/pricing" onClick={closePaywall}>
              Upgrade plan
            </Link>
          </Button>
          <Button variant="ghost" onClick={closePaywall}>
            Not now
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

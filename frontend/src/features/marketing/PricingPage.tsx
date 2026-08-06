import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Check } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { PLAN_TIERS, priceLabel } from '@/lib/constants'
import { cn } from '@/lib/utils'
import { revealVariants } from './motion'

export default function PricingPage() {
  const [yearly, setYearly] = useState(false)

  return (
    <div className="mx-auto max-w-6xl px-4 py-16">
      <motion.div
        variants={revealVariants(0)}
        initial="hidden"
        animate="visible"
        className="text-center"
      >
        <h1 className="font-display text-4xl font-bold">Simple, honest pricing</h1>
        <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
          Start free. Upgrade when the wind tunnel earns its keep.
        </p>
        <div className="mt-6 inline-flex items-center gap-2 rounded-full border border-border bg-card p-1">
          <button
            type="button"
            onClick={() => setYearly(false)}
            className={cn(
              'rounded-full px-4 py-1.5 text-sm font-medium transition-colors',
              !yearly ? 'bg-primary text-primary-foreground' : 'text-muted-foreground',
            )}
          >
            Monthly
          </button>
          <button
            type="button"
            onClick={() => setYearly(true)}
            className={cn(
              'rounded-full px-4 py-1.5 text-sm font-medium transition-colors',
              yearly ? 'bg-primary text-primary-foreground' : 'text-muted-foreground',
            )}
          >
            Yearly
          </button>
        </div>
        {yearly && (
          <p className="mt-3 text-xs text-muted-foreground">
            2 months free — billed annually (prices shown per month).
          </p>
        )}
      </motion.div>

      <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {PLAN_TIERS.map((tier, i) => (
          <motion.div
            key={tier.id}
            variants={revealVariants(i * 0.06)}
            initial="hidden"
            animate="visible"
            className={cn(
              'relative flex flex-col rounded-xl border bg-card p-6',
              tier.highlighted
                ? 'border-primary shadow-lg shadow-primary/10'
                : 'border-border',
            )}
          >
            {tier.highlighted && (
              <Badge className="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-primary text-primary-foreground">
                Most popular
              </Badge>
            )}
            <h3 className="font-display text-lg font-semibold">{tier.name}</h3>
            <p className="mt-1 text-xs text-muted-foreground">{tier.tagline}</p>
            <div className="mt-4 flex items-baseline gap-1">
              {tier.price_monthly === null ? (
                <span className="text-3xl font-semibold">Custom</span>
              ) : (
                <>
                  <span className="text-3xl font-semibold">
                    {priceLabel(tier, yearly)}
                  </span>
                  <span className="text-sm text-muted-foreground">/ mo</span>
                </>
              )}
            </div>
            <ul className="mt-6 flex-1 space-y-2">
              {tier.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
            <Button
              className="mt-6"
              variant={tier.highlighted ? 'default' : 'outline'}
              asChild
            >
              <Link to={`/register?plan=${tier.id}`}>
                {tier.price_monthly === null ? 'Contact sales' : 'Get started'}
              </Link>
            </Button>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

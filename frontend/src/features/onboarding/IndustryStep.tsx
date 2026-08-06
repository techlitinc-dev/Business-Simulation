import { cn } from '@/lib/utils'

export const INDUSTRIES = [
  'SaaS',
  'D2C/E-commerce',
  'Retail',
  'Restaurant',
  'Fintech',
  'Marketplace',
  'Agency/Services',
  'Other',
] as const

interface IndustryStepProps {
  value: string
  onChange: (v: string) => void
}

export default function IndustryStep({ value, onChange }: IndustryStepProps) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">What industry are you in?</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          This calibrates the market dynamics of your simulations.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {INDUSTRIES.map((industry) => (
          <button
            key={industry}
            type="button"
            onClick={() => onChange(industry)}
            className={cn(
              'rounded-lg border border-border bg-card px-4 py-3 text-left text-sm font-medium transition-colors hover:border-primary/50',
              value === industry && 'border-primary bg-primary/10 text-primary',
            )}
          >
            {industry}
          </button>
        ))}
      </div>
    </div>
  )
}

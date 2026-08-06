import { cn } from '@/lib/utils'

export const STAGES = ['Idea', 'MVP', 'Pre-Seed', 'Seed', 'Series A+'] as const

interface StageStepProps {
  value: string
  onChange: (v: string) => void
}

export default function StageStep({ value, onChange }: StageStepProps) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">What stage are you at?</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Earlier stages get gentler hurdles, later ones get harder.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-2">
        {STAGES.map((stage) => (
          <button
            key={stage}
            type="button"
            onClick={() => onChange(stage)}
            className={cn(
              'rounded-lg border border-border bg-card px-4 py-3 text-left text-sm font-medium transition-colors hover:border-primary/50',
              value === stage && 'border-primary bg-primary/10 text-primary',
            )}
          >
            {stage}
          </button>
        ))}
      </div>
    </div>
  )
}

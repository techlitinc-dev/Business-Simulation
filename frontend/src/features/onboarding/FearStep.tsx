import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

export const FEAR_SUGGESTIONS = [
  'Not enough runway',
  'CAC too high',
  "Don't know if the model works",
] as const

interface FearStepProps {
  value: string
  onChange: (v: string) => void
}

export default function FearStep({ value, onChange }: FearStepProps) {
  const valid = value.trim().length >= 10

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">What scares you most?</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          The AI Game Master will make sure your worst fear gets tested.
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="primary-fear">Primary fear</Label>
        <Textarea
          id="primary-fear"
          placeholder="e.g. I'm worried my CAC is too high"
          minLength={10}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="min-h-[100px]"
        />
        {!valid && (
          <p className="text-xs text-muted-foreground">
            At least 10 characters, please.
          </p>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {FEAR_SUGGESTIONS.map((chip) => (
          <button
            key={chip}
            type="button"
            onClick={() => onChange(chip)}
            className={cn(
              'rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium transition-colors hover:border-primary/50',
              value === chip && 'border-primary bg-primary/10 text-primary',
            )}
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  )
}

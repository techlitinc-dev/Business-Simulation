import { useIndustryPacks } from '@/features/industry-packs/api'
import { cn } from '@/lib/utils'

interface IndustryPackSelectorProps {
  value: string
  onChange: (packId: string) => void
}

/** Onboarding step: pick an industry pack to pre-tune the simulation engine. */
export default function IndustryPackSelector({
  value,
  onChange,
}: IndustryPackSelectorProps) {
  const { data: packs = [], isLoading } = useIndustryPacks()

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Pick a starting playbook</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Pre-tuned parameters for your industry — applied to your blueprints.
        </p>
      </div>
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading packs…</p>
      ) : (
        <div className="space-y-3">
          {packs.map((pack) => (
            <button
              key={pack.id}
              type="button"
              onClick={() => onChange(pack.id)}
              className={cn(
                'w-full rounded-lg border border-border bg-card px-4 py-3 text-left transition-colors hover:border-primary/50',
                value === pack.id && 'border-primary bg-primary/10',
              )}
            >
              <span className="block text-sm font-medium">{pack.name}</span>
              <span className="mt-0.5 block text-xs text-muted-foreground">
                {pack.description}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

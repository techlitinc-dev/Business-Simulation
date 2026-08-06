import { LucideIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  ctaLabel?: string
  onCtaClick?: () => void
  className?: string
}

/** Branded empty-state fallback with optional CTA. */
export function EmptyState({
  icon: Icon,
  title,
  description,
  ctaLabel,
  onCtaClick,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card/50 px-6 py-12 text-center',
        className,
      )}
    >
      {Icon && (
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-accent">
          <Icon className="h-6 w-6 text-muted-foreground" />
        </div>
      )}
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      {description && (
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          {description}
        </p>
      )}
      {ctaLabel && onCtaClick && (
        <Button className="mt-5" onClick={onCtaClick}>
          {ctaLabel}
        </Button>
      )}
    </div>
  )
}

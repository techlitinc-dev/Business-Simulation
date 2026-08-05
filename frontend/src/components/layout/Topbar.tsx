import { ChevronDown, CircleUserRound } from 'lucide-react'

import { Button } from '@/components/ui/button'

export default function Topbar() {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-6">
      <span className="text-sm text-muted-foreground">Acme Workspace</span>
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" className="gap-2">
          <CircleUserRound className="h-4 w-4" />
          <span className="hidden sm:inline">User</span>
          <ChevronDown className="h-4 w-4" />
        </Button>
      </div>
    </header>
  )
}

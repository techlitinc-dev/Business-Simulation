import { Link, Outlet } from 'react-router-dom'
import { Flame } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { APP_NAME } from '@/lib/constants'

/** Public marketing shell — no auth required. */
export default function MarketingLayout() {
  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b border-border/60 bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2">
            <Flame className="h-5 w-5 text-primary" />
            <span className="font-display text-sm font-semibold tracking-wide">
              {APP_NAME}
            </span>
          </Link>
          <nav className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/login">Log in</Link>
            </Button>
            <Button size="sm" asChild>
              <Link to="/register">Start free</Link>
            </Button>
          </nav>
        </div>
      </header>
      <Outlet />
    </div>
  )
}

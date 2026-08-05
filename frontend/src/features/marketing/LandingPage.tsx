import { Link } from 'react-router-dom'
import { Flame } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { APP_NAME } from '@/lib/constants'

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center">
      <Flame className="h-10 w-10 text-primary" />
      <h1 className="mt-4 text-3xl font-semibold">{APP_NAME}</h1>
      <p className="mt-2 max-w-md text-muted-foreground">
        A digital wind tunnel for entrepreneurs — simulate 24+ months of
        operations, face AI-generated hurdles, and stress-test your business
        model.
      </p>
      <div className="mt-6 flex gap-3">
        <Button asChild>
          <Link to="/app">Open Dashboard</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link to="/login">Login</Link>
        </Button>
      </div>
    </div>
  )
}

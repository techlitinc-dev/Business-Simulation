import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'

interface ComingSoonPageProps {
  title: string
}

export default function ComingSoonPage({ title }: ComingSoonPageProps) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center rounded-lg border border-dashed border-border">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">Coming soon.</p>
      <Button asChild variant="link" className="mt-4">
        <Link to="/app">Back to Dashboard</Link>
      </Button>
    </div>
  )
}

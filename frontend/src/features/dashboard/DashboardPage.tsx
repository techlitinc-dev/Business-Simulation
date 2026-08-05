import { Button } from '@/components/ui/button'

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Your business simulation overview
          </p>
        </div>
        <Button>New Simulation</Button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {['MRR', 'Cash Runway', 'Resilience Score', 'Active Runs'].map(
          (label) => (
            <div
              key={label}
              className="rounded-lg border border-border bg-card p-4"
            >
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="mt-1 text-2xl font-semibold">—</p>
            </div>
          ),
        )}
      </div>
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        Build a blueprint to get started, or load a scenario from the
        marketplace.
      </div>
    </div>
  )
}

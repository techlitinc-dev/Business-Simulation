import { useParams } from 'react-router-dom'

import { Card, CardContent } from '@/components/ui/card'
import { ReportView } from '@/features/reports/ReportPage'
import { useSharedReport } from '@/features/reports/hooks'

/** Public, unauthenticated report view from a signed share token. */
export default function SharedReportPage() {
  const { token } = useParams<{ token: string }>()
  const { data: report, isLoading, isError } = useSharedReport(token)

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-5xl space-y-6">
        <div>
          <h1 className="text-2xl font-semibold">Shared Resilience Audit</h1>
          <p className="text-sm text-muted-foreground">
            Brought to you by The Forge — AI business simulation.
          </p>
        </div>

        {isLoading && <p className="text-sm text-muted-foreground">Loading report…</p>}
        {isError && (
          <Card>
            <CardContent className="p-6">
              <p className="text-sm text-destructive">
                This share link is invalid or has expired.
              </p>
            </CardContent>
          </Card>
        )}
        {report && <ReportView report={report} />}
      </div>
    </div>
  )
}

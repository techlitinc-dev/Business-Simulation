import { Link, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useSharedReport } from '@/features/reports/hooks'

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: 'border-red-500/50 bg-red-500/10 text-red-300',
  HIGH: 'border-orange-500/50 bg-orange-500/10 text-orange-300',
  MEDIUM: 'border-yellow-500/50 bg-yellow-500/10 text-yellow-300',
  LOW: 'border-slate-500/50 bg-slate-500/10 text-slate-300',
}

/** Public, unauthenticated report view from a share token (T44). */
export default function SharedReportPage() {
  const { token } = useParams<{ token: string }>()
  const { data: report, isLoading, isError } = useSharedReport(token)

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold">Shared Resilience Audit</h1>
            <p className="text-sm text-muted-foreground">
              {report
                ? `${report.blueprint_name} · ${new Date(report.completed_at).toLocaleDateString()}`
                : 'Brought to you by The Forge'}
            </p>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link to="/">Back to The Forge</Link>
          </Button>
        </div>

        {isLoading && (
          <div className="space-y-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-72 w-full" />
          </div>
        )}

        {isError && (
          <Card>
            <CardContent className="p-6">
              <p className="text-sm text-destructive">
                This share link is invalid or has been revoked.
              </p>
            </CardContent>
          </Card>
        )}

        {report && (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">
                    Survival rate
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-3xl font-semibold text-emerald-400">
                  {Math.round(report.content_json.survival.survival_rate * 100)}%
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">
                    Median lifespan
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-3xl font-semibold">
                  {report.content_json.survival.median_lifespan_months} mo
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">
                    Runs survived
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-3xl font-semibold">
                  {report.content_json.survival.runs_survived}/
                  {report.content_json.survival.runs_total}
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">
                    Resilience score
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-3xl font-semibold text-amber-400">
                  {report.content_json.resilience_score}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  Architectural weaknesses
                  <Badge className="border-border bg-muted/40">Format C</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {report.content_json.weaknesses.map((w, i) => (
                  <div
                    key={i}
                    className={`rounded-md border p-3 ${SEVERITY_STYLES[w.severity] ?? ''}`}
                  >
                    <p className="text-sm font-medium">{w.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{w.detail}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Full report (markdown)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose-sm prose prose-invert max-w-none">
                  <ReactMarkdown>{report.content_md}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  )
}

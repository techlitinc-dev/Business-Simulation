import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Download, Share2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toastError, toastSuccess } from '@/lib/toast'
import { copyToClipboard } from '@/lib/utils'
import { useExportPdf, useReport, useShareReport } from '@/features/reports/hooks'
import type { ReportOut } from '@/features/reports/hooks'
import { DeepReportPage } from './deep_report/DeepReportPage'

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: 'border-red-500/50 bg-red-500/10 text-red-300',
  HIGH: 'border-orange-500/50 bg-orange-500/10 text-orange-300',
  MEDIUM: 'border-yellow-500/50 bg-yellow-500/10 text-yellow-300',
  LOW: 'border-slate-500/50 bg-slate-500/10 text-slate-300',
}

interface ReportViewProps {
  report: ReportOut
}

/** Shared stat-card + sections renderer used by both ReportPage and shared view. */
export function ReportView({ report }: ReportViewProps) {
  const { survival, weaknesses, optimizations, resilience_score } =
    report.content_json

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">Survival rate</CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-semibold text-emerald-400">
            {Math.round(survival.survival_rate * 100)}%
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">Median lifespan</CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-semibold">
            {survival.median_lifespan_months} mo
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">Runs survived</CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-semibold">
            {survival.runs_survived}/{survival.runs_total}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">Resilience score</CardTitle>
          </CardHeader>
          <CardContent className="text-3xl font-semibold text-amber-400">
            {resilience_score}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Kill vectors</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {survival.kill_vectors.length === 0 ? (
              <p className="text-sm text-muted-foreground">No failures recorded.</p>
            ) : (
              survival.kill_vectors.map((kv) => (
                <div key={kv.cause} className="flex items-center justify-between rounded-md border border-border p-3">
                  <span className="text-sm">{kv.cause}</span>
                  <span className="text-sm text-muted-foreground">
                    {kv.count} failures · {kv.pct}%
                  </span>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Architectural weaknesses</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {weaknesses.map((w, i) => (
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
      </div>

      {optimizations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">AI-generated optimizations</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground">
                  <th className="pb-2 pr-4">Recommendation</th>
                  <th className="pb-2 pr-4">Cost</th>
                  <th className="pb-2 pr-4">Survival impact</th>
                  <th className="pb-2">Trade-off</th>
                </tr>
              </thead>
              <tbody>
                {optimizations.map((opt) => (
                  <tr key={opt.tweak_key} className="border-t border-border">
                    <td className="py-2 pr-4">{opt.recommendation}</td>
                    <td className="py-2 pr-4">{opt.implementation_cost}</td>
                    <td
                      className={`py-2 pr-4 font-medium ${
                        opt.impact_on_survival_rate >= 0 ? 'text-emerald-400' : 'text-red-400'
                      }`}
                    >
                      {opt.impact_on_survival_rate >= 0 ? '+' : ''}
                      {opt.impact_on_survival_rate}pp
                    </td>
                    <td className="py-2">{opt.trade_off}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {report.content_json.counter_factual?.text && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Counter-factual insight</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {report.content_json.counter_factual.text}
            </p>
          </CardContent>
        </Card>
      )}

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
    </div>
  )
}

export default function ReportPage() {
  const { runId } = useParams<{ runId: string }>()
  const { data: report, isLoading, isError } = useReport(runId)
  const exportPdf = useExportPdf(runId)
  const share = useShareReport(runId)
  const [copied, setCopied] = useState(false)

  const handleExport = () => {
    exportPdf.mutate(undefined, {
      onSuccess: (data) => {
        toastSuccess('Report exported', 'PDF generated')
        window.open(data.pdf_url, '_blank')
      },
      onError: (err: unknown) => {
        toastError(
          err instanceof Error ? err.message : 'Export failed',
          'Report export failed',
        )
      },
    })
  }

  const handleShare = () => {
    share.mutate(undefined, {
      onSuccess: (data) => {
        void copyToClipboard(data.share_url)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      },
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
            <Link to="/app/simulations">
              <ArrowLeft className="h-4 w-4" /> Back to runs
            </Link>
          </Button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">Resilience Audit</h1>
            <Badge className="text-muted-foreground">Format C</Badge>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleExport} disabled={exportPdf.isPending || !report}>
            <Download className="h-4 w-4" /> Export PDF
          </Button>
          <Button variant="outline" onClick={handleShare} disabled={share.isPending || !report}>
            {copied ? <Badge className="bg-emerald-500/20 text-emerald-300">Copied</Badge> : <Share2 className="h-4 w-4" />}
            {copied ? 'Copied' : 'Copy share link'}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="audit">
        <TabsList>
          <TabsTrigger value="audit">Resilience Audit</TabsTrigger>
          <TabsTrigger value="deep-dive">Deep-Dive Report</TabsTrigger>
        </TabsList>
        <TabsContent value="audit">
          {isLoading && <p className="text-sm text-muted-foreground">Loading report…</p>}
          {isError && (
            <Card>
              <CardContent className="p-6">
                <p className="text-sm text-destructive">
                  Report unavailable — the run must be completed.
                </p>
              </CardContent>
            </Card>
          )}
          {report && <ReportView report={report} />}
        </TabsContent>
        <TabsContent value="deep-dive">
          {runId ? <DeepReportPage runId={runId} /> : null}
        </TabsContent>
      </Tabs>
    </div>
  )
}

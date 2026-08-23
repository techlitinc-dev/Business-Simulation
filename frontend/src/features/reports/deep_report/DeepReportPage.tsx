import { useState } from 'react'

import { ApiError } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useWorkspaceStore } from '@/stores/workspace-store'
import { ReportViewer } from './ReportViewer'
import { SectionProgressFeed } from './SectionProgressFeed'
import { getDownloadUrl, getReportStatus, requestDeepReport } from './api'
import type { DeepReportJob } from './api'

type Phase = 'idle' | 'generating' | 'complete'

interface Props {
  runId: string
}

export function DeepReportPage({ runId }: Props) {
  const [phase, setPhase] = useState<Phase>('idle')
  const [job, setJob] = useState<DeepReportJob | null>(null)
  const [error, setError] = useState<string | null>(null)
  const workspaces = useWorkspaceStore((s) => s.workspaces)
  const activeWorkspaceId = useWorkspaceStore((s) => s.activeWorkspaceId)
  const planTier =
    workspaces.find((w) => w.id === activeWorkspaceId)?.plan_tier ?? 'free'
  const isFree = planTier === 'free'

  async function handleGenerate() {
    if (isFree) return
    try {
      setPhase('generating')
      setError(null)
      const newJob = await requestDeepReport(runId)
      setJob(newJob)
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Failed to start report generation',
      )
      setPhase('idle')
    }
  }

  async function handleComplete() {
    if (!job) return
    // The worker publishes the final "done" event before PDF assembly, so the
    // status may briefly report completed-without-pdf_url. Keep polling until
    // the PDF exists so the download/viewer only appear when ready.
    for (let attempt = 0; attempt < 10; attempt += 1) {
      const updated = await getReportStatus(job.job_id)
      setJob(updated)
      if (updated.pdf_url) {
        setPhase('complete')
        return
      }
      await new Promise((resolve) => setTimeout(resolve, 1500))
    }
    // Give up waiting but still surface the completed state; the download
    // button will re-fetch status if clicked.
    setPhase('complete')
  }

  if (isFree) {
    return (
      <Card className="border-dashed border-slate-600 bg-slate-800/40">
        <CardContent className="py-12 text-center space-y-4">
          <div className="text-4xl">📊</div>
          <h3 className="text-xl font-semibold text-white">Deep-Dive Report</h3>
          <p className="text-slate-400 max-w-md mx-auto">
            Generate a board-grade 70-page simulation audit with investor-grade
            financials, kill-vector analysis, and prescriptive recommendations.
          </p>
          <Button variant="default" className="bg-blue-600 hover:bg-blue-700">
            Upgrade to Pro — $49/mo
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Deep-Dive Simulation Audit</CardTitle>
          <p className="text-slate-400 text-sm">
            AI-generated board-grade report grounded in your simulation data.
            {job && ` ${job.total_sections} sections · ${job.tier.toUpperCase()} tier`}
          </p>
        </CardHeader>
        <CardContent>
          {phase === 'idle' && (
            <Button
              onClick={handleGenerate}
              className="bg-blue-600 hover:bg-blue-700"
              disabled={!!error}
            >
              Generate Deep-Dive Report
            </Button>
          )}
          {error && <p className="text-red-400 text-sm mt-2">{error}</p>}

          {phase === 'generating' && job && (
            <SectionProgressFeed
              jobId={job.job_id}
              totalSections={job.total_sections}
              onComplete={handleComplete}
            />
          )}

          {phase === 'complete' && job?.pdf_url && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-green-400 font-medium">
                ✅ Report ready — {job.total_sections} sections generated
              </div>
              <div className="flex gap-3">
                <a
                  href={getDownloadUrl(job.job_id)}
                  download
                  className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                >
                  ⬇️ Download PDF
                </a>
              </div>
              <ReportViewer pdfUrl={getDownloadUrl(job.job_id)} />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

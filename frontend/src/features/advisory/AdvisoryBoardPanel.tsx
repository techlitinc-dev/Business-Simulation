import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ApiError } from '@/lib/api-client'
import { getBoardReview, requestBoardReview } from './api'
import type { BoardReviewResult } from './api'
import { PersonaCard } from './PersonaCard'

interface Props {
  blueprintId: string
  runId?: string
}

const POLL_ATTEMPTS = 30
const POLL_INTERVAL_MS = 2000

export function AdvisoryBoardPanel({ blueprintId, runId }: Props) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<BoardReviewResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleRequest() {
    setLoading(true)
    setError(null)
    try {
      const { job_id } = await requestBoardReview(blueprintId, runId)
      for (let i = 0; i < POLL_ATTEMPTS; i++) {
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS))
        const res = await getBoardReview(job_id)
        if (res.status === 'complete' && res.result) {
          setResult(res.result)
          return
        }
        if (res.status === 'error') {
          throw new Error(res.error ?? 'Board review failed')
        }
      }
      throw new Error('Board review timed out')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Board review failed')
      if (err instanceof ApiError) setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {!result && (
        <>
          <Button
            onClick={handleRequest}
            disabled={loading}
            className="bg-purple-600 hover:bg-purple-700"
          >
            {loading ? 'Running Board Review…' : 'Get Advisory Board Review'}
          </Button>
          {error && <p className="text-red-400 text-sm">{error}</p>}
        </>
      )}

      {result && (
        <>
          {/* 4 Persona Cards */}
          <div className="grid grid-cols-2 gap-4">
            {result.reviews.map((r) => (
              <PersonaCard key={r.persona} review={r} />
            ))}
          </div>

          {/* Summary */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Board Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-slate-300 italic">"{result.summary.consensus_verdict}"</p>
              <div>
                <p className="text-slate-400 text-xs uppercase tracking-wide mb-2">
                  Points of Agreement
                </p>
                {result.summary.points_of_agreement.map((p, i) => (
                  <div key={i} className="text-green-300 text-sm">
                    🤝 {p}
                  </div>
                ))}
              </div>
              {result.summary.points_of_conflict?.length > 0 && (
                <div>
                  <p className="text-slate-400 text-xs uppercase tracking-wide mb-2">
                    Points of Conflict
                  </p>
                  {result.summary.points_of_conflict.map((p, i) => (
                    <div key={i} className="text-orange-300 text-sm">
                      ⚡ {p}
                    </div>
                  ))}
                </div>
              )}
              <div className="bg-blue-900/30 border border-blue-700 rounded p-3">
                <p className="text-blue-300 text-sm font-semibold">🎯 Top Priority</p>
                <p className="text-white text-sm">{result.summary.top_priority_action}</p>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

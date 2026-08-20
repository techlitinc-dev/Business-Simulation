import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ApiError } from '@/lib/api-client'
import { uploadActuals } from './api'
import type { ActualsUploadResult } from './api'

const KNOWN_FIELDS = [
  'month',
  'revenue',
  'costs',
  'cash',
  'customers',
  'churn_rate',
  'cac',
  'headcount',
  'mrr',
]

interface Props {
  blueprintId: string
  onSuccess: () => void
}

type Step = 'paste' | 'map' | 'done'

export function ActualsUploadPage({ blueprintId, onSuccess }: Props) {
  const [csv, setCsv] = useState('')
  const [headers, setHeaders] = useState<string[]>([])
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [step, setStep] = useState<Step>('paste')
  const [result, setResult] = useState<ActualsUploadResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  function handleParseCsv() {
    const firstLine = csv.split('\n')[0]
    const cols = firstLine.split(',').map((c) => c.trim().replace(/^"|"$/g, ''))
    setHeaders(cols)
    const autoMap: Record<string, string> = {}
    cols.forEach((col) => {
      const normalized = col.toLowerCase().replace(/\s+/g, '_')
      if (KNOWN_FIELDS.includes(normalized)) autoMap[col] = normalized
    })
    setMapping(autoMap)
    setStep('map')
  }

  async function handleUpload() {
    try {
      const res = await uploadActuals(blueprintId, csv, mapping)
      setResult(res)
      setStep('done')
      onSuccess()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed')
    }
  }

  return (
    <div className="space-y-4">
      {step === 'paste' && (
        <>
          <p className="text-slate-400 text-sm">
            Paste your CSV (first row = headers). Required column: <code>month</code>.
          </p>
          <Textarea
            className="bg-slate-700 border-slate-600 text-white font-mono text-xs h-48"
            placeholder={'month,revenue,costs,cash,churn_rate\n1,12000,14000,86000,0.05'}
            value={csv}
            onChange={(e) => setCsv(e.target.value)}
          />
          <Button onClick={handleParseCsv} disabled={!csv.trim()}>
            Parse Headers →
          </Button>
        </>
      )}

      {step === 'map' && (
        <>
          <p className="text-slate-400 text-sm">Map CSV columns to blueprint fields:</p>
          <div className="space-y-2">
            {headers.map((col) => (
              <div key={col} className="flex items-center gap-3">
                <span className="text-white font-mono text-sm w-40">{col}</span>
                <span className="text-slate-400">→</span>
                <select
                  className="bg-slate-700 border border-slate-600 text-white rounded px-2 py-1 text-sm"
                  value={mapping[col] ?? ''}
                  onChange={(e) => setMapping((prev) => ({ ...prev, [col]: e.target.value }))}
                >
                  <option value="">-- skip --</option>
                  {KNOWN_FIELDS.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <Button onClick={handleUpload} className="bg-blue-600 hover:bg-blue-700">
            Upload Actuals
          </Button>
        </>
      )}

      {step === 'done' && result && (
        <div className="text-green-400 space-y-1">
          <p>✅ Upload complete</p>
          <p className="text-slate-300 text-sm">
            {result.records_created} created · {result.records_updated} updated
            {result.validation_warnings?.length > 0 &&
              ` · ${result.validation_warnings.length} warnings`}
          </p>
        </div>
      )}
    </div>
  )
}

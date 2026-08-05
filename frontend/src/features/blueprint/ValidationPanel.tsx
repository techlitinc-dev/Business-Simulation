import { AlertTriangle, CheckCircle2, XCircle } from 'lucide-react'

import { useBlueprintValidation } from './api'
import type { ValidationIssue } from './types'

function IssueRow({ issue }: { issue: ValidationIssue }) {
  const isError = issue.severity === 'error'
  return (
    <li className="flex items-start gap-2 text-sm">
      {isError ? (
        <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
      ) : (
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
      )}
      <div className="min-w-0">
        <p className={isError ? 'text-destructive' : 'text-amber-600 dark:text-amber-400'}>
          {issue.message}
        </p>
        <p className="font-mono text-xs text-muted-foreground">{issue.field}</p>
      </div>
    </li>
  )
}

interface ValidationPanelProps {
  blueprintId: string | undefined
}

export default function ValidationPanel({ blueprintId }: ValidationPanelProps) {
  const { data, isLoading, isError } = useBlueprintValidation(blueprintId)

  if (!blueprintId) {
    return (
      <p className="text-sm text-muted-foreground">
        Save step 1 to start validating against the API.
      </p>
    )
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Validating…</p>
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-destructive">
        Could not reach the validation API. Is the backend running?
      </p>
    )
  }

  const hasIssues = data.errors.length > 0 || data.warnings.length > 0

  if (!hasIssues) {
    return (
      <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
        <CheckCircle2 className="h-4 w-4" />
        All checks passed
      </div>
    )
  }

  return (
    <ul className="space-y-3">
      {data.errors.map((issue) => (
        <IssueRow key={`${issue.code}-${issue.field}`} issue={issue} />
      ))}
      {data.warnings.map((issue) => (
        <IssueRow key={`${issue.code}-${issue.field}`} issue={issue} />
      ))}
    </ul>
  )
}

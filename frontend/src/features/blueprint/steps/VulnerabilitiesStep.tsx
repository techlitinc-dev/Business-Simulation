import { Plus, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useBlueprintDraftStore } from '@/stores/blueprint'
import {
  VULNERABILITY_SEVERITIES,
  VULNERABILITY_TYPES,
  type Vulnerability,
} from '@/features/blueprint/types'
import { Field, SelectInput } from './fields'

function blankVulnerability(): Vulnerability {
  return {
    type: 'liquidity',
    severity: 'medium',
    description: '',
    mitigation_suggestion: '',
  }
}

export default function VulnerabilitiesStep() {
  const vulnerabilities = useBlueprintDraftStore(
    (s) => s.draft.payload.identified_vulnerabilities,
  )
  const updateSection = useBlueprintDraftStore((s) => s.updateSection)

  const setVulnerabilities = (next: Vulnerability[]) =>
    updateSection('identified_vulnerabilities', next)

  const patchVulnerability = (index: number, patch: Partial<Vulnerability>) => {
    const next = vulnerabilities.map((v, i) => (i === index ? { ...v, ...patch } : v))
    setVulnerabilities(next)
  }

  const addVulnerability = () => setVulnerabilities([...vulnerabilities, blankVulnerability()])
  const removeVulnerability = (index: number) =>
    setVulnerabilities(vulnerabilities.filter((_, i) => i !== index))

  return (
    <div className="space-y-4">
      {vulnerabilities.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No vulnerabilities identified yet — add the risks you think could hurt this business.
        </p>
      )}
      {vulnerabilities.map((vulnerability, i) => (
        <Card key={i}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base">
              Vulnerability {i + 1}
              {vulnerability.type ? ` — ${vulnerability.type}` : ''}
            </CardTitle>
            <Button
              variant="ghost"
              size="icon"
              className="text-destructive"
              onClick={() => removeVulnerability(i)}
              aria-label={`Remove vulnerability ${i + 1}`}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <Field label="Type">
              <SelectInput
                value={vulnerability.type}
                onChange={(v) => patchVulnerability(i, { type: v as Vulnerability['type'] })}
                options={VULNERABILITY_TYPES}
              />
            </Field>
            <Field label="Severity">
              <SelectInput
                value={vulnerability.severity}
                onChange={(v) =>
                  patchVulnerability(i, { severity: v as Vulnerability['severity'] })
                }
                options={VULNERABILITY_SEVERITIES}
              />
            </Field>
            <Field label="Description">
              <textarea
                className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
                value={vulnerability.description}
                placeholder="What could go wrong?"
                onChange={(e) => patchVulnerability(i, { description: e.target.value })}
              />
            </Field>
            <Field label="Mitigation suggestion">
              <textarea
                className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
                value={vulnerability.mitigation_suggestion}
                placeholder="How would you reduce this risk?"
                onChange={(e) => patchVulnerability(i, { mitigation_suggestion: e.target.value })}
              />
            </Field>
          </CardContent>
        </Card>
      ))}
      <Button variant="outline" onClick={addVulnerability}>
        <Plus className="h-4 w-4" /> Add vulnerability
      </Button>
    </div>
  )
}

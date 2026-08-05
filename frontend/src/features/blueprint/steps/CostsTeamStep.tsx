import { Plus, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useBlueprintDraftStore } from '@/stores/blueprint'
import type { TeamMember } from '@/features/blueprint/types'
import { Field, NumberInput } from './fields'

function blankMember(): TeamMember {
  return { role: '', salary_annual: 0, hire_month: 0 }
}

export default function CostsTeamStep() {
  const cost = useBlueprintDraftStore((s) => s.draft.payload.cost_structure)
  const updateSection = useBlueprintDraftStore((s) => s.updateSection)

  const patchCost = (patch: Partial<typeof cost>) =>
    updateSection('cost_structure', { ...cost, ...patch })

  const patchMember = (index: number, patch: Partial<TeamMember>) => {
    const team = cost.team.map((m, i) => (i === index ? { ...m, ...patch } : m))
    patchCost({ team })
  }

  const addMember = () => patchCost({ team: [...cost.team, blankMember()] })
  const removeMember = (index: number) => patchCost({ team: cost.team.filter((_, i) => i !== index) })

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Fixed monthly costs ($)">
          <NumberInput
            value={cost.fixed_monthly}
            onChange={(v) => patchCost({ fixed_monthly: v })}
          />
        </Field>
        <Field label="Variable cost per unit ($)">
          <NumberInput
            value={cost.variable_per_unit}
            onChange={(v) => patchCost({ variable_per_unit: v })}
          />
        </Field>
        <Field label="Burn rate, month 1 ($)">
          <NumberInput
            value={cost.burn_rate_month_1}
            onChange={(v) => patchCost({ burn_rate_month_1: v })}
          />
        </Field>
      </div>

      <div className="space-y-3">
        {cost.team.map((member, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">
                Team member {i + 1}
                {member.role ? ` — ${member.role}` : ''}
              </CardTitle>
              <Button
                variant="ghost"
                size="icon"
                className="text-destructive"
                onClick={() => removeMember(i)}
                aria-label={`Remove team member ${i + 1}`}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-3">
              <Field label="Role">
                <input
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                  value={member.role}
                  placeholder="Lead Developer"
                  onChange={(e) => patchMember(i, { role: e.target.value })}
                />
              </Field>
              <Field label="Annual salary ($)">
                <NumberInput
                  value={member.salary_annual}
                  onChange={(v) => patchMember(i, { salary_annual: v })}
                />
              </Field>
              <Field label="Hire month" hint="0 = from day one">
                <NumberInput
                  value={member.hire_month}
                  onChange={(v) => patchMember(i, { hire_month: v })}
                  step={1}
                />
              </Field>
            </CardContent>
          </Card>
        ))}
        <Button variant="outline" onClick={addMember}>
          <Plus className="h-4 w-4" /> Add team member
        </Button>
      </div>
    </div>
  )
}

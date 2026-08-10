import { useBlueprintDraftStore } from '@/stores/blueprint'
import { GEOGRAPHIES, MODEL_TYPES, STAGES } from '@/features/blueprint/types'
import { Field, SelectInput } from './fields'

export default function ProfileStep() {
  const draft = useBlueprintDraftStore((s) => s.draft)
  const profile = draft.payload.business_profile
  const updateSection = useBlueprintDraftStore((s) => s.updateSection)
  const updateMeta = useBlueprintDraftStore((s) => s.updateMeta)

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Field label="Blueprint name">
        <input
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
          value={draft.name}
          placeholder="My business"
          onChange={(e) => updateMeta({ name: e.target.value })}
        />
      </Field>
      <Field label="Business model" hint="SaaS, D2C, Retail, Restaurant, Fintech, Other">
        <SelectInput
          value={profile.model_type}
          onChange={(v) =>
            updateSection('business_profile', { ...profile, model_type: v })
          }
          options={MODEL_TYPES}
        />
      </Field>
      <Field label="Stage">
        <SelectInput
          value={profile.stage}
          onChange={(v) => updateSection('business_profile', { ...profile, stage: v })}
          options={STAGES}
        />
      </Field>
      <Field label="Industry">
        <SelectInput
          value={profile.industry}
          onChange={(v) => updateSection('business_profile', { ...profile, industry: v })}
          options={['B2B Productivity Software', 'B2B SaaS', 'Consumer', 'E-commerce', 'Food & Beverage', 'Fintech', 'Healthcare', 'Other']}
          placeholder="Select industry"
        />
      </Field>
      <Field label="Geography">
        <SelectInput
          value={profile.geography}
          onChange={(v) => updateSection('business_profile', { ...profile, geography: v })}
          options={GEOGRAPHIES}
        />
      </Field>
    </div>
  )
}

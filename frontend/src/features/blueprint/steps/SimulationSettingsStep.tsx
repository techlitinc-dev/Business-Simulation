import { useEffect, useState } from 'react'

import { useBlueprintDraftStore } from '@/stores/blueprint'
import {
  MONTE_CARLO_RUNS,
  type SimulationParameters,
} from '@/features/blueprint/types'
import { Field, SelectInput } from './fields'

export default function SimulationSettingsStep() {
  const simulation = useBlueprintDraftStore((s) => s.draft.payload.simulation_parameters)
  const updateSection = useBlueprintDraftStore((s) => s.updateSection)

  const patchSimulation = (patch: Partial<SimulationParameters>) =>
    updateSection('simulation_parameters', { ...simulation, ...patch })

  // Local text state so the seed field can be blank (null) and cleared.
  const [seedText, setSeedText] = useState(
    simulation.random_seed === null ? '' : String(simulation.random_seed),
  )
  useEffect(() => {
    setSeedText(simulation.random_seed === null ? '' : String(simulation.random_seed))
  }, [simulation.random_seed])

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Field
        label="Time step"
        hint="The engine always advances monthly — locked to monthly."
      >
        <SelectInput value="monthly" onChange={() => undefined} options={['monthly']} />
      </Field>
      <Field
        label="Monte Carlo runs"
        hint="How many simulation batches to run for resilience analysis."
      >
        <SelectInput
          value={String(simulation.monte_carlo_runs)}
          onChange={(v) => patchSimulation({ monte_carlo_runs: Number(v) })}
          options={MONTE_CARLO_RUNS.map(String)}
        />
      </Field>
      <Field
        label="Random seed"
        hint="Optional. Set a fixed seed to make simulations reproducible."
      >
        <input
          type="number"
          min={0}
          step={1}
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
          value={seedText}
          placeholder="Leave blank for a random seed"
          onChange={(e) => {
            const raw = e.target.value
            setSeedText(raw)
            patchSimulation({
              random_seed: raw === '' ? null : Number(raw),
            })
          }}
        />
      </Field>
    </div>
  )
}

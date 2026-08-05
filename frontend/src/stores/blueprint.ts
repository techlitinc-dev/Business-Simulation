import { create } from 'zustand'

import { emptyBlueprintPayload, type BlueprintPayload } from '@/features/blueprint/types'

export interface BlueprintDraft {
  name: string
  industry: string
  stage: string
  payload: BlueprintPayload
  /** Server-side blueprint id, set after the first POST /blueprints. */
  blueprintId: string | null
}

interface BlueprintDraftState {
  draft: BlueprintDraft
  step: number
  setStep: (step: number) => void
  updateSection: (section: keyof BlueprintPayload, value: unknown) => void
  updateMeta: (patch: Partial<Pick<BlueprintDraft, 'name' | 'industry' | 'stage'>>) => void
  setBlueprintId: (id: string | null) => void
  setDraftFromBlueprint: (draft: BlueprintDraft) => void
  reset: () => void
}

function initialDraft(): BlueprintDraft {
  return {
    name: '',
    industry: '',
    stage: '',
    payload: emptyBlueprintPayload(),
    blueprintId: null,
  }
}

export const useBlueprintDraftStore = create<BlueprintDraftState>((set) => ({
  draft: initialDraft(),
  step: 0,

  setStep: (step) => set({ step }),

  updateSection: (section, value) =>
    set((state) => ({
      draft: {
        ...state.draft,
        payload: { ...state.draft.payload, [section]: value },
      },
    })),

  updateMeta: (patch) =>
    set((state) => ({ draft: { ...state.draft, ...patch } })),

  setBlueprintId: (id) => set((state) => ({ draft: { ...state.draft, blueprintId: id } })),

  setDraftFromBlueprint: (draft) => set({ draft, step: 0 }),

  reset: () => set({ draft: initialDraft(), step: 0 }),
}))

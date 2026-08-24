import { create } from 'zustand'

export interface WorkspaceOut {
  id: string
  name: string
  slug: string
  plan_tier: string
  role: string
  benchmark_opt_in: boolean
}

const ACTIVE_KEY = 'forge.active_workspace_id'

interface WorkspaceState {
  workspaces: WorkspaceOut[]
  activeWorkspaceId: string | null
  setWorkspaces: (workspaces: WorkspaceOut[]) => void
  setActive: (id: string) => void
  activeWorkspace: () => WorkspaceOut | null
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  workspaces: [],
  activeWorkspaceId: localStorage.getItem(ACTIVE_KEY),

  setWorkspaces: (workspaces) => {
    const current = get().activeWorkspaceId
    if (!current || !workspaces.some((w) => w.id === current)) {
      const first = workspaces[0]?.id ?? null
      if (first) localStorage.setItem(ACTIVE_KEY, first)
      set({ workspaces, activeWorkspaceId: first })
    } else {
      set({ workspaces })
    }
  },

  setActive: (id) => {
    localStorage.setItem(ACTIVE_KEY, id)
    set({ activeWorkspaceId: id })
  },

  activeWorkspace: () => {
    const { workspaces, activeWorkspaceId } = get()
    return workspaces.find((w) => w.id === activeWorkspaceId) ?? null
  },
}))

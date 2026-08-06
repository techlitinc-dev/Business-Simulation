import { create } from 'zustand'

interface PaywallState {
  /** Non-null when the app should show the upgrade modal. */
  pendingLimit: {
    metric: string
    limit: number
    used: number
    tier: string
  } | null
  openPaywall: (info: {
    metric: string
    limit: number
    used: number
    tier: string
  }) => void
  closePaywall: () => void
}

export const useBillingStore = create<PaywallState>((set) => ({
  pendingLimit: null,
  openPaywall: (info) => set({ pendingLimit: info }),
  closePaywall: () => set({ pendingLimit: null }),
}))

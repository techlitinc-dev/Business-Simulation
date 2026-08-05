export const APP_NAME = 'The Forge'

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface NavItem {
  label: string
  to: string
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', to: '/app' },
  { label: 'Blueprints', to: '/app/blueprints' },
  { label: 'Simulations', to: '/app/simulations' },
  { label: 'Reports', to: '/app/reports' },
  { label: 'Settings', to: '/app/settings' },
]

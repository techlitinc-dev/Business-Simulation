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

export interface PlanTier {
  id: string
  name: string
  price_monthly: number | null
  price_yearly: number | null
  tagline: string
  features: string[]
  highlighted: boolean
}

export const PLAN_TIERS: PlanTier[] = [
  {
    id: 'free',
    name: 'Free',
    price_monthly: 0,
    price_yearly: 0,
    tagline: 'Test the waters',
    features: [
      '5 runs / month',
      'Baseline mode only',
      '1 seat',
      'Basic reports',
    ],
    highlighted: false,
  },
  {
    id: 'pro',
    name: 'Pro',
    price_monthly: 49,
    price_yearly: 40,
    tagline: 'For serious founders',
    features: [
      '100 runs / month',
      'Monte Carlo ×100',
      '3 seats',
      'AI Game Master hurdles',
      'Full resilience reports',
    ],
    highlighted: true,
  },
  {
    id: 'team',
    name: 'Team',
    price_monthly: 149,
    price_yearly: 124,
    tagline: 'For growing teams',
    features: [
      'Unlimited runs',
      'Monte Carlo ×1000',
      '10 seats',
      'Marketplace publishing',
      'Priority support',
    ],
    highlighted: false,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price_monthly: null,
    price_yearly: null,
    tagline: 'For scale',
    features: [
      'API access',
      'SSO / SAML',
      'On-prem option',
      'Dedicated support',
    ],
    highlighted: false,
  },
]

export function priceLabel(tier: PlanTier, yearly: boolean): string {
  if (tier.price_monthly === null) return 'Custom'
  const price = yearly ? tier.price_yearly ?? tier.price_monthly : tier.price_monthly
  return `$${price}`
}

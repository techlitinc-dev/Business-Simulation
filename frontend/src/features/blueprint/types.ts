/** Format A blueprint payload types (mirror of backend/app/schemas/blueprint.py). */

export interface BusinessProfile {
  model_type: string
  stage: string
  industry: string
  geography: string
}

export interface RevenueStream {
  name: string
  pricing_model: string
  price_point: number
  projected_customers_month_12: number
  ltv: number
  cac: number
  churn_monthly: number
}

export interface TeamMember {
  role: string
  salary_annual: number
  hire_month: number
}

export interface CostStructure {
  fixed_monthly: number
  variable_per_unit: number
  team: TeamMember[]
  burn_rate_month_1: number
}

export interface FundingRound {
  month: number
  amount: number
}

export interface Financials {
  starting_capital: number
  funding_rounds: FundingRound[]
  target_runway_months: number
}

export interface Vulnerability {
  type: string
  severity: 'low' | 'medium' | 'high'
  description: string
  mitigation_suggestion: string
}

export interface SimulationParameters {
  time_step: 'monthly'
  monte_carlo_runs: number
  random_seed: number | null
}

export interface BlueprintPayload {
  blueprint_version: string
  business_profile: BusinessProfile
  revenue_engine: { streams: RevenueStream[] }
  cost_structure: CostStructure
  financials: Financials
  identified_vulnerabilities: Vulnerability[]
  simulation_parameters: SimulationParameters
}

export function emptyBlueprintPayload(): BlueprintPayload {
  return {
    blueprint_version: '1.0',
    business_profile: {
      model_type: 'SaaS',
      stage: 'Seed',
      industry: '',
      geography: 'North America',
    },
    revenue_engine: { streams: [] },
    cost_structure: {
      fixed_monthly: 0,
      variable_per_unit: 0,
      team: [],
      burn_rate_month_1: 0,
    },
    financials: {
      starting_capital: 0,
      funding_rounds: [],
      target_runway_months: 18,
    },
    identified_vulnerabilities: [],
    simulation_parameters: {
      time_step: 'monthly',
      monte_carlo_runs: 100,
      random_seed: null,
    },
  }
}

/** Options for the wizard's select inputs (spec §9 Phase 2). */
export const MODEL_TYPES = ['SaaS', 'D2C', 'Retail', 'Restaurant', 'Fintech', 'Other']
export const STAGES = ['Idea', 'MVP', 'Pre-Seed', 'Seed', 'Series A+']
export const GEOGRAPHIES = [
  'North America',
  'Europe',
  'Asia-Pacific',
  'India',
  'Latin America',
  'Global',
]
export const PRICING_MODELS = ['Subscription', 'One-time', 'Usage-based', 'Freemium', 'Marketplace']

export interface ValidationIssue {
  code: string
  severity: 'error' | 'warning'
  field: string
  message: string
}

export interface ValidationReport {
  is_valid: boolean
  errors: ValidationIssue[]
  warnings: ValidationIssue[]
}

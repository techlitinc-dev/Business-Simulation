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

/**
 * Client-side mirror of the backend's structural validation rules
 * (backend/app/services/blueprint_service.py). Runs against the *current*
 * draft so the Finish button reflects what the user has typed, not the last
 * server-saved version (which lags behind by the debounce + round-trip).
 */
export function validateDraft(payload: BlueprintPayload): ValidationReport {
  const errors: ValidationIssue[] = []
  const warnings: ValidationIssue[] = []

  const streams = payload.revenue_engine.streams
  if (!streams || streams.length === 0) {
    errors.push({
      code: 'NO_REVENUE_STREAMS',
      severity: 'error',
      field: 'revenue_engine.streams',
      message: 'At least one revenue stream is required.',
    })
  }

  for (const stream of streams ?? []) {
    const base = `revenue_engine.streams[${stream.name || 'unnamed'}]`
    if (stream.cac > 0 && stream.ltv / stream.cac < 3) {
      warnings.push({
        code: 'LTV_CAC_RATIO',
        severity: 'warning',
        field: `${base}.ltv`,
        message:
          'Your LTV:CAC ratio is below 3:1. Consider raising prices or reducing churn.',
      })
    }
    if (stream.ltv < stream.cac) {
      errors.push({
        code: 'NEGATIVE_UNIT_ECONOMICS',
        severity: 'error',
        field: `${base}.ltv`,
        message: 'LTV is less than CAC, so each customer is acquired at a loss.',
      })
    }
    if (
      stream.price_point > 0 &&
      payload.cost_structure.variable_per_unit >= stream.price_point
    ) {
      errors.push({
        code: 'NEGATIVE_CONTRIBUTION_MARGIN',
        severity: 'error',
        field: `${base}.price_point`,
        message: 'Variable cost per unit meets or exceeds the price point.',
      })
    }
  }

  const burn = payload.cost_structure.burn_rate_month_1
  if (burn > 0) {
    const runway = payload.financials.starting_capital / burn
    if (runway < payload.financials.target_runway_months) {
      warnings.push({
        code: 'INSUFFICIENT_RUNWAY',
        severity: 'warning',
        field: 'financials.starting_capital',
        message: `Starting capital covers only ${runway.toFixed(1)} months of burn, below the ${payload.financials.target_runway_months}-month target.`,
      })
    }
  }

  return { is_valid: errors.length === 0, errors, warnings }
}

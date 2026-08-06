/** Simulation contracts mirroring backend/app/schemas/simulation.py. */

export type RunStatus =
  | 'pending'
  | 'running'
  | 'awaiting_decision'
  | 'paused'
  | 'completed'
  | 'dead'
  | 'cancelled'
  | 'failed'

export type RunMode = 'baseline' | 'stress' | 'monte_carlo' | 'ghost'

export interface SimulationConfig {
  months: number
  difficulty: 'standard' | 'hard' | 'nightmare'
  n_runs: number
}

export interface SimulationRun {
  id: string
  workspace_id: string
  blueprint_version_id: string
  mode: RunMode
  status: RunStatus
  seed: number
  current_month: number
  config: Partial<SimulationConfig> & Record<string, unknown>
  result: Record<string, unknown> | null
  progress: { completed: number; total: number; percent: number } | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface TickLog {
  id: string
  run_id: string
  month: number
  kpis: Record<string, number>
}

/** Format B hurdle (spec §10) as persisted in SimulationEvent.payload. */
export interface HurdleNarrative {
  title: string
  story: string
  source_actor: string
  believability_score: number
}

export interface ImmediateDeltas {
  cac_delta_percent?: number | null
  churn_delta_percent?: number | null
  new_signups_delta_percent?: number | null
  team_morale_delta?: number | null
  cash_burn_delta_monthly?: number | null
  mrr_delta_percent?: number | null
}

export interface MechanicalImpact {
  immediate: ImmediateDeltas
  cascading: Record<string, string>
}

export interface StrategicOption {
  option_id: string
  name: string
  description: string
  cash_impact_monthly: number
  probability_success: number
  second_order_risk: string
  required_execution: string
}

export interface OptionProjection {
  option_id: string
  monthly_cash: number[]
  end_cash: number
  min_cash: number
  survives: boolean
  runway_months: number
}

export interface HurdleEvent {
  event_id: string
  trigger_timing: string
  category: 'market' | 'operational' | 'financial' | 'black_swan' | 'internal'
  narrative: HurdleNarrative
  mechanical_impact: MechanicalImpact
  strategic_options?: StrategicOption[]
  options_projection?: OptionProjection[]
  ai_game_master_note: string
  chosen_option_id?: string
}

export type WsEnvelope =
  | { type: 'snapshot'; data: SimulationRun }
  | { type: 'tick'; data: { month: number; kpis: Record<string, number> } }
  | { type: 'event'; data: HurdleEvent }
  | { type: 'status'; data: { status: RunStatus } }
  | { type: 'progress'; data: { completed: number; total: number; percent: number } }

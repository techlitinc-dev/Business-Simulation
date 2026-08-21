import { useBlueprintDraftStore } from '@/stores/blueprint'
import { Field } from './fields'

export default function ReviewStep() {
  const draft = useBlueprintDraftStore((s) => s.draft)
  const { payload } = draft

  const totalMonthlySalary =
    payload.cost_structure.team.reduce((sum, m) => sum + m.salary_annual, 0) / 12

  return (
    <div className="space-y-6">
      <section className="space-y-2">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Profile
        </h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Name">
            <p className="text-sm">{draft.name || '—'}</p>
          </Field>
          <Field label="Model type">
            <p className="text-sm">{payload.business_profile.model_type}</p>
          </Field>
          <Field label="Stage">
            <p className="text-sm">{payload.business_profile.stage}</p>
          </Field>
          <Field label="Industry">
            <p className="text-sm">{payload.business_profile.industry || '—'}</p>
          </Field>
        </div>
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Revenue streams
        </h3>
        {payload.revenue_engine.streams.length === 0 ? (
          <p className="text-sm text-muted-foreground">No streams added.</p>
        ) : (
          <ul className="divide-y divide-border">
            {payload.revenue_engine.streams.map((s, i) => {
              const ratio = s.cac > 0 ? s.ltv / s.cac : 0
              return (
                <li key={i} className="flex items-center justify-between py-2 text-sm">
                  <span>
                    {s.name || `Stream ${i + 1}`} — ${s.price_point}/mo, {s.projected_customers_month_12} customers
                  </span>
                  <span className="text-muted-foreground">LTV:CAC {ratio.toFixed(1)}:1</span>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Costs & team
        </h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Fixed monthly">
            <p className="text-sm">${payload.cost_structure.fixed_monthly.toLocaleString()}</p>
          </Field>
          <Field label="Burn (month 1)">
            <p className="text-sm">${payload.cost_structure.burn_rate_month_1.toLocaleString()}</p>
          </Field>
          <Field label="Monthly payroll">
            <p className="text-sm">${totalMonthlySalary.toLocaleString()}</p>
          </Field>
        </div>
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Financials
        </h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Starting capital">
            <p className="text-sm">${payload.financials.starting_capital.toLocaleString()}</p>
          </Field>
          <Field label="Target runway">
            <p className="text-sm">{payload.financials.target_runway_months} months</p>
          </Field>
        </div>
        {payload.financials.funding_rounds.length > 0 && (
          <ul className="divide-y divide-border">
            {payload.financials.funding_rounds.map((r, i) => (
              <li key={i} className="flex justify-between py-1 text-sm">
                <span>Month {r.month}</span>
                <span>${r.amount.toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Vulnerabilities
        </h3>
        {payload.identified_vulnerabilities.length === 0 ? (
          <p className="text-sm text-muted-foreground">No vulnerabilities identified.</p>
        ) : (
          <ul className="divide-y divide-border">
            {payload.identified_vulnerabilities.map((v, i) => (
              <li key={i} className="py-2 text-sm">
                <span className="font-medium">{v.type}</span>{' '}
                <span className="text-muted-foreground">({v.severity})</span>
                <p>{v.description}</p>
                {v.mitigation_suggestion && (
                  <p className="text-muted-foreground">
                    Mitigation: {v.mitigation_suggestion}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Simulation settings
        </h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Time step">
            <p className="text-sm">{payload.simulation_parameters.time_step}</p>
          </Field>
          <Field label="Monte Carlo runs">
            <p className="text-sm">{payload.simulation_parameters.monte_carlo_runs}</p>
          </Field>
          <Field label="Random seed">
            <p className="text-sm">
              {payload.simulation_parameters.random_seed ?? '—'}
            </p>
          </Field>
        </div>
      </section>
    </div>
  )
}

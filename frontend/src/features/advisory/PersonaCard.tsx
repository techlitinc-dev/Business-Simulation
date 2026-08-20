import type { PersonaReview } from './api'

const PERSONA_COLORS: Record<string, string> = {
  CFO: 'border-blue-500',
  CMO: 'border-green-500',
  RiskAuditor: 'border-red-500',
  Operator: 'border-amber-500',
}
const PERSONA_ICONS: Record<string, string> = {
  CFO: '💼',
  CMO: '📈',
  RiskAuditor: '🛡️',
  Operator: '⚙️',
}

export function PersonaCard({ review }: { review: PersonaReview }) {
  const borderColor = PERSONA_COLORS[review.persona] ?? 'border-slate-600'
  const icon = PERSONA_ICONS[review.persona] ?? '👤'
  const riskColor =
    review.confidence_level === 'HIGH'
      ? 'text-green-400'
      : review.confidence_level === 'MEDIUM'
        ? 'text-yellow-400'
        : 'text-red-400'

  return (
    <div className={`bg-slate-800 border ${borderColor} rounded-lg p-4 space-y-3`}>
      <div className="flex items-center justify-between">
        <span className="font-semibold text-white">
          {icon} {review.persona}
        </span>
        <span className={`text-xs ${riskColor}`}>{review.confidence_level}</span>
      </div>
      <p className="text-slate-300 text-sm italic">"{review.verdict}"</p>
      <div>
        <p className="text-slate-400 text-xs font-semibold uppercase tracking-wide mb-1">
          Top Concerns
        </p>
        <ul className="space-y-1">
          {review.top_concerns.map((c, i) => (
            <li key={i} className="text-red-300 text-xs flex gap-1">
              <span>⚠️</span>
              {c}
            </li>
          ))}
        </ul>
      </div>
      {review.opportunities?.length > 0 && (
        <div>
          <p className="text-slate-400 text-xs font-semibold uppercase tracking-wide mb-1">
            Opportunities
          </p>
          <ul className="space-y-1">
            {review.opportunities.map((o, i) => (
              <li key={i} className="text-green-300 text-xs flex gap-1">
                <span>✅</span>
                {o}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

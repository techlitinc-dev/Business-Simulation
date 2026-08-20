import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { sendCopilotMessage } from '@/features/copilot/api'

interface Props {
  runId: string
  optionLabel: string
}

export function DecisionCoach({ runId, optionLabel }: Props) {
  const [opinion, setOpinion] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function getOpinion() {
    setLoading(true)
    try {
      const res = await sendCopilotMessage(
        runId,
        `I'm about to choose: "${optionLabel}". What are the risks of this decision based on the simulation data?`,
      )
      setOpinion(res.answer)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mt-3">
      <Button
        variant="outline"
        size="sm"
        onClick={getOpinion}
        disabled={loading}
        className="border-amber-600 text-amber-400 hover:bg-amber-900/30"
      >
        {loading ? 'Consulting AI…' : '🤔 Get Second Opinion'}
      </Button>
      {opinion && (
        <div className="mt-2 bg-amber-950/30 border border-amber-700 rounded p-3 text-sm text-slate-200">
          {opinion}
        </div>
      )}
    </div>
  )
}

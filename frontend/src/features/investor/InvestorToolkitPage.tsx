import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataRoomManager } from './DataRoomManager'
import { downloadBlob, generatePitchDeck, generateTeaser } from './api'

interface Props {
  runId: string
}

export function InvestorToolkitPage({ runId }: Props) {
  const [loading, setLoading] = useState<string | null>(null)

  async function handle(action: string, fn: () => Promise<Blob>, filename: string) {
    setLoading(action)
    try {
      const blob = await fn()
      downloadBlob(blob, filename)
    } finally {
      setLoading(null)
    }
  }

  const actions = [
    {
      id: 'teaser',
      icon: '📄',
      title: 'Investment Teaser',
      desc: '1-page summary for warm introductions. Problem, model, simulation validation, key ask.',
      onClick: () => handle('teaser', () => generateTeaser(runId), `teaser_${runId}.pdf`),
    },
    {
      id: 'pitch',
      icon: '📊',
      title: 'Pitch Deck Outline',
      desc: '10–12 slide outline with data-grounded talking points ready for your deck.',
      onClick: () => handle('pitch', () => generatePitchDeck(runId), `pitch_${runId}.pdf`),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        {actions.map((action) => (
          <Card key={action.id} className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-base">
                {action.icon} {action.title}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-slate-400 text-sm">{action.desc}</p>
              <Button
                onClick={action.onClick}
                disabled={loading === action.id}
                className="bg-blue-600 hover:bg-blue-700 w-full"
              >
                {loading === action.id ? 'Generating…' : `Generate ${action.title}`}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white text-base">🔐 Investor Data Room</CardTitle>
          <p className="text-slate-400 text-sm">
            Create expiring, view-tracked bundles for investors.
          </p>
        </CardHeader>
        <CardContent>
          <DataRoomManager runId={runId} />
        </CardContent>
      </Card>
    </div>
  )
}

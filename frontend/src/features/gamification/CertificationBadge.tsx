import { Award, Download } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useCertification } from '@/features/gamification/api'

interface Props {
  runId: string
  percentile?: number
}

/** "Forge-Validated Business" badge with a certification PDF download button. */
export function CertificationBadge({ runId, percentile = 90 }: Props) {
  const certification = useCertification(runId)

  return (
    <Card className="border-amber-500/40 bg-gradient-to-br from-amber-500/10 to-slate-800">
      <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🏆</span>
          <div>
            <p className="text-white font-semibold">Forge-Validated Business</p>
            <Badge className="mt-1 border-amber-500/40 bg-amber-500/10 text-amber-300">
              Top {percentile}th percentile
            </Badge>
          </div>
        </div>
        <Button
          onClick={() => certification.mutate()}
          disabled={certification.isPending}
        >
          <Download className="h-4 w-4" />
          {certification.isPending ? 'Generating…' : 'Certificate PDF'}
        </Button>
      </CardContent>
    </Card>
  )
}

export { Award }

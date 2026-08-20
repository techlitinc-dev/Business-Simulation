import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CohortRankings } from './CohortRankings'
import { PortfolioDashboard } from './PortfolioDashboard'
import { usePortfolioSummary } from './api'

interface Props {
  portfolioId: string
}

export function PortfolioPage({ portfolioId }: Props) {
  const { data } = usePortfolioSummary(portfolioId)

  return (
    <div className="space-y-6">
      <PortfolioDashboard portfolioId={portfolioId} />

      {data && data.workspaces.length > 1 && (
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white text-base">Rankings</CardTitle>
          </CardHeader>
          <CardContent>
            <CohortRankings workspaces={data.workspaces} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}

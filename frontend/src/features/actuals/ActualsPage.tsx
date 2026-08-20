import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ActualsUploadPage } from './ActualsUploadPage'
import { RollingForecastTimeline } from './RollingForecastTimeline'
import { VarianceReportPage } from './VarianceReportPage'
import { useActualsHistory } from './api'

interface Props {
  blueprintId: string
}

export function ActualsPage({ blueprintId }: Props) {
  const queryClient = useQueryClient()
  const { data: history = [] } = useActualsHistory(blueprintId)
  const [refreshKey, setRefreshKey] = useState(0)

  function handleUploadSuccess() {
    void queryClient.invalidateQueries({ queryKey: ['actuals', blueprintId] })
    setRefreshKey((k) => k + 1)
  }

  return (
    <div className="space-y-6">
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Import Actuals</CardTitle>
        </CardHeader>
        <CardContent>
          <ActualsUploadPage blueprintId={blueprintId} onSuccess={handleUploadSuccess} />
        </CardContent>
      </Card>

      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white">Rolling Forecast Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <RollingForecastTimeline history={history} />
        </CardContent>
      </Card>

      <VarianceReportPage key={refreshKey} blueprintId={blueprintId} />
    </div>
  )
}

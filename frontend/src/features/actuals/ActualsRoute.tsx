import { useParams } from 'react-router-dom'

import { ActualsPage } from './ActualsPage'

/** Route wrapper: resolves the blueprintId param for the actuals page. */
export default function ActualsRoute() {
  const { blueprintId } = useParams<{ blueprintId: string }>()
  if (!blueprintId) return null
  return <ActualsPage blueprintId={blueprintId} />
}

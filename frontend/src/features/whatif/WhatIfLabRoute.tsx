import { useParams } from 'react-router-dom'

import { WhatIfLabPage } from './WhatIfLabPage'

/** Route wrapper: resolves the blueprintId param for the lab. */
export default function WhatIfLabRoute() {
  const { blueprintId } = useParams<{ blueprintId: string }>()
  if (!blueprintId) return null
  return <WhatIfLabPage blueprintId={blueprintId} />
}

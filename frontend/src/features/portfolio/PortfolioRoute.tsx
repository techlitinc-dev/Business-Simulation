import { useParams } from 'react-router-dom'

import { PortfolioPage } from './PortfolioPage'

/** Route wrapper: resolves the portfolioId param. */
export default function PortfolioRoute() {
  const { portfolioId } = useParams<{ portfolioId: string }>()
  if (!portfolioId) return null
  return <PortfolioPage portfolioId={portfolioId} />
}

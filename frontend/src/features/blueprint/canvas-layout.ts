import type { Edge, Node } from '@xyflow/react'

import type { BlueprintPayload } from './types'

export interface CanvasNodeData {
  label: string
  kind: string
  severity?: 'low' | 'medium' | 'high'
  ltvCacRatio?: number
  risk?: 'bad' | 'ok'
  detail?: string
  items?: { label: string; value: string }[]
  [key: string]: unknown
}

export type CanvasNode = Node<CanvasNodeData>
export type CanvasEdge = Edge

const LTV_CAC_THRESHOLD = 3

/** Convert a Format A blueprint payload into a deterministic React Flow layout.
 *
 * Layout (hand-computed, no auto-layout):
 * - business at (0, 0)
 * - revenue streams stacked at x = -400
 * - cost + team at x = +400
 * - vulnerabilities below the business node
 */
export function blueprintToFlow(payload: BlueprintPayload): {
  nodes: CanvasNode[]
  edges: CanvasEdge[]
} {
  const nodes: CanvasNode[] = []
  const edges: CanvasEdge[] = []

  const profile = payload.business_profile

  nodes.push({
    id: 'business',
    type: 'business',
    position: { x: 0, y: 0 },
    data: {
      label: profile.industry || 'Business',
      kind: 'business',
      detail: `${profile.model_type} · ${profile.stage} · ${profile.geography}`,
    },
  })

  const streams = payload.revenue_engine.streams
  streams.forEach((stream, i) => {
    const ratio = stream.cac > 0 ? stream.ltv / stream.cac : 0
    const m12Revenue = stream.price_point * stream.projected_customers_month_12
    nodes.push({
      id: `stream-${i}`,
      type: 'revenue',
      position: { x: -400, y: i * 140 - ((streams.length - 1) * 140) / 2 },
      data: {
        label: stream.name || `Stream ${i + 1}`,
        kind: 'revenue',
        ltvCacRatio: ratio,
        risk: ratio < LTV_CAC_THRESHOLD ? 'bad' : 'ok',
        items: [
          { label: 'Price', value: `$${stream.price_point}` },
          { label: 'Customers (M12)', value: String(stream.projected_customers_month_12) },
          { label: 'LTV:CAC', value: ratio.toFixed(1) },
        ],
      },
    })
    edges.push({
      id: `edge-stream-${i}`,
      source: `stream-${i}`,
      target: 'business',
      animated: true,
      label: `$${m12Revenue.toLocaleString()} M12`,
      labelStyle: { fill: '#94a3b8', fontSize: 11 },
    })
  })

  nodes.push({
    id: 'cost',
    type: 'cost',
    position: { x: 400, y: -60 },
    data: {
      label: 'Costs',
      kind: 'cost',
      items: [
        { label: 'Fixed monthly', value: `$${payload.cost_structure.fixed_monthly.toLocaleString()}` },
        { label: 'Burn (M1)', value: `$${payload.cost_structure.burn_rate_month_1.toLocaleString()}` },
      ],
    },
  })
  edges.push({ id: 'edge-cost', source: 'business', target: 'cost', animated: false })

  const headcount = payload.cost_structure.team.length
  const totalSalary = payload.cost_structure.team.reduce(
    (sum, m) => sum + m.salary_annual,
    0,
  )
  nodes.push({
    id: 'team',
    type: 'team',
    position: { x: 400, y: 140 },
    data: {
      label: 'Team',
      kind: 'team',
      items: [
        { label: 'Headcount', value: String(headcount) },
        { label: 'Annual salaries', value: `$${totalSalary.toLocaleString()}` },
      ],
    },
  })
  edges.push({ id: 'edge-team', source: 'business', target: 'team', animated: false })

  payload.identified_vulnerabilities.forEach((vuln, i) => {
    nodes.push({
      id: `vuln-${i}`,
      type: 'vulnerability',
      position: { x: (i - (payload.identified_vulnerabilities.length - 1) / 2) * 260, y: 320 },
      data: {
        label: vuln.type,
        kind: 'vulnerability',
        severity: vuln.severity,
        detail: vuln.description,
      },
    })
    edges.push({
      id: `edge-vuln-${i}`,
      source: `vuln-${i}`,
      target: 'business',
      animated: false,
      style: vuln.severity === 'high' ? { stroke: '#ef4444', strokeDasharray: '5 5' } : undefined,
    })
  })

  return { nodes, edges }
}

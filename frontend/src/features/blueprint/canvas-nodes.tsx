import { Handle, Position, type NodeProps } from '@xyflow/react'

import { cn } from '@/lib/utils'
import type { CanvasNode, CanvasNodeData } from './canvas-layout'

const base = 'rounded-lg border bg-card px-4 py-3 text-sm shadow'

function NodeShell({
  children,
  tone,
}: {
  children: React.ReactNode
  tone?: 'bad' | 'warn' | 'default'
}) {
  return (
    <div
      className={cn(
        base,
        tone === 'bad' && 'border-destructive bg-destructive/10 text-destructive',
        tone === 'warn' && 'border-amber-500/60 bg-amber-500/10 text-amber-600 dark:text-amber-400',
      )}
    >
      {children}
    </div>
  )
}

function ItemList({ items }: { items: CanvasNodeData['items'] }) {
  if (!items || items.length === 0) return null
  return (
    <dl className="mt-2 space-y-0.5 text-xs text-muted-foreground">
      {items.map((item) => (
        <div key={item.label} className="flex justify-between gap-3">
          <dt>{item.label}</dt>
          <dd className="font-medium text-foreground">{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

export function BusinessNode({ data }: NodeProps<CanvasNode>) {
  return (
    <NodeShell>
      <Handle type="target" position={Position.Left} />
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Right} />
      <p className="font-semibold">{data.label}</p>
      {data.detail && <p className="text-xs text-muted-foreground">{data.detail}</p>}
    </NodeShell>
  )
}

export function RevenueStreamNode({ data }: NodeProps<CanvasNode>) {
  const tone = data.risk === 'bad' ? 'bad' : 'default'
  return (
    <NodeShell tone={tone}>
      <Handle type="source" position={Position.Right} />
      <p className="font-semibold">{data.label}</p>
      <ItemList items={data.items} />
      {data.risk === 'bad' && (
        <p className="mt-1 text-xs font-medium">Below 3:1 survival threshold</p>
      )}
    </NodeShell>
  )
}

export function CostNode({ data }: NodeProps<CanvasNode>) {
  return (
    <NodeShell>
      <Handle type="target" position={Position.Left} />
      <p className="font-semibold">{data.label}</p>
      <ItemList items={data.items} />
    </NodeShell>
  )
}

export function TeamNode({ data }: NodeProps<CanvasNode>) {
  return (
    <NodeShell>
      <Handle type="target" position={Position.Left} />
      <p className="font-semibold">{data.label}</p>
      <ItemList items={data.items} />
    </NodeShell>
  )
}

export function VulnerabilityNode({ data }: NodeProps<CanvasNode>) {
  const tone = data.severity === 'high' ? 'bad' : data.severity === 'medium' ? 'warn' : 'default'
  return (
    <NodeShell tone={tone}>
      <Handle type="source" position={Position.Top} />
      <p className="font-semibold capitalize">{data.label}</p>
      {data.severity && (
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{data.severity}</p>
      )}
      {data.detail && <p className="mt-1 text-xs text-muted-foreground">{data.detail}</p>}
    </NodeShell>
  )
}

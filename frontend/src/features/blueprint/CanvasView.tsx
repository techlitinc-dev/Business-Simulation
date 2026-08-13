import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import {
  Background,
  Controls,
  Panel,
  ReactFlow,
  type NodeTypes,
} from '@xyflow/react'

import '@xyflow/react/dist/style.css'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useBlueprint } from './api'
import { blueprintToFlow } from './canvas-layout'
import {
  BusinessNode,
  CostNode,
  RevenueStreamNode,
  TeamNode,
  VulnerabilityNode,
} from './canvas-nodes'

const nodeTypes: NodeTypes = {
  business: BusinessNode,
  revenue: RevenueStreamNode,
  cost: CostNode,
  team: TeamNode,
  vulnerability: VulnerabilityNode,
}

export default function BlueprintCanvasPage() {
  const { blueprintId } = useParams<{ blueprintId: string }>()
  const { data: blueprint, isLoading, isError } = useBlueprint(blueprintId)

  const flow = useMemo(
    () => (blueprint ? blueprintToFlow(blueprint.payload) : { nodes: [], edges: [] }),
    [blueprint],
  )

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading canvas…</p>
  }

  if (isError || !blueprint) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Blueprint not found</AlertTitle>
        <AlertDescription>
          This blueprint could not be loaded. It may have been deleted.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-4">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to={`/app/blueprints/${blueprint.id}`}>
          <ArrowLeft className="h-4 w-4" /> Back to blueprint
        </Link>
      </Button>
      <div>
        <h1 className="text-2xl font-semibold">{blueprint.name}</h1>
        <p className="text-sm text-muted-foreground">
          Model canvas — {flow.nodes.length} nodes, read-only
        </p>
      </div>
      <Card>
        <CardContent className="h-[600px] p-0">
          <ReactFlow
            nodes={flow.nodes}
            edges={flow.edges}
            nodeTypes={nodeTypes}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background />
            <Controls />
            <Panel position="bottom-left" className="rounded-md border border-border bg-card px-3 py-2 text-xs">
              <span className="mr-2 inline-block h-2 w-2 rounded-full bg-destructive" /> &lt;3:1 LTV:CAC
              <span className="mx-2 inline-block h-2 w-2 rounded-full bg-amber-500" /> medium risk
              <span className="mr-2 inline-block h-2 w-2 rounded-full bg-border" /> low risk
            </Panel>
          </ReactFlow>
        </CardContent>
      </Card>
    </div>
  )
}

import { useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useBlueprintDraftStore } from '@/stores/blueprint'
import BuilderWizard from './BuilderWizard'
import { useBlueprint } from './api'

/** Loads an existing blueprint's current payload into the draft store, then
 * renders the same wizard used for new blueprints (edits save as v+1). */
export default function BlueprintEditPage() {
  const { blueprintId } = useParams<{ blueprintId: string }>()
  const { data: blueprint, isLoading, isError } = useBlueprint(blueprintId)

  const setDraft = useBlueprintDraftStore((s) => s.setDraftFromBlueprint)

  useEffect(() => {
    if (blueprint) {
      setDraft({
        name: blueprint.name,
        industry: blueprint.industry,
        stage: blueprint.stage,
        payload: blueprint.payload,
        blueprintId: blueprint.id,
      })
    }
  }, [blueprint, setDraft])

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading blueprint…</p>
  }

  if (isError || !blueprint) {
    return <p className="text-sm text-destructive">Blueprint not found.</p>
  }

  return (
    <div className="space-y-4">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to={`/app/blueprints/${blueprint.id}`}>
          <ArrowLeft className="h-4 w-4" /> Back to blueprint
        </Link>
      </Button>
      <Card>
        <CardContent className="p-6">
          <BuilderWizard />
        </CardContent>
      </Card>
    </div>
  )
}

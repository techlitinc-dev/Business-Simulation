import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Copy, GitFork } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { toastSuccess } from '@/lib/toast'
import { useAuthStore } from '@/stores/auth-store'
import { useCloneScenario, useScenario } from './api'

export default function ScenarioDetailPage() {
  const { scenarioId } = useParams<{ scenarioId: string }>()
  const { data, isLoading } = useScenario(scenarioId)
  const clone = useCloneScenario()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const navigate = useNavigate()
  const backPath = isAuthenticated ? '/app/marketplace' : '/marketplace'

  const handleClone = () => {
    if (!scenarioId) return
    if (!isAuthenticated) {
      navigate('/register')
      return
    }
    clone.mutate(scenarioId, {
      onSuccess: () => {
        toastSuccess('Scenario cloned into your blueprints')
      },
    })
  }

  if (isLoading || !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  const payloadJson = JSON.stringify(data.payload, null, 2)

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link to={backPath}>
          <ArrowLeft className="h-4 w-4" /> Back to marketplace
        </Link>
      </Button>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold">{data.title}</h1>
            {data.is_featured && (
              <Badge className="border-warning/40 bg-warning/10 text-warning">
                Featured
              </Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{data.description}</p>
        </div>
        <Button onClick={handleClone} disabled={clone.isPending}>
          <Copy className="h-4 w-4" />
          {clone.isPending ? 'Cloning…' : 'Clone to my workspace'}
        </Button>
      </div>

      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        <span className="flex items-center gap-1">
          <GitFork className="h-4 w-4" /> {data.clones_count} clones
        </span>
        <Badge className="border-border bg-muted/40">{data.category}</Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Blueprint payload</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="prose-sm prose prose-invert max-w-none">
            <ReactMarkdown>{`\`\`\`json\n${payloadJson}\n\`\`\``}</ReactMarkdown>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

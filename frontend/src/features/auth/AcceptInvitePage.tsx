import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useWorkspaceStore } from '@/stores/workspace-store'
import { useQueryClient } from '@tanstack/react-query'

export default function AcceptInvitePage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setActive = useWorkspaceStore((s) => s.setActive)
  const [error, setError] = useState<string | null>(null)

  const accept = useMutation({
    mutationFn: () =>
      apiFetch<{ workspace_id: string; role: string }>(
        `/api/v1/invites/${token}/accept`,
        { method: 'POST' },
      ),
    onSuccess: (result) => {
      setActive(result.workspace_id)
      void queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      navigate('/app/settings/members', { replace: true })
    },
    onError: (err: unknown) => {
      setError(err instanceof Error ? err.message : 'Could not accept invite')
    },
  })

  useEffect(() => {
    if (token) accept.mutate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <CardTitle>Accept invite</CardTitle>
          <CardDescription>
            {error ? 'This invite could not be accepted.' : 'Joining workspace…'}
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center text-sm">
          {error ? (
            <p className="text-destructive">{error}</p>
          ) : accept.isPending ? (
            <p className="text-muted-foreground">Please wait…</p>
          ) : (
            <p className="text-muted-foreground">Done!</p>
          )}
        </CardContent>
        {error && (
          <CardFooter className="justify-center">
            <Button variant="outline" onClick={() => navigate('/app')}>
              Go to dashboard
            </Button>
          </CardFooter>
        )}
      </Card>
    </div>
  )
}

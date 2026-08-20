import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ApiError } from '@/lib/api-client'
import { createDataRoom, revokeDataRoom } from './api'
import type { DataRoom } from './api'

interface Props {
  runId: string
}

export function DataRoomManager({ runId }: Props) {
  const [rooms, setRooms] = useState<DataRoom[]>([])
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleCreate() {
    setCreating(true)
    setError(null)
    try {
      const room = await createDataRoom(runId, 'Investor Data Room')
      setRooms((prev) => [room, ...prev])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to create data room')
    } finally {
      setCreating(false)
    }
  }

  async function handleRevoke(token: string) {
    await revokeDataRoom(token)
    setRooms((prev) => prev.filter((r) => r.token !== token))
  }

  return (
    <div className="space-y-3">
      <Button
        onClick={handleCreate}
        disabled={creating}
        className="bg-green-600 hover:bg-green-700"
      >
        {creating ? 'Creating…' : '🔗 Create Data Room Link'}
      </Button>
      {error && <p className="text-red-400 text-sm">{error}</p>}

      {rooms.map((room) => (
        <Card key={room.token} className="bg-slate-700 border-slate-600">
          <CardContent className="py-3 flex items-center justify-between">
            <div>
              <div className="text-white text-sm font-medium">{room.label}</div>
              <div className="text-slate-400 text-xs">
                Expires: {new Date(room.expires_at).toLocaleDateString()} · Token: {room.token}
              </div>
            </div>
            <div className="flex gap-2">
              <a
                href={room.download_url}
                target="_blank"
                rel="noreferrer"
                className="text-blue-400 hover:text-blue-300 text-xs"
              >
                Open Link
              </a>
              <button
                onClick={() => handleRevoke(room.token)}
                className="text-red-400 hover:text-red-300 text-xs"
              >
                Revoke
              </button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

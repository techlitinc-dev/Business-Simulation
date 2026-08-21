import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  useComments,
  usePostComment,
} from '@/features/collaboration/api'
import type { CommentTargetType } from '@/features/collaboration/api'

interface Props {
  targetType: CommentTargetType
  targetId: string
}

export function CommentThread({ targetType, targetId }: Props) {
  const [input, setInput] = useState('')
  const { data: comments = [] } = useComments(targetType, targetId)
  const post = usePostComment(targetType, targetId)

  function handlePost() {
    if (!input.trim() || post.isPending) return
    post.mutate(input.trim(), {
      onSuccess: () => setInput(''),
    })
  }

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {comments.map((c) => (
          <div key={c.id} className="bg-slate-700 rounded p-3 text-sm">
            <span className="text-slate-400 text-xs">{c.author_user_id}</span>
            <p className="text-white mt-1">{c.body}</p>
          </div>
        ))}
        {comments.length === 0 && (
          <p className="text-slate-500 text-sm">No comments yet.</p>
        )}
      </div>
      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Add comment… @mention users"
          className="flex-1 bg-slate-700 border-slate-600 text-white"
          onKeyDown={(e) => e.key === 'Enter' && handlePost()}
        />
        <Button onClick={handlePost} disabled={post.isPending || !input.trim()}>
          Post
        </Button>
      </div>
    </div>
  )
}

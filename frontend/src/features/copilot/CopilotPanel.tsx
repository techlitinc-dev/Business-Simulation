import { useEffect, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/api-client'
import { sendCopilotMessage } from './api'
import type { ChatMessage } from './api'
import { ChatBubble } from './ChatBubble'

interface Message extends ChatMessage {
  grounded?: boolean
  flaggedClaims?: string[]
}

export function CopilotPanel({ runId }: { runId: string }) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend() {
    if (!input.trim() || loading) return
    const question = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setLoading(true)
    try {
      const history: ChatMessage[] = messages.map((m) => ({ role: m.role, content: m.content }))
      const res = await sendCopilotMessage(runId, question, history)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.answer,
          grounded: res.grounded,
          flaggedClaims: res.flagged_claims,
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: err instanceof ApiError ? err.message : 'Copilot unavailable right now.',
          grounded: false,
          flaggedClaims: [],
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 bg-blue-600 hover:bg-blue-700 text-white rounded-full p-4 shadow-lg z-50"
      >
        💬
      </button>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[520px] bg-slate-900 border border-slate-700 rounded-xl shadow-2xl flex flex-col z-50">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <span className="text-white font-semibold text-sm">Ask About This Run</span>
        <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-white">
          ✕
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="text-slate-500 text-sm text-center mt-8">
            Ask anything about this simulation.
            <br />
            <span className="text-xs">e.g. "Why did cash dip in month 9?"</span>
          </p>
        )}
        {messages.map((m, i) => (
          <ChatBubble key={i} {...m} />
        ))}
        {loading && <div className="text-slate-400 text-sm animate-pulse">Thinking…</div>}
        <div ref={bottomRef} />
      </div>
      <div className="p-3 border-t border-slate-700 flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask a question…"
          className="bg-slate-700 border-slate-600 text-white text-sm"
        />
        <Button onClick={handleSend} disabled={loading} size="sm" className="bg-blue-600">
          Send
        </Button>
      </div>
    </div>
  )
}

interface Props {
  role: 'user' | 'assistant'
  content: string
  grounded?: boolean
  flaggedClaims?: string[]
}

export function ChatBubble({ role, content, grounded, flaggedClaims = [] }: Props) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-3 text-sm ${
          isUser ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-200'
        }`}
      >
        {content}
        {!isUser && grounded !== undefined && (
          <div className="mt-2 flex items-center gap-2">
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                grounded ? 'bg-green-900/50 text-green-300' : 'bg-red-900/50 text-red-300'
              }`}
            >
              {grounded ? '✅ Grounded in data' : '⚠️ Unverified claim'}
            </span>
          </div>
        )}
        {flaggedClaims.length > 0 && (
          <p className="text-red-300 text-xs mt-1">Flagged: {flaggedClaims.join(', ')}</p>
        )}
      </div>
    </div>
  )
}

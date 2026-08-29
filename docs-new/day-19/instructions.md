# Day 19 — F-02: Copilot Chat UI + Decision Coach (War Room)

## Feature
F-02: AI Advisory Board & Copilot

## Goal
Build the collapsible CopilotPanel on the Simulation Runner page (chat with grounding badges), and add a "Get Second Opinion" button to the War Room decision modal.

---

## Step 1 — `frontend/src/features/copilot/api.ts`

```typescript
import { apiClient } from "@/lib/api";

export interface ChatResponse {
  answer: string;
  sources_used: string[];
  confidence: "LOW" | "MEDIUM" | "HIGH";
  grounded: boolean;
  flagged_claims: string[];
}

export async function sendCopilotMessage(runId: string, question: string, history: any[] = []): Promise<ChatResponse> {
  const res = await apiClient.post<ChatResponse>(`/simulations/${runId}/chat`, { question, history });
  return res.data;
}
```

---

## Step 2 — `ChatBubble.tsx`

```typescript
// frontend/src/features/copilot/ChatBubble.tsx
interface Props {
  role: "user" | "assistant";
  content: string;
  grounded?: boolean;
  flaggedClaims?: string[];
}

export function ChatBubble({ role, content, grounded, flaggedClaims = [] }: Props) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-[85%] rounded-lg px-4 py-3 text-sm ${
        isUser ? "bg-blue-600 text-white" : "bg-slate-700 text-slate-200"
      }`}>
        {content}
        {!isUser && grounded !== undefined && (
          <div className="mt-2 flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full ${grounded ? "bg-green-900/50 text-green-300" : "bg-red-900/50 text-red-300"}`}>
              {grounded ? "✅ Grounded in data" : "⚠️ Unverified claim"}
            </span>
          </div>
        )}
        {flaggedClaims.length > 0 && (
          <p className="text-red-300 text-xs mt-1">
            Flagged: {flaggedClaims.join(", ")}
          </p>
        )}
      </div>
    </div>
  );
}
```

---

## Step 3 — `CopilotPanel.tsx`

```typescript
// frontend/src/features/copilot/CopilotPanel.tsx
import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChatBubble } from "./ChatBubble";
import { sendCopilotMessage } from "./api";

interface Message { role: "user" | "assistant"; content: string; grounded?: boolean; flaggedClaims?: string[]; }

export function CopilotPanel({ runId }: { runId: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function handleSend() {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: question }]);
    setLoading(true);
    try {
      const res = await sendCopilotMessage(runId, question, messages.map(m => ({ role: m.role, content: m.content })));
      setMessages(prev => [...prev, {
        role: "assistant", content: res.answer,
        grounded: res.grounded, flaggedClaims: res.flagged_claims,
      }]);
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 bg-blue-600 hover:bg-blue-700 text-white rounded-full p-4 shadow-lg z-50">
        💬
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[520px] bg-slate-900 border border-slate-700 rounded-xl shadow-2xl flex flex-col z-50">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <span className="text-white font-semibold text-sm">Ask About This Run</span>
        <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-white">✕</button>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="text-slate-500 text-sm text-center mt-8">
            Ask anything about this simulation.<br />
            <span className="text-xs">e.g. "Why did cash dip in month 9?"</span>
          </p>
        )}
        {messages.map((m, i) => <ChatBubble key={i} {...m} />)}
        {loading && <div className="text-slate-400 text-sm animate-pulse">Thinking…</div>}
        <div ref={bottomRef} />
      </div>
      <div className="p-3 border-t border-slate-700 flex gap-2">
        <Input
          value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSend()}
          placeholder="Ask a question…"
          className="bg-slate-700 border-slate-600 text-white text-sm"
        />
        <Button onClick={handleSend} disabled={loading} size="sm" className="bg-blue-600">Send</Button>
      </div>
    </div>
  );
}
```

---

## Step 4 — `DecisionCoach.tsx` in War Room

```typescript
// frontend/src/features/warroom/DecisionCoach.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { sendCopilotMessage } from "@/features/copilot/api";

interface Props { runId: string; optionLabel: string; }

export function DecisionCoach({ runId, optionLabel }: Props) {
  const [opinion, setOpinion] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function getOpinion() {
    setLoading(true);
    try {
      const res = await sendCopilotMessage(
        runId,
        `I'm about to choose: "${optionLabel}". What are the risks of this decision based on the simulation data?`,
      );
      setOpinion(res.answer);
    } finally { setLoading(false); }
  }

  return (
    <div className="mt-3">
      <Button variant="outline" size="sm" onClick={getOpinion} disabled={loading}
        className="border-amber-600 text-amber-400 hover:bg-amber-900/30">
        {loading ? "Consulting AI…" : "🤔 Get Second Opinion"}
      </Button>
      {opinion && (
        <div className="mt-2 bg-amber-950/30 border border-amber-700 rounded p-3 text-sm text-slate-200">
          {opinion}
        </div>
      )}
    </div>
  );
}
```

---

## Step 5 — Wire into existing components

In `frontend/src/features/simulation/RunnerPage.tsx`:
```tsx
import { CopilotPanel } from "@/features/copilot/CopilotPanel";
// Add at bottom of JSX:
<CopilotPanel runId={runId} />
```

In `frontend/src/features/warroom/DecisionModal.tsx`:
```tsx
import { DecisionCoach } from "./DecisionCoach";
// Inside each option card:
<DecisionCoach runId={runId} optionLabel={option.label} />
```

---

## Verification Commands
```bash
cd frontend && npm run build && npm run lint
```

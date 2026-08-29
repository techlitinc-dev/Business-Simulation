# Day 24 — F-03: Investor Toolkit UI

## Feature
F-03: Investor & Lender Toolkit

## Goal
Build the "Investor Toolkit" tab on the Report page with 4 action cards (Generate Teaser, Pitch Outline, Lender Report, Create Data Room) and a Data Room Manager.

---

## Step 1 — `frontend/src/features/investor/api.ts`

```typescript
import { apiClient } from "@/lib/api";

export async function generateTeaser(runId: string): Promise<Blob> {
  const res = await apiClient.post(`/investor/runs/${runId}/teaser`, {}, { responseType: "blob" });
  return res.data;
}

export async function generatePitchDeck(runId: string): Promise<Blob> {
  const res = await apiClient.post(`/investor/runs/${runId}/pitch-deck`, {}, { responseType: "blob" });
  return res.data;
}

export async function createDataRoom(runId: string, label: string, expiryDays: number = 7) {
  const res = await apiClient.post("/dataroom/", { run_id: runId, label, expiry_days: expiryDays });
  return res.data as { token: string; download_url: string; expires_at: string; label: string };
}

export async function revokeDataRoom(token: string) {
  await apiClient.delete(`/dataroom/${token}`);
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

export { downloadBlob };
```

---

## Step 2 — `DataRoomManager.tsx`

```typescript
// frontend/src/features/investor/DataRoomManager.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { createDataRoom, revokeDataRoom } from "./api";

interface DataRoom { token: string; download_url: string; expires_at: string; label: string; }

interface Props { runId: string; }

export function DataRoomManager({ runId }: Props) {
  const [rooms, setRooms] = useState<DataRoom[]>([]);
  const [creating, setCreating] = useState(false);

  async function handleCreate() {
    setCreating(true);
    try {
      const room = await createDataRoom(runId, "Investor Data Room");
      setRooms(prev => [room, ...prev]);
    } finally { setCreating(false); }
  }

  async function handleRevoke(token: string) {
    await revokeDataRoom(token);
    setRooms(prev => prev.filter(r => r.token !== token));
  }

  return (
    <div className="space-y-3">
      <Button onClick={handleCreate} disabled={creating} className="bg-green-600 hover:bg-green-700">
        {creating ? "Creating…" : "🔗 Create Data Room Link"}
      </Button>

      {rooms.map(room => (
        <Card key={room.token} className="bg-slate-700 border-slate-600">
          <CardContent className="py-3 flex items-center justify-between">
            <div>
              <div className="text-white text-sm font-medium">{room.label}</div>
              <div className="text-slate-400 text-xs">
                Expires: {new Date(room.expires_at).toLocaleDateString()} · Token: {room.token}
              </div>
            </div>
            <div className="flex gap-2">
              <a href={room.download_url} target="_blank" rel="noreferrer"
                className="text-blue-400 hover:text-blue-300 text-xs">
                Copy Link
              </a>
              <button onClick={() => handleRevoke(room.token)}
                className="text-red-400 hover:text-red-300 text-xs">
                Revoke
              </button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

---

## Step 3 — `InvestorToolkitPage.tsx`

```typescript
// frontend/src/features/investor/InvestorToolkitPage.tsx
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DataRoomManager } from "./DataRoomManager";
import { generateTeaser, generatePitchDeck, downloadBlob } from "./api";

interface Props { runId: string; }

export function InvestorToolkitPage({ runId }: Props) {
  const [loading, setLoading] = useState<string | null>(null);

  async function handle(action: string, fn: () => Promise<Blob>, filename: string) {
    setLoading(action);
    try {
      const blob = await fn();
      downloadBlob(blob, filename);
    } finally { setLoading(null); }
  }

  const actions = [
    {
      id: "teaser",
      icon: "📄",
      title: "Investment Teaser",
      desc: "1-page summary for warm introductions. Problem, model, simulation validation, key ask.",
      onClick: () => handle("teaser", () => generateTeaser(runId), `teaser_${runId}.pdf`),
    },
    {
      id: "pitch",
      icon: "📊",
      title: "Pitch Deck Outline",
      desc: "10–12 slide outline with data-grounded talking points ready for your deck.",
      onClick: () => handle("pitch", () => generatePitchDeck(runId), `pitch_${runId}.pdf`),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        {actions.map(action => (
          <Card key={action.id} className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-base">{action.icon} {action.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-slate-400 text-sm">{action.desc}</p>
              <Button
                onClick={action.onClick}
                disabled={loading === action.id}
                className="bg-blue-600 hover:bg-blue-700 w-full"
              >
                {loading === action.id ? "Generating…" : `Generate ${action.title}`}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white text-base">🔐 Investor Data Room</CardTitle>
          <p className="text-slate-400 text-sm">Create expiring, view-tracked bundles for investors.</p>
        </CardHeader>
        <CardContent>
          <DataRoomManager runId={runId} />
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## Step 4 — Add tab to ReportPage

```tsx
<TabsTrigger value="investor">Investor Toolkit</TabsTrigger>
<TabsContent value="investor">
  <InvestorToolkitPage runId={runId} />
</TabsContent>
```

---

## Verification Commands
```bash
cd frontend && npm run build && npm run lint
```

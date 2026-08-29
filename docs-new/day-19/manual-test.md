# Day 19 — Manual Test Checklist

## Checklist

### 1. Copilot panel open/close
- [ ] Blue 💬 button visible on simulation runner
- [ ] Click opens panel with "Ask About This Run" header
- [ ] ✕ closes panel
- [ ] Panel reopens in same conversation state

### 2. Send a question
- [ ] Type "What was the survival rate?" → press Enter
- [ ] User message appears right-aligned
- [ ] "Thinking…" appears
- [ ] Answer appears with "✅ Grounded in data" badge

### 3. Grounding badge shows correctly
- [ ] Grounded answer shows green badge
- [ ] Unverifiable answer (if injected) shows red badge

### 4. Decision Coach
- [ ] Open War Room modal
- [ ] Each option shows "🤔 Get Second Opinion" button
- [ ] Click → "Consulting AI…" appears
- [ ] Amber critique box appears with analysis

### 5. Build
```bash
cd frontend && npm run build
```
- [ ] 0 errors

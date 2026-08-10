# Bug Fix Summary — The Forge (Business Simulation)

Date: 2026-08-10
Scope: Frontend (React/Vite) + deployment config; no backend code changes required.

---

## 1. Settings errors — `crypto.randomUUID is not a function` (root cause of many issues)

**Files:** `frontend/src/stores/notifications.ts`

`crypto.randomUUID()` is only available on **secure origins (HTTPS)**. The app is served over plain HTTP, so every `toastSuccess` / `toastError` call crashed inside `addNotification` — which broke Profile update, Workspace update, Member invite, Security password change, and API-key revoke. In several cases the API call had actually **succeeded**, but the crash in the success handler made the UI report failure.

**Fix:** Added a `newId()` helper that falls back to a `Math.random`-based UUID v4 when `crypto.randomUUID` is unavailable.

This single fix resolves:
- Profile: "profile update failed"
- Workspace: "workspace update failed"
- Member: "invite member" crash
- Security: password-change crash (the backend logic was fine — it returns 400 "Current password is incorrect" on a real mismatch)
- API Key: delete/revoke button crash
- Notification symbol "no action for clear" — the bell now accumulates entries, so "Clear" and "Mark all read" work

## 2. Page-not-found routes (Ghost Mode, Marketplace, Leaderboard, Billing)

**Files:** `frontend/src/router.tsx`, `frontend/src/features/billing/BillingPage.tsx` (new)

The sidebar links to `/app/ghost`, `/app/marketplace`, `/app/leaderboard`, `/app/billing`, but the router had **no routes** for them under `/app` — every click fell through to the 404 "Page not found" page.

**Fix:** Added app routes:
- `/app/ghost` → GhostSetupPage
- `/app/marketplace` → MarketplacePage
- `/app/marketplace/:scenarioId` → ScenarioDetailPage (kept the public marketing versions too)
- `/app/leaderboard` → LeaderboardPage
- `/app/billing` → new BillingPage (plan + usage meters + link to pricing)

Also made marketplace "View" / "Back to marketplace" links context-aware (authenticated users stay inside the app shell; anonymous users use the public marketing routes).

## 3. Dashboard: War Room not clickable

**Files:** `frontend/src/components/layout/Topbar.tsx`

The Topbar breadcrumb "War Room" was a plain `<span>`. Made it a `<Link>` to `/app/simulations` (the War Room hub), with hover styling.

## 4. Dashboard: Cash curve & MRR-vs-burn chart background

**Files:** `frontend/src/styles/index.css`, `frontend/src/components/charts/CashCurve.tsx`, `frontend/src/components/charts/BurnChart.tsx`

Added a distinct chart surface background:
- New CSS tokens `--chart-surface`, `--chart-grid`, `--chart-text`
- Dark mode: soft light background (`30 22% 97%`) with dark text
- Light mode: pure white background with dark text
- Both charts now render inside a rounded, bordered panel with the surface background, and axis/tooltip text uses the chart-text color for contrast

## 5. Blueprints: "Finish" button not working (phase 5 review)

**Files:** `frontend/src/features/blueprint/BuilderWizard.tsx`

Root causes:
- The Finish button was gated on `validation?.is_valid`, but validation only runs after a debounced version-save completes, so the button stayed disabled.
- The debounce hook set `ready=true` once and never re-fired on later payload changes.
- The auto-create POST sent the (empty) payload, which the backend rejects (422) because a blueprint must have ≥1 revenue stream — so `blueprintId` stayed null and Finish stayed disabled forever.

**Fixes:**
- Auto-create now seeds a minimal-valid payload (one placeholder revenue stream) so creation always succeeds; the real payload replaces it via the debounced version-save.
- Debounce now re-fires on every payload change (returns the debounced value instead of a one-shot `ready` flag).
- Finish button: enabled whenever a blueprint exists and validation has no *errors* (warnings are OK). Clicking Finish explicitly saves the latest payload, then navigates. Label shows "Saving…" while saving.

## 6. Blueprints: number typing problems (revenue streams, costs & team)

**Files:** `frontend/src/features/blueprint/steps/fields.tsx`

`NumberInput` coerced `''` → `0` on every keystroke, so you couldn't clear a field or type an intermediate value. Rewrote it with local string state that syncs from the prop; `onChange` only fires for valid numbers. Applies to Revenue, Costs & Team, and Financials steps (all use the shared component).

## 7. Blueprint Profile step: add geography = India

**Files:** `frontend/src/features/blueprint/types.ts`

Added `India` to the `GEOGRAPHIES` list (backend stores geography as a free string, so no backend change needed).

## 8. Login page: founder name / company name + demo user button

**Files:** `frontend/src/features/auth/RegisterPage.tsx`, `frontend/src/features/auth/LoginPage.tsx`

- Register page: renamed "Name" → **"Founder name"** and added a **"Company name"** field. After signup, the auto-created personal workspace is renamed to the company name (best-effort).
- Login page: added a **"Try the demo account"** button that logs in as the seeded demo user (`demo@forge.dev` / `demo-password-123`), which previously "had no action" because no such button existed.

## 9. Billing tab: PDF not downloaded / share link broken

**Files:** `frontend/nginx.conf`, `frontend/vite.config.ts`, `frontend/src/features/reports/ReportPage.tsx`, `.env` (local, gitignored)

Root causes:
- Exported PDFs are served by the backend at `/reports/...`, but **nginx only proxied `/api/`, `/ws/`, `/health`, `/ready`** — `/reports/` 404'd through the SPA.
- Share links are built from `FRONTEND_URL`, which was set to `http://localhost:5173` while production is `http://65.20.89.170`.
- Clipboard copy can fail on insecure origins.

**Fixes:**
- nginx: added `location /reports/` proxy to the backend.
- Vite dev server: added `/api`, `/reports`, and `/ws` proxies so dev matches prod.
- ReportPage: clipboard copy now falls back to a hidden-textarea `execCommand('copy')` on insecure origins.
- `.env` (local, not committed): `FRONTEND_URL` updated to `http://65.20.89.170`.

---

## Validation

- `npm run build` — passes (no type errors)
- `npm run lint` — passes (0 errors; 5 pre-existing warnings unrelated to these changes)
- `npm run test` — **36/36 pass** (with `NODE_ENV=test`; the shell's global `NODE_ENV=production` makes React load the prod build and breaks `act()`, which is a pre-existing environment artifact, not a code issue)
- Backend unit tests — 248 passed (no backend code changed; integration tests need the docker stack)

## Notes / follow-ups

- `.env` is gitignored, so the `FRONTEND_URL` fix is local-only — apply the same value in the deployed environment.
- The 500 kB+ chunk warning on build is pre-existing (the app is a single bundle); code-splitting is an optional follow-up.
- "Demo user" exists only after running `make seed` (creates `demo@forge.dev`).

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

---

# Round 2 — Deploy & live-server verification

Date: 2026-08-10

## Problem

Same errors reappeared on the live site (`65.20.89.170`):

- `crypto.randomUUID is not a function` — identical stack traces as round 1
- `GET /api/v1/simulations 401 (Unauthorized)`

## Root cause — fixes were never deployed

The round-1 fixes were committed (`5007896`) and pushed to GitHub, but the live
server was **still serving the old bundle** (`index-DAP_33iT.js`), which
contained the unfixed `crypto.randomUUID` code. Deployment is manual: the
server runs the containers from `docker-compose.yml` and only picks up new
frontend code after a rebuild (`docker compose up -d --build`).

Verified by comparing bundle hashes:
- Live server before deploy: `index-DAP_33iT.js` (old)
- Local build: `index-CKp96HUI.js` (fixed)

## The 401 — separate, transient auth issue

`/api/v1/simulations` 401s when the browser's access token is expired
(access tokens last **15 minutes**). Verified the endpoint and auth flow work
correctly against the live API with a fresh token:

- `POST /auth/login` → 200 (returns access + refresh tokens)
- `GET /api/v1/workspaces` with fresh token → 200
- `GET /api/v1/simulations` with fresh token + `X-Workspace-Id` → 200
- `GET /api/v1/blueprints` with fresh token + `X-Workspace-Id` → 200

The client has a transparent refresh-on-401 path, but it can only help after
the new bundle is deployed and if the refresh token is still valid. The 401 in
the console was most likely the old bundle failing during a routine
token-expiry refresh — users can simply re-login, and the deployed refresh
logic now handles it automatically.

## Fixes applied (this round)

1. **Deployed the round-1 fixes to the live server**
   - `docker compose up -d --build frontend` on the server (`65.20.89.170`)
   - New bundle now served: `index-izxQpyuR.js` (confirmed to contain the
     `4xxx-yxxx` UUID fallback)

2. **Verified deployment end-to-end**
   - `/api/v1/health` → 200
   - `/reports/<missing>.pdf` → 404 from the backend (nginx proxy working;
     real PDFs now download instead of returning the SPA shell)
   - Authenticated workspaces/simulations/blueprints → all 200

## Notes

- The access-token 401 requires no code change — it's normal token expiry.
  The auto-refresh in the new bundle handles it; a page refresh or re-login
  clears any stale state.
- The backend image was also rebuilt as a side effect of the compose command
  (its code is unchanged, so behavior is identical).

---

# Round 3 — Ghost chart colors, demo seed data, stale-cache fix

Date: 2026-08-10

## Problems reported

1. **Ghost run: graph values shown in black** — on the ghost spectator page's
   cash-curve chart the axis values rendered near-black on the light surface.
2. `POST /api/v1/simulations` → **404 (Not Found)** — reported mid-session.
3. `POST /api/v1/users/me/password` → **400 (Bad Request)** + `crypto.randomUUID`
   crash on `index-DAP_33iT.js` (old bundle).
4. "Simulation not run" — no simulation would start.

## Root causes & fixes

### 1. Graph values in black → changed chart text color

`--chart-text` was `222 47% 11%` (near-black) on a light surface — exactly the
"values shown in black" the user saw. Split the tokens into two tones:

- `--chart-text` (values/tooltip): mid slate `215 25% 27%` — readable, not black
- `--chart-axis` (axis labels / month label / $k ticks): muted `24 8% 45%`

Updated `CashCurve.tsx` and `BurnChart.tsx` to use `--chart-axis` for ticks and
`--chart-text` for tooltip values. Both dark and light variants updated.

### 2. Demo account could not log in → seed data was lost/stale

Investigation found:
- The demo user existed in the DB, but its stored password hash did **not**
  match `demo-password-123` (the seed script is check-then-insert, so it never
  resets an existing user's password).
- The `demo-ventures` workspace had **no blueprints or runs** — the seed data
  was missing, so there was nothing to simulate ("simulation not run").

Fixes (on the server):
- Reset the demo user's password hash to `demo-password-123`.
- Ran `python -m app.utils.seed` (idempotent) → created the 3 demo blueprints
  (SaaSFlow, BrewBox, ConsultPro) and a completed Monte Carlo run in the demo
  workspace.
- Verified end-to-end: demo login 200, blueprints 200, a ghost-mode simulation
  POST returns 201.

### 3. POST /simulations 404 → transient during deploy

Backend logs show the 404 happened **during the container recreate** (the
previous deploy). Later POSTs returned 201 and 402 (plan limit). With the
seed restored, ghost-mode POST now returns 201. No code change needed.

### 4. Password change 400 → correct behavior

`POST /users/me/password` returns 400 "Current password is incorrect" when the
current password doesn't match — that is intended. The accompanying
`crypto.randomUUID` crash was from the stale cached bundle (see below).

### 5. Stale bundle (`index-DAP_33iT.js`) → nginx cache headers

The server was serving the new bundle, but the user's browser kept the old one
because nginx sent no `Cache-Control` on `index.html`. Fix:

- `location /` → `Cache-Control: no-cache` (always refetch the HTML, which
  points at the new hashed bundle)
- `location /assets/` → `Cache-Control: public, immutable` + 1y expiry
  (hashed files are safe to cache forever)

Deployed bundle is now `index-DSVBfvlp.js`; verified the HTML is `no-cache`
and assets are `immutable`. Users must hard-refresh **once** to drop the old
bundle, then future deploys propagate automatically.

## Verification (live server)

- `GET /api/v1/health` → 200
- `POST /api/v1/auth/login` (demo) → 200
- `GET /api/v1/blueprints` (demo ws) → 200, 3 blueprints
- `POST /api/v1/simulations` (ghost mode, demo ws) → 201
- HTML served with `Cache-Control: no-cache`; assets with `immutable`
- `npm run build` passes; frontend tests 36/36 pass

---

# Round 4 — Blueprint Finish button not clickable

Date: 2026-08-10

## Problem

On the Build-a-Blueprint wizard (step 5 / Review), the **Finish button was
disabled / did nothing** even with a complete blueprint.

## Root causes

1. **Stale server-validation gating.** `canFinish` was computed from
   `GET /blueprints/{id}/validate`, which validates the *last saved version*.
   The wizard auto-saves 800 ms after every keystroke, so validation always
   lagged the current draft. The button could be disabled by stale errors from
   an earlier state even when the current draft was fine — or enabled when the
   current draft was actually broken.
2. **Silent disabling.** When blocked, the button was just `disabled` with only
   a hover tooltip. There was no on-screen reason, so it looked broken
   ("not clickable").
3. **Silent save failures.** `useAddVersion` had no `onError` handler, and the
   Finish click's `onError` was empty — if the server rejected the payload
   (422), the user got no feedback and stayed stuck.
4. **A `//versions` 404** in the logs showed the debounced auto-save could fire
   with an empty `blueprintId` (pre-deploy race in the old bundle).

## Fixes

- **Client-side validation of the current draft.** Added `validateDraft()` to
  `frontend/src/features/blueprint/types.ts`, mirroring the backend rules
  (revenue streams present, LTV ≥ CAC, positive contribution margin, runway
  warning). The wizard now validates what the user has *actually typed*, so
  the Finish state is always accurate.
- **Finish is always clickable once a blueprint exists.** The button is no
  longer disabled by validation errors. Clicking Finish saves the payload and
  navigates; if the server rejects it, an error toast explains why and the
  user stays on the wizard with the ValidationPanel showing the issues.
- **Inline error feedback.** When the local draft has validation errors, a
  message appears above the Finish button listing what to fix (previously a
  dead button with no explanation).
- **Finish save errors toast.** `handleFinish` now surfaces the server's
  rejection message via `toastError` instead of failing silently.
- **Removed the wizard's own `useBlueprintValidation`** — it only duplicated
  what `ValidationPanel` already fetches, and its stale result was the source
  of the wrong `canFinish` state.

## Files changed

- `frontend/src/features/blueprint/types.ts` — added `validateDraft()`
- `frontend/src/features/blueprint/BuilderWizard.tsx` — use local validation,
  clickable Finish with toast on server rejection, inline error message

## Verification

- `npm run build` passes; frontend tests 36/36 pass; lint clean
- Deployed to the live server; new bundle `index-CHk4b3D-.js` contains the fix
- `/api/v1/health` → 200

## Note

Users who were previously stuck should hard-refresh once to load the new
bundle (cache headers now make this automatic on future deploys).

# Phase 7 — App Shell, Dashboard & Marketing

Turn the working core product into a flagship SaaS surface: a polished dark-first design system, a real dashboard, onboarding, notifications, settings, and a public marketing site. All work in this phase is frontend-heavy; T36 and T38 include small, precisely-specified backend extensions.

Conventions for this phase (established in earlier phases — do not reinvent):
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui + TanStack Query + Zustand, routes in `frontend/src/router.tsx`, API calls only via `frontend/src/lib/api-client.ts`.
- Frontend tests: Vitest + React Testing Library + jsdom. If `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, and `jsdom` are not yet in `frontend/package.json` devDependencies, add them (`npm i -D vitest @testing-library/react @testing-library/jest-dom jsdom`) and add `"test": "vitest run"` to `package.json` scripts.
- Backend (where touched): Python 3.12, FastAPI, async SQLAlchemy 2.0, Pydantic v2, Alembic. Tests: pytest + pytest-asyncio + httpx. Lint: `cd backend && ruff check app tests && mypy app`.

---

## Task T34: Design system polish — dark theme tokens, motion, skeletons, empty states

**Description:** Elevate the T03 shell into a distinctive, cohesive "war room" design system that every later feature card reuses. (1) Theme tokens: extend `frontend/tailwind.config.ts` with a dark-first palette defined as CSS custom properties in `frontend/src/styles/globals.css` (shadcn/ui HSL variable style): background near-black with a subtle warm/ember tint, `forge` accent color (e.g. ember orange) as the primary accent, semantic `success`/`warning`/`danger` tokens, and chart palette tokens (`chart-1`…`chart-5`) that T35's Recharts charts will consume. Add font tokens (one display font for headings/numbers, one sans for body — self-host via `@fontsource` packages, e.g. `@fontsource/space-grotesk` + `@fontsource/inter`; no Google Fonts CDN). (2) Motion: install `framer-motion` and create `frontend/src/components/layout/PageTransition.tsx` — a wrapper using `AnimatePresence` + `motion.div` (fade + 8px slide-up, ~200ms, `easeOut`) applied per route in `frontend/src/router.tsx`; respect `prefers-reduced-motion` by disabling transforms. (3) Primitives: create `frontend/src/components/ui/skeleton.tsx` (shadcn-style pulsing skeleton) and `frontend/src/components/ui/empty-state.tsx` (`EmptyState` component: icon, title, description, optional CTA button). (4) Sweep: add skeleton loading states and `EmptyState` fallbacks to every existing feature page that fetches data (at minimum: auth-adjacent pages from T07/T09, blueprint list from T18, simulation runner list/history from T29, reports list from T32) — every list page must show skeletons while its TanStack Query is pending and an `EmptyState` with a relevant CTA when the query returns an empty array.

**Acceptance criteria:**
- [ ] `tailwind.config.ts` exposes the new tokens and `npm run build` succeeds with them used in at least one component (`bg-background`, `text-forge` or equivalent primary token, `text-success`/`text-danger`)
- [ ] Navigating between any two routes animates via `PageTransition` (fade + slide-up) and does not animate when `prefers-reduced-motion: reduce` is set
- [ ] Every data-fetching list page renders skeleton placeholders while loading and an `EmptyState` (with CTA) when empty — no raw "No items" strings or blank pages remain
- [ ] No hardcoded hex colors in feature components outside `tailwind.config.ts`/`globals.css` token definitions (grep check)
- [ ] `PageTransition`, `Skeleton`, and `EmptyState` have Vitest tests: transition renders children, empty state renders title + CTA and fires CTA onClick

**Verification:**
- [ ] Tests pass: `cd frontend && npx vitest run src/components/layout/__tests__/PageTransition.test.tsx src/components/ui/__tests__/empty-state.test.tsx` — create these two test files
- [ ] Lint/build passes: `cd frontend && npm run lint && npm run build`
- [ ] Manual check: load the app, throttle network to "Slow 3G" in devtools, navigate between pages — skeletons appear, transitions play, empty lists show branded empty states

**Dependencies:** T03

**Files likely touched:**
- `frontend/tailwind.config.ts`
- `frontend/src/styles/globals.css`
- `frontend/src/components/layout/PageTransition.tsx`
- `frontend/src/components/ui/skeleton.tsx`
- `frontend/src/components/ui/empty-state.tsx`
- `frontend/src/router.tsx`
- `frontend/package.json` (framer-motion, @fontsource packages, vitest deps if missing)
- `frontend/src/components/layout/__tests__/PageTransition.test.tsx`
- `frontend/src/components/ui/__tests__/empty-state.test.tsx`
- Existing feature list pages (skeleton/empty-state sweep, e.g. `frontend/src/features/blueprint/`, `frontend/src/features/simulation/`, `frontend/src/features/reports/`)

**Estimated scope:** M

---

## Task T35: Main dashboard — KPI cards, resilience gauge, charts, recent activity

**Description:** Build the post-login home page at route `/` (inside `AppShell`) as `frontend/src/features/dashboard/DashboardPage.tsx`. Data comes from existing Phase 5/6 endpoints via TanStack Query hooks in `frontend/src/features/dashboard/hooks.ts`: recent runs `GET /api/v1/simulations` (list of `{id, blueprint_version_id, mode, status, seed, created_at, result}`), latest completed run's ticks `GET /api/v1/simulations/{id}/ticks` (array of `{run_id, month, kpis}` where `kpis` is JSONB shaped like `{cash_balance, mrr, burn_rate, runway_months, customers, churn_rate}`), and latest Monte Carlo report `GET /api/v1/simulations/{id}/report` (`{survival_rate, median_lifespan_months, resilience_score, kill_vectors}`). Layout: (1) a row of `KpiCard` components (create in `frontend/src/features/dashboard/KpiCard.tsx`) showing latest cash balance, MRR, burn rate, and runway from the newest tick, each with a delta vs. previous month and a sparkline; (2) a `ResilienceGauge` (create `frontend/src/components/charts/ResilienceGauge.tsx` — radial gauge, 0–100, colored by threshold: <40 danger, 40–70 warning, >70 success, animated with framer-motion on mount) fed by the latest report's `resilience_score`; (3) cash curve and MRR/burn charts using Recharts — create `frontend/src/components/charts/CashCurve.tsx` (`AreaChart` of `cash_balance` by `month`) and `frontend/src/components/charts/BurnChart.tsx` (`ComposedChart`: MRR as line, burn as bars) using the `chart-1…chart-5` tokens from T34; (4) a recent runs table (`mode`, `status` badge, `seed`, created date, resilience score if present, row click → `/simulations/{id}`); (5) quick-action buttons: "New Blueprint" → `/blueprints/new`, "Run Baseline" → `/simulations/new`, "Monte Carlo" → `/simulations/new?mode=monte_carlo`. All cards use T34 `Skeleton` while pending and `EmptyState` (with "Create your first blueprint" CTA) when the workspace has no runs yet.

**Acceptance criteria:**
- [ ] `/` renders KPI cards with values from the latest tick of the most recent completed run (not hardcoded), each showing a month-over-month delta
- [ ] `ResilienceGauge` animates from 0 to the report's `resilience_score` and changes color across the 40/70 thresholds
- [ ] `CashCurve` and `BurnChart` render from `GET /api/v1/simulations/{id}/ticks` data and are hidden behind skeletons until loaded
- [ ] Recent runs table shows the 5 most recent runs and row-click navigates to `/simulations/{id}`
- [ ] With zero runs, the page shows the T34 `EmptyState` with a working "Create your first blueprint" CTA instead of empty charts
- [ ] Vitest test mounts `DashboardPage` with a mocked api-client and asserts KPI values, gauge, and table rows render from fixture data

**Verification:**
- [ ] Tests pass: `cd frontend && npx vitest run src/features/dashboard/__tests__/DashboardPage.test.tsx src/components/charts/__tests__/ResilienceGauge.test.tsx` — create these two test files
- [ ] Lint/build passes: `cd frontend && npm run lint && npm run build`
- [ ] Manual check: after a seed/demo run exists (T25+), `/` shows live KPI numbers, an animated gauge, and two charts; on a fresh workspace it shows the empty state

**Dependencies:** T25, T34

**Files likely touched:**
- `frontend/src/features/dashboard/DashboardPage.tsx`
- `frontend/src/features/dashboard/KpiCard.tsx`
- `frontend/src/features/dashboard/RecentRunsTable.tsx`
- `frontend/src/features/dashboard/hooks.ts`
- `frontend/src/components/charts/ResilienceGauge.tsx`
- `frontend/src/components/charts/CashCurve.tsx`
- `frontend/src/components/charts/BurnChart.tsx`
- `frontend/src/router.tsx` (register `/` route)
- `frontend/src/features/dashboard/__tests__/DashboardPage.test.tsx`
- `frontend/src/components/charts/__tests__/ResilienceGauge.test.tsx`

**Estimated scope:** M

---

## Task T36: Onboarding wizard — industry / stage / primary fear

**Description:** Implement spec §9 Phase 1 onboarding as a 3-step wizard shown once after registration, before the user reaches the dashboard. Create `frontend/src/features/onboarding/OnboardingWizard.tsx` with step components in the same folder (`IndustryStep.tsx`, `StageStep.tsx`, `FearStep.tsx`) plus a `ProgressDots` header; steps advance with T34 `PageTransition`-style motion. Step 1: industry select — card-grid radio of at least: SaaS, D2C/E-commerce, Retail, Restaurant, Fintech, Marketplace, Agency/Services, Other. Step 2: stage select — exactly: Idea, MVP, Pre-Seed, Seed, Series A+. Step 3: primary fear — free-text textarea (min 10 chars, placeholder: *"e.g. I'm worried my CAC is too high"*), plus 3 selectable suggestion chips ("Not enough runway", "CAC too high", "Don't know if the model works") that fill the textarea. On finish, persist via `PATCH /api/v1/users/me` with body `{industry, stage, primary_fear}` — backend extension: add nullable string columns `industry`, `stage`, `primary_fear`, plus boolean `onboarding_completed DEFAULT false` to the `User` model, an Alembic migration, and extend the user update schema in `backend/app/schemas/user.py` (`UserUpdate` gains optional `industry`, `stage`, `primary_fear`; `UserRead` exposes them and `onboarding_completed`; when all three onboarding fields are set, `users.py` sets `onboarding_completed = True`). Gating: a `RequireOnboarding` wrapper in `frontend/src/router.tsx` redirects authenticated users with `onboarding_completed === false` (from `GET /api/v1/users/me`) to `/onboarding`; the wizard invalidates the `["me"]` TanStack Query cache on success and routes to `/`. The wizard must be skippable via a "Skip for now" link that PATCHes nothing but sets a `localStorage` flag so the gate stops redirecting.

**Acceptance criteria:**
- [ ] `PATCH /api/v1/users/me` with `{industry, stage, primary_fear}` returns 200, persists the values, and flips `onboarding_completed` to `true` in the response
- [ ] Alembic migration adds the four columns and `alembic upgrade head` + `alembic downgrade -1` both run clean
- [ ] A fresh registered user visiting `/` is redirected to `/onboarding`; after completing the wizard they land on `/` and are never redirected again
- [ ] Step 3 blocks "Finish" until the textarea has ≥10 characters; suggestion chips populate the textarea
- [ ] "Skip for now" exits to `/` and the gate does not redirect again for that browser
- [ ] Backend integration test covers the PATCH flow end-to-end (register → patch → `GET /users/me` reflects fields)

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/integration/api/test_users_onboarding.py -v` — create this test file; and `cd frontend && npx vitest run src/features/onboarding/__tests__/OnboardingWizard.test.tsx` — create this test file (step navigation, validation, submit calls api-client with the right body)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app` and `cd frontend && npm run lint && npm run build`
- [ ] Manual check: register a new account → wizard appears → pick industry/stage, type a fear → land on dashboard → reload, wizard does not reappear

**Dependencies:** T07

**Files likely touched:**
- `frontend/src/features/onboarding/OnboardingWizard.tsx`
- `frontend/src/features/onboarding/IndustryStep.tsx`
- `frontend/src/features/onboarding/StageStep.tsx`
- `frontend/src/features/onboarding/FearStep.tsx`
- `frontend/src/features/onboarding/__tests__/OnboardingWizard.test.tsx`
- `frontend/src/router.tsx` (`RequireOnboarding` gate + `/onboarding` route)
- `backend/app/models/user.py` (4 new columns)
- `backend/app/schemas/user.py` (`UserUpdate`/`UserRead` extensions)
- `backend/app/api/v1/endpoints/users.py` (set `onboarding_completed`)
- `backend/alembic/versions/<new_revision>_add_onboarding_fields.py`
- `backend/tests/integration/api/test_users_onboarding.py`

**Estimated scope:** S

---

## Task T37: Notifications center + toast system

**Description:** Add an app-wide notification layer, frontend-only for now (backend persistence via `app/services/notification_service.py` arrives in Phase 8). (1) Toast system: install `sonner`, mount `<Toaster />` once in `AppShell` (dark theme, top-right), and wrap it in `frontend/src/lib/toast.ts` exporting `toastSuccess(msg)`, `toastError(msg)`, `toastInfo(msg)` so feature code never imports `sonner` directly. Wire the three most important flows: simulation started/completed/failed, blueprint saved, and report exported — each emits a toast from its existing mutation's `onSuccess`/`onError`. (2) Notifications store: create `frontend/src/stores/notifications.ts` — a Zustand store with `persist` middleware (localStorage key `forge-notifications`) holding `{id, title, body, kind: "info"|"success"|"warning"|"error", created_at, read}[]`, capped at 50 entries, with `addNotification`, `markRead(id)`, `markAllRead`, and derived `unreadCount`. The toast helpers above also push into this store so every toast lands in the center. (3) Bell dropdown: extend `frontend/src/components/layout/Topbar.tsx` with a bell icon button showing an unread-count badge (hidden when 0), opening a shadcn/ui `Popover` dropdown listing notifications newest-first: unread rows have a bold title + accent dot, clicking a row marks it read, footer has "Mark all as read" and "Clear" buttons, and an empty dropdown shows the T34 `EmptyState` ("You're all caught up").

**Acceptance criteria:**
- [ ] `toastSuccess`/`toastError`/`toastInfo` render a sonner toast AND append an entry to the notifications store
- [ ] Bell badge shows the exact unread count and disappears at 0; opening the dropdown and clicking "Mark all as read" zeroes it
- [ ] Notifications survive a page reload (localStorage persistence) and the list never exceeds 50 entries
- [ ] Unread entries are visually distinct (bold + dot) and become read on click
- [ ] Simulation start and blueprint save flows each produce a toast + notification entry
- [ ] Vitest tests cover the store (add/markRead/cap-at-50/persistence rehydrate) and the dropdown (badge count, mark-all-read)

**Verification:**
- [ ] Tests pass: `cd frontend && npx vitest run src/stores/__tests__/notifications.test.ts src/components/layout/__tests__/NotificationBell.test.tsx` — create these two test files
- [ ] Lint/build passes: `cd frontend && npm run lint && npm run build`
- [ ] Manual check: start a simulation → toast pops → bell badge increments → open dropdown, click the entry → badge decrements; reload the page → notification history intact

**Dependencies:** T34

**Files likely touched:**
- `frontend/src/lib/toast.ts`
- `frontend/src/stores/notifications.ts`
- `frontend/src/components/layout/Topbar.tsx` (bell + dropdown; extract `NotificationBell.tsx` in the same folder if Topbar grows)
- `frontend/src/components/layout/AppShell.tsx` (mount `<Toaster />`)
- `frontend/package.json` (sonner)
- Toast call sites in `frontend/src/features/simulation/`, `frontend/src/features/blueprint/`, `frontend/src/features/reports/`
- `frontend/src/stores/__tests__/notifications.test.ts`
- `frontend/src/components/layout/__tests__/NotificationBell.test.tsx`

**Estimated scope:** S

---

## Task T38: Settings pages — profile, workspace, members, security

**Description:** Build the settings area at `/settings` as `frontend/src/features/settings/SettingsLayout.tsx` with a left sub-nav (Profile, Workspace, Members, Security) rendering four pages. Profile (`/settings/profile`, `ProfilePage.tsx`): form pre-filled from `GET /api/v1/users/me` — name, email (read-only), and the T36 onboarding fields (industry, stage, primary_fear) editable; saves via `PATCH /api/v1/users/me`, invalidates `["me"]`, fires `toastSuccess`. Workspace (`/settings/workspace`, `WorkspacePage.tsx`): edit workspace name via `PATCH /api/v1/workspaces/{id}` (owner/admin only — disable the form with an explanatory note for `member` role, using the role from the workspace store). Members (`/settings/members`, `MembersPage.tsx`): reuse T09's member list and invite flow — table of members (name, email, role badge), invite-by-email form posting `POST /api/v1/workspaces/{id}/invites`, role change dropdown and remove-member button gated to owner/admin, all with T34 skeletons/empty states and T37 toasts. Security (`/settings/security`, `SecurityPage.tsx`): password change form (current password, new password ≥8 chars, confirm) posting to a NEW backend endpoint `POST /api/v1/users/me/password` with body `{"current_password": "...", "new_password": "..."}` — backend extension: add `PasswordChange` schema to `backend/app/schemas/user.py`, implement the route in `backend/app/api/v1/endpoints/users.py` delegating to `backend/app/services/auth_service.py` (`change_password(user, current, new)`: verify current hash via existing passlib context in `app/core/security.py`, return 400 `{"detail": "Current password is incorrect"}` on mismatch, otherwise store new argon2/bcrypt hash and return 204). On success the page shows `toastSuccess` and clears the form.

**Acceptance criteria:**
- [ ] `POST /api/v1/users/me/password` with a correct current password returns 204 and the new password works on subsequent `POST /api/v1/auth/login`; wrong current password returns 400
- [ ] Profile page loads current values and a save round-trips them (visible after reload)
- [ ] Workspace rename succeeds for owner/admin and the form is disabled with a note for `member` role
- [ ] Members page can invite an email (invite appears in list/console email fallback) and remove a member; both actions toast
- [ ] Security form blocks submit when new password <8 chars or confirm mismatches, and clears on success
- [ ] All four pages use skeletons while loading and never render raw API errors to the user (errors go through `toastError`)

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/integration/api/test_users_password.py -v` — create this test file (204 on success, 400 on wrong current, login works with new password); and `cd frontend && npx vitest run src/features/settings/__tests__/SecurityPage.test.tsx` — create this test file (validation + submit contract)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app` and `cd frontend && npm run lint && npm run build`
- [ ] Manual check: change password in settings → log out → log in with the new password → succeeds; log in with the old password → fails

**Dependencies:** T09

**Files likely touched:**
- `frontend/src/features/settings/SettingsLayout.tsx`
- `frontend/src/features/settings/ProfilePage.tsx`
- `frontend/src/features/settings/WorkspacePage.tsx`
- `frontend/src/features/settings/MembersPage.tsx`
- `frontend/src/features/settings/SecurityPage.tsx`
- `frontend/src/features/settings/__tests__/SecurityPage.test.tsx`
- `frontend/src/router.tsx` (register `/settings/*` routes)
- `backend/app/schemas/user.py` (`PasswordChange`)
- `backend/app/api/v1/endpoints/users.py` (`POST /users/me/password`)
- `backend/app/services/auth_service.py` (`change_password`)
- `backend/tests/integration/api/test_users_password.py`

**Estimated scope:** M

---

## Task T39: Marketing landing page + pricing page

**Description:** Build the public marketing surface, served without auth. Define plan tiers once in `frontend/src/lib/constants.ts` as `PLAN_TIERS: [{id, name, price_monthly, price_yearly, tagline, features[], highlighted}]` — four tiers: Free ($0 — 5 runs/mo, baseline mode only, 1 seat), Pro ($49/mo — 100 runs/mo, Monte Carlo ×100, 3 seats), Team ($149/mo — unlimited runs, Monte Carlo ×1000, 10 seats, marketplace publishing), Enterprise (custom — API access, SSO, on-prem option). Landing page (`/`, public — move the T35 dashboard to `/app` or gate the existing `/` behind auth and put marketing at `/`; pick one approach and keep route constants in `frontend/src/lib/constants.ts`): `frontend/src/features/marketing/LandingPage.tsx` composed of section components in the same folder — `Hero.tsx` (headline "The digital wind tunnel for your business", subhead pitching deterministic engine + AI Game Master, primary CTA "Start simulating free" → `/register`, secondary CTA "See pricing" → `/pricing`, animated with T34 framer-motion — staggered fade-up on load, subtle ember-glow gradient background using theme tokens), `HowItWorks.tsx` (4 numbered steps from spec §9: Build blueprint → Baseline run → Stress test → Resilience audit), `Features.tsx` (3–4 cards: Deterministic Engine "physics that can't be overridden", AI Game Master "bespoke, narratively coherent crises", Monte Carlo "100 runs in seconds", War Room "branching strategic decisions"), `SocialProof.tsx` (placeholder: 3 testimonial cards marked as placeholders + a "trusted by" logo strip of grayed placeholder boxes — clearly swap-ready), `FinalCta.tsx` (repeat CTA + footer with docs/GitHub placeholder links). Pricing page (`/pricing`, `PricingPage.tsx`): monthly/yearly billing toggle (yearly = 2 months free, price displayed per month), tier cards from `PLAN_TIERS` with the `highlighted` tier visually elevated (accent border + "Most popular" badge), CTA buttons → `/register?plan={id}` (registration can ignore the param for now — T40 wires checkout), and a compact feature-comparison note. Both pages use a minimal `MarketingLayout` (logo + Login/Get started nav) instead of `AppShell`, and every section animates in on scroll (`whileInView`).

**Acceptance criteria:**
- [ ] The landing page is reachable at `/` without authentication and the authenticated dashboard lives at its own route with no route conflicts (router test asserts both resolve)
- [ ] Hero primary CTA navigates to `/register`; pricing tier CTAs navigate to `/register?plan={id}`
- [ ] Pricing toggle switches all tier prices between monthly and yearly (yearly shown as 10/12 of monthly × 12) without page reload
- [ ] All marketing strings/prices come from `PLAN_TIERS` and section components — no tier data hardcoded in JSX
- [ ] Social proof placeholders are visually present and clearly marked as placeholders (e.g. `data-testid="social-proof-placeholder"`)
- [ ] Sections animate on scroll via framer-motion `whileInView` and respect `prefers-reduced-motion`

**Verification:**
- [ ] Tests pass: `cd frontend && npx vitest run src/features/marketing/__tests__/LandingPage.test.tsx src/features/marketing/__tests__/PricingPage.test.tsx` — create these two test files (CTA hrefs, toggle math, tier rendering from `PLAN_TIERS`)
- [ ] Lint/build passes: `cd frontend && npm run lint && npm run build`
- [ ] Manual check: in an incognito window, `/` shows the animated landing page, `/pricing` toggle flips prices, and clicking "Start simulating free" reaches registration

**Dependencies:** T34

**Files likely touched:**
- `frontend/src/features/marketing/LandingPage.tsx`
- `frontend/src/features/marketing/Hero.tsx`
- `frontend/src/features/marketing/HowItWorks.tsx`
- `frontend/src/features/marketing/Features.tsx`
- `frontend/src/features/marketing/SocialProof.tsx`
- `frontend/src/features/marketing/FinalCta.tsx`
- `frontend/src/features/marketing/PricingPage.tsx`
- `frontend/src/features/marketing/MarketingLayout.tsx`
- `frontend/src/lib/constants.ts` (`PLAN_TIERS`)
- `frontend/src/router.tsx` (public marketing routes, dashboard route move)
- `frontend/src/features/marketing/__tests__/LandingPage.test.tsx`
- `frontend/src/features/marketing/__tests__/PricingPage.test.tsx`

**Estimated scope:** M

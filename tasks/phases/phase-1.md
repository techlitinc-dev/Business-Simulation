# Phase 1 — Auth & Multi-Tenancy

Adds the SaaS identity layer on top of the Phase 0 scaffold: JWT auth with argon2-hashed passwords, React auth UI with automatic token refresh, workspace-scoped multi-tenancy with owner/admin/member RBAC, workspace management UI, and an email abstraction with SMTP + console fallback for verification and invite flows.

---

## Task T06: User model + register/login/refresh JWT endpoints + password hashing

**Description:** Build the backend identity foundation. Create the SQLAlchemy 2.0 async `User` model in `backend/app/models/user.py` with columns: `id` (UUID string pk, use the prefixed-id helper from `app/utils/ids.py` if it exists, else plain `uuid4` hex), `email` (unique, indexed, lowercase), `name` (str), `pw_hash` (str), `is_verified` (bool, default False), `is_admin` (bool, default False), plus the common `created_at`/`updated_at` columns from `app/db/base.py`. In `backend/app/core/security.py` implement password hashing with **passlib 1.7.4 `CryptContext(schemes=["argon2"])`** (requires `passlib[argon2]` + `argon2-cffi` in `requirements.txt`): functions `hash_password(pw: str) -> str` and `verify_password(pw: str, pw_hash: str) -> bool`. Implement JWT with **PyJWT 2.x**: `create_access_token(user_id) -> str`, `create_refresh_token(user_id) -> str`, `decode_token(token) -> dict` (raises on expiry/invalid). Add settings to `app/core/config.py` (+ `.env.example`): `JWT_SECRET_KEY`, `JWT_ALGORITHM="HS256"`, `ACCESS_TOKEN_EXPIRE_MINUTES=15`, `REFRESH_TOKEN_EXPIRE_DAYS=7`. Access token claims: `{"sub": user_id, "type": "access", "exp": ...}`; refresh token: `{"sub": user_id, "type": "refresh", "exp": ...}`. Define Pydantic v2 schemas in `backend/app/schemas/auth.py`: `RegisterRequest{email: EmailStr, name: str, password: str(min_length=8)}`, `LoginRequest{email, password}`, `RefreshRequest{refresh_token: str}`, `TokenPair{access_token: str, refresh_token: str, token_type: str = "bearer"}` and in `schemas/user.py`: `UserOut{id, email, name, is_verified}` (`model_config = ConfigDict(from_attributes=True)`). Business logic goes in `backend/app/services/auth_service.py` (`register_user`, `authenticate_user`, `refresh_tokens`); endpoints in `backend/app/api/v1/endpoints/auth.py`, mounted in `app/api/v1/router.py` under prefix `/auth`. Also add the auth dependencies in `backend/app/api/deps.py`: `get_current_user` (OAuth2-style `Authorization: Bearer` header → decode access token → load User, 401 on failure). Exact routes:

- `POST /api/v1/auth/register` → 201, body `RegisterRequest`, response `UserOut`; 409 if email exists. On success create user with `is_verified=False` and enqueue the verification email (call `app.workers.email_tasks.send_verification_email_task`; it will exist after T10 — guard the import/call so T06 works standalone, e.g. try/except around `.delay()` with a logged fallback).
- `POST /api/v1/auth/login` → 200, body `LoginRequest`, response `TokenPair`; 401 on bad credentials (same message for unknown email / wrong password).
- `POST /api/v1/auth/refresh` → 200, body `RefreshRequest`, response `TokenPair` (rotates both tokens); 401 if token invalid or `type != "refresh"`.
- `GET /api/v1/users/me` → 200, response `UserOut`, requires `get_current_user` (create `endpoints/users.py`; needed by the frontend to hydrate session state).

Generate an Alembic migration for the `users` table (`cd backend && alembic revision --autogenerate -m "add users table"`).

**Acceptance criteria:**
- [ ] `POST /api/v1/auth/register` returns 201 with `{id, email, name, is_verified}` and the DB row contains an argon2 hash (starts with `$argon2`), never the plaintext password
- [ ] Duplicate email register returns 409; login with wrong password and with unknown email both return 401 with identical error body
- [ ] `POST /api/v1/auth/login` returns `{access_token, refresh_token, token_type: "bearer"}`; the access token decodes to `type="access"` and expires per `ACCESS_TOKEN_EXPIRE_MINUTES`
- [ ] `POST /api/v1/auth/refresh` with a valid refresh token returns a new `TokenPair`; with an access token (wrong `type`) it returns 401
- [ ] `GET /api/v1/users/me` returns 401 without a token and 200 with the caller's `UserOut` with a valid access token
- [ ] `alembic upgrade head` applies the users migration cleanly

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/integration/api/test_auth.py tests/unit/services/test_auth_service.py -v` — create `tests/integration/api/test_auth.py` (httpx AsyncClient against the app: register/login/refresh/me happy paths + 401/409 cases) and `tests/unit/services/test_auth_service.py` (hash/verify roundtrip, token create/decode, expiry)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: `docker compose up -d`, then `curl -X POST localhost:8000/api/v1/auth/register -H 'Content-Type: application/json' -d '{"email":"a@b.co","name":"A","password":"password123"}'` returns 201, and a follow-up login returns both tokens

**Dependencies:** T04

**Files likely touched:**
- `backend/app/models/user.py`
- `backend/app/core/security.py`
- `backend/app/core/config.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/user.py`
- `backend/app/services/auth_service.py`
- `backend/app/api/deps.py`
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/api/v1/endpoints/users.py`
- `backend/app/api/v1/router.py`
- `backend/alembic/versions/<new>_add_users_table.py`
- `backend/requirements.txt`
- `backend/tests/integration/api/test_auth.py`
- `backend/tests/unit/services/test_auth_service.py`
- `.env.example`

**Estimated scope:** M

---

## Task T07: Auth UI: login/register pages, token storage/refresh, protected routes, API client interceptors

**Description:** Build the frontend auth flow on the Phase 0 shell. In `frontend/src/lib/api-client.ts` create a typed `fetch` wrapper `apiClient<T>(path, options?)` that: prefixes requests with `import.meta.env.VITE_API_URL` (default `http://localhost:8000`), attaches `Authorization: Bearer <access_token>` from the auth store, parses JSON error bodies into a thrown `ApiError{status, detail}`, and on a 401 response (for non-auth endpoints) performs **one** transparent refresh attempt: `POST /api/v1/auth/refresh` with the stored refresh token, stores the new `TokenPair`, retries the original request once, and if refresh fails clears the store and redirects to `/login`. Create the Zustand auth store `frontend/src/stores/auth-store.ts`: state `{user: UserOut | null, accessToken, refreshToken, isAuthenticated}`, actions `login`, `register`, `logout`, `loadMe` (`GET /api/v1/users/me`); persist tokens in `localStorage` keys `forge.access_token` / `forge.refresh_token` (persist user too so refresh survives reload; rehydrate via `loadMe`). Pages in `frontend/src/features/auth/`: `LoginPage.tsx` and `RegisterPage.tsx` — dark-theme forms using shadcn/ui `Card`, `Input`, `Label`, `Button`; client-side validation (email format, password ≥ 8 chars), server error display, TanStack Query `useMutation` for submit; on success store tokens and navigate to `/`. Add a `ProtectedRoute` component in `frontend/src/features/auth/ProtectedRoute.tsx` that renders `<Outlet/>` when authenticated (triggering `loadMe` if tokens exist but user is null, with a loading state) and otherwise `<Navigate to="/login" replace state={{from}}/>`. Wire routes in `frontend/src/router.tsx`: public `/login` and `/register`; wrap the existing AppShell route tree in `ProtectedRoute`. Match backend contracts from T06 exactly: `RegisterRequest{email,name,password}` → 201 `UserOut`; `LoginRequest{email,password}` → 200 `{access_token, refresh_token, token_type}`; `RefreshRequest{refresh_token}` → 200 TokenPair.

**Acceptance criteria:**
- [ ] Registering via `/register` then logging in via `/login` stores tokens in localStorage and lands the user on the protected shell with their name/email visible (e.g. sidebar footer)
- [ ] Reloading the app with stored tokens keeps the user logged in (`loadMe` hydrates `user` before protected content renders)
- [ ] Calling any protected API with an expired access token but valid refresh token silently refreshes and the original request succeeds (no user-visible failure)
- [ ] With an invalid/expired refresh token the user is logged out and redirected to `/login`, and after login is returned to the originally requested URL (`state.from`)
- [ ] Visiting a protected route while logged out redirects to `/login`; `/login` and `/register` are reachable while logged out
- [ ] No token is ever sent to `/auth/login`, `/auth/register`, or `/auth/refresh`

**Verification:**
- [ ] Tests pass: no frontend test runner exists yet — type-safety is the gate: `cd frontend && npx tsc --noEmit`
- [ ] Lint/build passes: `cd frontend && npm run lint && npm run build`
- [ ] Manual check: against the running backend, register + log in in the browser, reload the page (still logged in), then in DevTools set `forge.access_token` to garbage and click around — one refresh happens and the app keeps working

**Dependencies:** T06, T03

**Files likely touched:**
- `frontend/src/lib/api-client.ts`
- `frontend/src/stores/auth-store.ts`
- `frontend/src/features/auth/LoginPage.tsx`
- `frontend/src/features/auth/RegisterPage.tsx`
- `frontend/src/features/auth/ProtectedRoute.tsx`
- `frontend/src/features/auth/hooks.ts`
- `frontend/src/router.tsx`
- `frontend/.env.example` (add `VITE_API_URL`)

**Estimated scope:** M

---

## Task T08: Workspace/membership models + CRUD API + RBAC guard dependency

**Description:** Add the multi-tenancy layer. Models in `backend/app/models/workspace.py` (async SQLAlchemy 2.0, common columns from `app/db/base.py`): `Workspace{id, name, slug (unique, indexed), plan_tier (str, default "free"), stripe_customer_id (str, nullable)}`; `Membership{user_id (FK users.id), workspace_id (FK workspaces.id), role (str: "owner"|"admin"|"member")}` with composite PK `(user_id, workspace_id)`; `Invite{id, token (unique, indexed, `secrets.token_urlsafe(32)`), email, role, workspace_id (FK), expires_at, accepted_at (nullable)}`. Schemas in `backend/app/schemas/workspace.py`: `WorkspaceCreate{name: str}` (slug auto-generated: slugified name + 4-char random suffix), `WorkspaceUpdate{name}`, `WorkspaceOut{id, name, slug, plan_tier, role}` (role = caller's role), `MemberOut{user_id, email, name, role, joined_at}`, `MemberRoleUpdate{role}`, `InviteCreate{email: EmailStr, role: Literal["admin","member"] = "member"}`, `InviteOut{id, email, role, invite_url, expires_at}`, `InviteAcceptOut{workspace_id, role}`. Business logic in `backend/app/services/workspace_service.py`. RBAC guard in `backend/app/api/deps.py`: a dependency factory `require_workspace_role(min_role: str = "member")` that reads `workspace_id` from the path, loads the caller's `Membership`, and raises 403 if absent or if role rank (`owner=3 > admin=2 > member=1`) is below `min_role`; returns the `Membership`. Endpoints in `backend/app/api/v1/endpoints/workspaces.py`, mounted under `/workspaces` (plus the accept route) in `app/api/v1/router.py`:

- `POST /api/v1/workspaces` → 201 `WorkspaceOut`; creator becomes `owner`. Also auto-create a personal workspace ("{name}'s Workspace") on user registration — extend `auth_service.register_user` accordingly.
- `GET /api/v1/workspaces` → 200 `list[WorkspaceOut]` (caller's workspaces only)
- `GET /api/v1/workspaces/{workspace_id}` → 200 `WorkspaceOut` (guard: member)
- `PATCH /api/v1/workspaces/{workspace_id}` → 200 `WorkspaceOut` (guard: admin)
- `DELETE /api/v1/workspaces/{workspace_id}` → 204 (guard: owner)
- `GET /api/v1/workspaces/{workspace_id}/members` → 200 `list[MemberOut]` (guard: member)
- `PATCH /api/v1/workspaces/{workspace_id}/members/{user_id}` → 200 `MemberOut` (guard: admin; only owner may grant/revoke `owner` or `admin`)
- `DELETE /api/v1/workspaces/{workspace_id}/members/{user_id}` → 204 (guard: admin, or self-removal; the last owner cannot be removed — 409)
- `POST /api/v1/workspaces/{workspace_id}/invites` → 201 `InviteOut` (guard: admin); creates `Invite` expiring in 7 days, `invite_url = f"{settings.FRONTEND_URL}/accept-invite?token={token}"`, and enqueues `email_tasks.send_invite_email_task` with the same guarded try/except pattern as T06
- `POST /api/v1/invites/{token}/accept` → 200 `InviteAcceptOut`, requires auth (not workspace membership); 404/410 for unknown or expired token; creates `Membership` for the current user (409 if already a member) and stamps `accepted_at`

Add `FRONTEND_URL` to `app/core/config.py` + `.env.example`. Generate the Alembic migration for the three tables.

**Acceptance criteria:**
- [ ] Registering a user auto-creates a personal workspace with that user as `owner`; `GET /api/v1/workspaces` lists it
- [ ] A `member` can `GET` the workspace and members list but gets 403 on `PATCH /workspaces/{id}`, invites, and member-role changes; `admin` can do those but gets 403 on `DELETE /workspaces/{id}`; only `owner` can delete
- [ ] A user with no membership gets 403 on every `/workspaces/{id}/*` route (not 404 leaking existence beyond auth'd scope — either is acceptable, but be consistent and document the choice in the endpoint docstring)
- [ ] Full invite round trip: owner creates invite → `invite_url` returned → invitee (logged in as a second user) `POST /api/v1/invites/{token}/accept` → invitee appears in members list with the invited role; accepting twice returns 409; expired token returns 410
- [ ] Removing the last owner returns 409; a member can remove themselves
- [ ] `alembic upgrade head` applies cleanly; all workspace rows are only reachable via a `Membership` join (no cross-tenant reads in any query)

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/integration/api/test_workspaces.py tests/unit/services/test_workspace_service.py -v` — create `tests/integration/api/test_workspaces.py` (two-user fixtures: CRUD happy paths, 403 matrix for member/admin/owner/outsider, invite accept round trip, last-owner guard) and `tests/unit/services/test_workspace_service.py` (slug uniqueness, role-rank logic, invite expiry)
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: with two registered users via curl, invite user B into user A's workspace, accept with B's token, then `GET /workspaces/{id}/members` with B's token shows both users and roles

**Dependencies:** T06

**Files likely touched:**
- `backend/app/models/workspace.py`
- `backend/app/schemas/workspace.py`
- `backend/app/services/workspace_service.py`
- `backend/app/services/auth_service.py` (auto-create personal workspace)
- `backend/app/api/deps.py`
- `backend/app/api/v1/endpoints/workspaces.py`
- `backend/app/api/v1/router.py`
- `backend/app/core/config.py`
- `backend/alembic/versions/<new>_add_workspace_tables.py`
- `backend/tests/integration/api/test_workspaces.py`
- `backend/tests/unit/services/test_workspace_service.py`
- `.env.example`

**Estimated scope:** M

---

## Task T09: Workspace UI: switcher, member list, invite accept flow

**Description:** Build the frontend workspace experience on top of T07's auth client and T08's API. Create a Zustand workspace store `frontend/src/stores/workspace-store.ts`: `{workspaces: WorkspaceOut[], activeWorkspaceId: string | null}` with actions `setWorkspaces`, `setActive` (persisted to localStorage key `forge.active_workspace_id`); TanStack Query hooks in `frontend/src/features/settings/hooks.ts`: `useWorkspaces()` (`GET /api/v1/workspaces`), `useMembers(workspaceId)`, `useCreateWorkspace`, `useUpdateMemberRole`, `useRemoveMember`, `useCreateInvite` — all keyed by workspace id and invalidated on mutation. Add a **workspace switcher** to the sidebar (`frontend/src/components/layout/Sidebar.tsx`): a shadcn/ui `Select` (or `DropdownMenu`) listing the user's workspaces with a checkmark on the active one and a "Create workspace" item opening a small `Dialog` with a name field; switching updates the store and invalidates workspace-scoped queries. Build the member management page `frontend/src/features/settings/MembersPage.tsx` at route `/settings/members`: shadcn/ui `Table` of members (name, email, role badge, joined date) visible to all roles; role-change `Select` and remove `Button` rendered only when the current user's role is owner/admin (owner-only for changing admin/owner roles, mirroring the API); an "Invite member" `Dialog` (email + role) that on success displays the returned `invite_url` in a copyable read-only input (clipboard button). Build `frontend/src/features/auth/AcceptInvitePage.tsx` at public-but-auth-required route `/accept-invite?token=...`: reads `token` from the query string, calls `POST /api/v1/invites/{token}/accept` via mutation, shows success → navigates to `/settings/members` with the new workspace activated; shows the API error detail (404/409/410) on failure. Register routes in `frontend/src/router.tsx` (`/settings/members` and `/accept-invite` inside `ProtectedRoute`). Match T08 response schemas exactly: `WorkspaceOut{id,name,slug,plan_tier,role}`, `MemberOut{user_id,email,name,role,joined_at}`, `InviteOut{id,email,role,invite_url,expires_at}`, `InviteAcceptOut{workspace_id,role}`.

**Acceptance criteria:**
- [ ] Sidebar shows the active workspace name; the switcher lists all of the user's workspaces and switching persists across reload (localStorage)
- [ ] Creating a workspace from the switcher dialog makes it appear in the list and switches to it
- [ ] `/settings/members` lists all members with correct role badges; a `member` sees no edit controls, an `admin`/`owner` sees role selects and remove buttons, and forbidden actions are never shown (server 403s are the backstop)
- [ ] Inviting by email shows a copyable `invite_url`; opening that URL while logged in as the invitee accepts the invite and lands on `/settings/members` with the new workspace active
- [ ] Expired/invalid invite tokens show the backend error message on the accept page instead of crashing

**Verification:**
- [ ] Tests pass: `cd frontend && npx tsc --noEmit`
- [ ] Lint/build passes: `cd frontend && npm run lint && npm run build`
- [ ] Manual check: with two accounts in two browser profiles, owner invites member via the dialog, member opens the `invite_url`, accepts, and sees both members on `/settings/members`; member's UI shows no role-edit controls

**Dependencies:** T08, T07

**Files likely touched:**
- `frontend/src/stores/workspace-store.ts`
- `frontend/src/features/settings/MembersPage.tsx`
- `frontend/src/features/settings/hooks.ts`
- `frontend/src/features/auth/AcceptInvitePage.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/router.tsx`

**Estimated scope:** M

---

## Task T10: Email abstraction (verification + invite emails, SMTP/console fallback)

**Description:** Create the email layer in `backend/app/utils/email.py`. Define an `EmailBackend` protocol (`async def send(to: str, subject: str, body_text: str, body_html: str | None = None) -> None`) with two implementations: `SMTPEmailBackend` using **aiosmtplib** (add to `requirements.txt`), configured from new settings in `app/core/config.py` + `.env.example`: `SMTP_HOST` (default `""`), `SMTP_PORT=587`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TLS=true`, `EMAILS_FROM="The Forge <noreply@forge.app>"`; and `ConsoleEmailBackend` that logs the full email via structlog. Factory `get_email_backend()` returns the SMTP backend when `SMTP_HOST` is non-empty, else the console backend — **no SMTP server may be required in dev/test**. Add module-level helpers `send_verification_email(to, token)` and `send_invite_email(to, workspace_name, inviter_name, invite_url)` that render simple HTML+text bodies (inline string templates are fine; verification link = `f"{settings.FRONTEND_URL}/verify-email?token={token}"`) and send through `get_email_backend()`. Wrap these as Celery tasks in `backend/app/workers/email_tasks.py` (import the shared `celery_app` from `app/workers/celery_app.py` created in Phase 0): `send_verification_email_task(user_id)` — generates a signed verification token with **itsdangerous** (`URLSafeTimedSerializer(settings.JWT_SECRET_KEY)`, salt `"email-verify"`, max age 24h) — and `send_invite_email_task(invite_id)`; both load their DB row via the async session (use `asyncio.run` or the project's established sync/async Celery bridge from Phase 0 — keep it consistent with `monte_carlo.py` conventions if any exist yet, otherwise wrap with `asyncio.run`), then call the async helper. Also wire the consumer side: `POST /api/v1/auth/verify-email` in `endpoints/auth.py` with schema `VerifyEmailRequest{token: str}` in `schemas/auth.py` → 200 `{"detail": "email verified"}`, sets `is_verified=True`; 400 on invalid/expired token. Ensure T06's registration enqueue and T08's invite enqueue call these tasks (guarded try/except so a missing broker degrades to a direct synchronous send in dev).

**Acceptance criteria:**
- [ ] With `SMTP_HOST=""` (default), triggered emails are fully logged by `ConsoleEmailBackend` (to, subject, body) and no network/SMTP connection is attempted
- [ ] With `SMTP_HOST` set, `SMTPEmailBackend` delivers through aiosmtplib with STARTTLS when `SMTP_TLS=true`
- [ ] `send_verification_email_task` produces a token that `POST /api/v1/auth/verify-email` accepts; after verification `GET /users/me` shows `is_verified: true`; a tampered or >24h-old token returns 400
- [ ] `send_invite_email_task` sends the invite URL stored on the `Invite` row; re-sending for a nonexistent invite id fails the task without side effects
- [ ] Registering a user or creating an invite works end-to-end with Redis/Celery down (fallback logs the email instead of raising)

**Verification:**
- [ ] Tests pass: `cd backend && pytest tests/unit/services/test_email.py tests/integration/api/test_auth.py -v` — create `tests/unit/services/test_email.py` (factory selection by config, console backend captures output, verification-token round trip + expiry using itsdangerous directly, task fallback path with broker unavailable); extend `tests/integration/api/test_auth.py` with the verify-email endpoint cases
- [ ] Lint/build passes: `cd backend && ruff check app tests && mypy app`
- [ ] Manual check: with default env, register a user and watch the backend/worker log — the verification email (with a working `verify-email?token=...` link) appears in the logs

**Dependencies:** T06

**Files likely touched:**
- `backend/app/utils/email.py`
- `backend/app/workers/email_tasks.py`
- `backend/app/core/config.py`
- `backend/app/api/v1/endpoints/auth.py` (verify-email endpoint)
- `backend/app/schemas/auth.py` (`VerifyEmailRequest`)
- `backend/app/services/auth_service.py`
- `backend/requirements.txt` (aiosmtplib, itsdangerous)
- `backend/tests/unit/services/test_email.py`
- `backend/tests/integration/api/test_auth.py`
- `.env.example`

**Estimated scope:** S

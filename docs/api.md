# The Forge — API Reference (v1)

All routes are under `/api/v1` unless noted. Base URL in dev: `http://localhost:8000`.

**Auth:** most routes require `Authorization: Bearer <access_token>` plus a
`X-Workspace-Id` header (the workspace you're operating in). Public routes are
marked 🔓. API keys authenticate with `X-API-Key` instead of a JWT (see T45).

**Common status codes:**
- `401` — missing/invalid token
- `403` — authenticated but not a member / insufficient role / wrong workspace
- `404` — resource not found (cross-workspace resources read as 404)
- `409` — conflict (e.g. duplicate, wrong run state)
- `422` — validation error
- `429` — rate limit exceeded (`{"detail": "rate limit exceeded"}`)

Every response carries an `X-Request-ID` header (client-supplied or generated).

---

## Auth & Users

### POST `/auth/register` 🔓
Create a user + personal workspace.
- Body: `RegisterRequest` (`email`, `name`, `password` ≥8 chars)
- Returns **201** `UserOut`; **409** duplicate email; **429** too many attempts

### POST `/auth/login` 🔓
- Body: `LoginRequest` (`email`, `password`)
- Returns **200** `TokenPair` (`access_token`, `refresh_token`); **401** bad creds; **429**

### POST `/auth/refresh` 🔓
- Body: `RefreshRequest` (`refresh_token`)
- Returns **200** `TokenPair` (rotated); **401** invalid/expired refresh token

### POST `/auth/verify-email` 🔓
- Body: `VerifyEmailRequest` (`token`)
- Returns **200** `{"detail": "email verified"}`; **400** invalid/expired token

### GET `/users/me`
Returns **200** `UserRead` (profile + onboarding fields).

### PATCH `/users/me`
- Body: `UserUpdate` (`name`, `industry`, `stage`, `primary_fear`)
- Completing all three onboarding fields flips `onboarding_completed`.
- Returns **200** `UserRead`.

### POST `/users/me/password`
- Body: `PasswordChange` (`current_password`, `new_password`)
- Returns **204**; **400** wrong current password.

---

## Workspaces & Members

### POST `/workspaces`
- Body: `WorkspaceCreate` (`name`)
- Returns **201** `WorkspaceOut` (caller becomes owner).

### GET `/workspaces`
Returns **200** `list[WorkspaceOut]` for the caller.

### GET `/workspaces/{workspace_id}` · PATCH `/workspaces/{workspace_id}` · DELETE `/workspaces/{workspace_id}`
- PATCH body: `WorkspaceUpdate` (`name`); requires admin+.
- DELETE requires owner.
- Returns `WorkspaceOut` (200) or 204 for DELETE.

### GET `/workspaces/{workspace_id}/members`
Returns **200** `list[MemberOut]`.

### PATCH `/workspaces/{workspace_id}/members/{user_id}`
- Body: `MemberRoleUpdate` (`role`: owner|admin|member); owner-only for owner/admin grants.
- Returns **200** `MemberOut`.

### DELETE `/workspaces/{workspace_id}/members/{user_id}`
Admin+ or self-removal. Returns **204**; **409** removing the last owner.

### POST `/workspaces/{workspace_id}/invites`
- Body: `InviteCreate` (`email`, `role`); admin+.
- Returns **201** `InviteOut` (includes `invite_url`).

### POST `/invites/{token}/accept`
Returns **200** `InviteAcceptOut`; **404** unknown, **410** expired, **409** already a member.

---

## Blueprints

### POST `/blueprints`
- Body: `BlueprintCreate` (`name`, `industry`, `stage`, `payload` = Format A).
- Returns **201** `BlueprintDetailResponse`; **422** if structural validation fails.

### GET `/blueprints`
Returns **200** `list[BlueprintResponse]` (workspace-scoped).

### GET `/blueprints/{blueprint_id}`
Returns **200** `BlueprintDetailResponse` (includes current payload + vulnerabilities).

### PATCH `/blueprints/{blueprint_id}`
- Body: `BlueprintUpdate` (`name`, `industry`, `stage`)
- Returns **200** `BlueprintResponse`.

### DELETE `/blueprints/{blueprint_id}`
Returns **204**.

### POST `/blueprints/{blueprint_id}/versions`
- Body: `BlueprintVersionCreate` (`payload`)
- Returns **201** `BlueprintVersionResponse`; **422** invalid payload.

### GET `/blueprints/{blueprint_id}/versions`
Returns **200** `list[BlueprintVersionResponse]` (newest first).

### GET `/blueprints/{blueprint_id}/validate?version=N`
Returns **200** `ValidationReport` (`is_valid`, `errors[]`, `warnings[]`).

### POST `/blueprints/{blueprint_id}/review`
AI Forge review; returns **200** `ForgeReviewResponse`; **502** if the LLM
cannot produce schema-valid output.

---

## Simulations

### POST `/simulations`
- Body: `SimulationStartRequest` (`blueprint_version_id`, `mode`, `seed?`, `config?`)
- `mode`: `baseline` | `stress` | `monte_carlo` | `ghost`.
- Returns **201** `SimulationRunResponse`. Baseline runs synchronously; MC
  enqueues a Celery batch (`status: "pending"`); stress stops at the first
  hurdle (`awaiting_decision`).
- **402** when the workspace plan limit is exceeded (`plan_limit_exceeded`).

### GET `/simulations`
Returns **200** `list[SimulationRunResponse]` (newest first).

### GET `/simulations/{run_id}`
Returns **200** `SimulationRunResponse` (+ `progress` for pending MC runs).

### PATCH `/simulations/{run_id}`
- Body: `SimulationVisibilityUpdate` (`is_public`) — leaderboard opt-in.
- Returns **200**; **403** for non-members.

### GET `/simulations/{run_id}/ticks`
Returns **200** `list[TickLogResponse]` (month + KPI JSON).

### POST `/simulations/{run_id}/control`
- Body: `ControlRequest` (`action`: pause|resume|cancel)
- Returns **200** `SimulationRunResponse`; **409** on illegal transitions.

### POST `/simulations/{run_id}/decide`
- Body: `DecisionRequest` (`event_id`, `option_id`)
- Returns **200** `DecisionAppliedResponse`; **409** run not awaiting; **422** unknown option.

---

## Reports (Format C)

### GET `/reports/simulations/{run_id}/report`
Generates + persists the resilience audit on first call (idempotent).
Returns **200** `ReportResponse`; **404** unknown; **409** run not completed.

### POST `/reports/simulations/{run_id}/report/export`
Renders a PDF via WeasyPrint. Returns **201** `{"pdf_url": "..."}`; **500** if
PDF rendering fails.

### POST `/reports/simulations/{run_id}/report/share`
Creates a share token. Returns **201** `{"share_url", "token"}`.

### DELETE `/reports/simulations/{run_id}/report/share`
Revokes the token. Returns **204**.

### GET `/reports/shared/{token}` 🔓
Public report view. Returns **200** `SharedReportResponse`; **404** unknown/revoked.

### GET `/reports/compare?a={run_a}&b={run_b}`
Compares two completed runs. Returns **200** `ComparisonResponse`
(summaries, deltas, kill-vector changes, verdict).

---

## Scenarios (Marketplace)

### POST `/scenarios`
- Body: `ScenarioCreate` (`title`, `description`, `category`, `blueprint_version_id`)
- Returns **201** `ScenarioResponse`.

### GET `/scenarios?category=&page=`
Public browse. Returns **200** `ScenarioListResponse`.

### GET `/scenarios/featured` 🔓
Returns **200** `list[ScenarioSummary]`.

### GET `/scenarios/{scenario_id}` 🔓
Public unless private (author-only). Returns **200** `ScenarioResponse`; **404** for private/unknown.

### POST `/scenarios/{scenario_id}/clone`
Copies the scenario into the caller's workspace. Returns **201** `CloneResponse`.

### DELETE `/scenarios/{scenario_id}`
Author or admin. Returns **204**; **403** otherwise.

---

## Leaderboard

### GET `/leaderboard` 🔓
Top public MC runs by resilience score. Returns **200** `LeaderboardResponse`.

---

## Billing & Usage

### POST `/billing/checkout`
- Body: `CheckoutRequest` (`tier`: pro|enterprise)
- Returns **200** `CheckoutResponse` (`checkout_url`); **422** no price configured.

### POST `/billing/portal`
Returns **200** `PortalResponse`; **404** no Stripe customer yet.

### GET `/billing/subscription`
Returns **200** `SubscriptionResponse`.

### GET `/billing/usage`
Returns **200** `UsageResponse` (current-period meters + plan limits).

### POST `/webhooks/stripe` 🔓
Stripe signature-verified webhook. Returns **200** JSON; **400** bad signature.

---

## API Keys

### POST `/api-keys`
- Body: `ApiKeyCreate` (`name`, `scopes[]`, `rate_limit_rpm?`)
- Admin/owner only. Returns **201** `ApiKeyCreatedResponse` (plaintext key once).

### GET `/api-keys`
Admin/owner only. Returns **200** `list[ApiKeyResponse]`.

### DELETE `/api-keys/{api_key_id}`
Revokes the key. Returns **204**; **404** unknown.

---

## Admin

All admin routes require `is_admin=true` on the user (else **403**).

### GET `/admin/stats`
Returns **200** `AdminStatsResponse`.

### GET `/admin/users?page=&q=`
Returns **200** `AdminUserListResponse`.

### GET `/admin/workspaces?page=`
Returns **200** `AdminWorkspaceListResponse`.

### GET `/admin/audit-log?page=&limit=&user_id=&path=`
Returns **200** `AuditLogListResponse` — mutating-request audit trail (T49).

---

## Probes & Metrics (no auth, not under /api/v1)

| Route | Purpose |
|---|---|
| `GET /health` | Liveness — always 200 `{"status": "ok", "version": ...}` |
| `GET /ready` | Readiness — 200 when DB+Redis pass, else 503 with failing check |
| `GET /metrics` | Prometheus text format (`http_requests_total` etc.) |
| `WS /ws/simulations/{run_id}?token=` | Live tick/event stream |

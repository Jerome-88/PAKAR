# Shared workspace — 8 November 2026

PAKAR now opens without registration, login or a session cookie. The default is
`AUTH_REQUIRED=false`, configured explicitly in the local backend and VPS template.
Every visitor can read and edit business projects and conversations. Calls to AI
remain explicit and retain the previous cost/token/time limits.

The database keeps a stable internal `workspace_pakar` actor for new records.
Existing project ownership is not rewritten: shared business requests resolve the
stored owner internally, and the project list includes previous business projects.
Resource validation, revisions, project-scoped idempotency, conversation context
and simulation state remain in place. The optional legacy account mode can still
be enabled explicitly with `AUTH_REQUIRED=true`.

`/api/auth/me` remains the frontend bootstrap endpoint and returns shared workspace
metadata with HTTP 200 and no cookie. Account controls are absent in shared mode.
Old login/register URLs redirect to their validated intended destination. A backend
connection failure shows a retry action instead of sending users into a login loop.

## Files

- Backend: `app/config.py`, `app/__init__.py`, `app/auth.py`,
  `app/repository.py`, `app/business/api.py`, `app/business/repository.py`.
- Frontend: `src/api/client.ts`, `src/auth/auth-context.ts`,
  `src/auth/AuthContext.tsx`, `src/auth/ProtectedRoute.tsx`,
  `src/pages/Auth/AuthPage.tsx`, `src/pages/Business/BusinessHomePage.tsx`,
  `src/components/AppShell/AppShell.tsx`.
- Tests: `backend/tests/test_shared_workspace.py`,
  `backend/tests/conftest.py`, `frontend/src/App.test.tsx`.
- Configuration/docs: both environment examples, `compose.yaml`,
  `deploy/compose.vps.yaml`, `deploy/README.md`, `README.md`, `PRODUCT.md`.

## Verification

- 110 frontend tests across 20 files passed; ESLint and TypeScript/Vite build passed.
  The existing large shared-bundle warning remains.
- Backend shared-workspace, account compatibility, business API and conversation
  regressions passed against the isolated `pakar_authless_test` database.
- New backend coverage exercises anonymous upload, fixture simulation, report/export,
  a persisted chat with a local stubbed model, reload and access to previous owners'
  projects. No external inference is used by these tests.
- Four browser workflows passed for graph controls, 120 nodes, saved summaries
  and chat drafts/retry.
- Actual localhost API/browser verification passed without response interception,
  authentication cookies or temporary sessions. Existing Pepsodent project, graph,
  summary and saved live chat remain accessible on desktop/mobile. Old account
  URLs redirect correctly; drafts persist between tabs. Zero page errors, 401s,
  application writes or paid calls occurred during this read-only browser check.
- Before/after database hashes confirm that the original saved analysis input,
  result and owner are unchanged across the backend restart.
- Both Compose configurations and scoped diff checks passed.

Proof and captures: `backend/data/runtime-audit/2026-11-08/shared-workspace/`.
This verifies shared access and preserved workflows; it does not measure new model
quality or deploy/expose the service through ngrok.

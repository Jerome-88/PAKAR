# PAKAR

The homepage and `/business` workspace implement the PAKAR business workflow: intake, claim/persona review, analysis, traceable findings, interaction graph/timeline, scenario comparison and HTML export. Authentication is required for business resources. `/legacy` retains the previous policy landing and the policy routes remain available.

See [implementation status](../docs/PAKAR_IMPLEMENTATION_STATUS.md) for setup and the opt-in browser workflow test. Business fixtures are labeled and restricted to synthetic projects; live mode needs the configured backend provider/runtime.

## Shared frontend and legacy policy workflow

The legacy landing and policy simulation screens remain available within the PAKAR frontend.

## Running the project

```bash
bun install
bun run dev
```

To create a production build:

```bash
bun run build
bun run preview
```

The frontend uses `VITE_API_URL=/backend` by default. During development, Vite proxies that path to the FastAPI service at `http://localhost:5001`; the production Nginx configuration keeps the same `/backend` path. This same-origin path allows the browser to send the authentication cookie on all API requests. Copy `.env.example` to `.env` only when you need to override this path.

Authentication uses `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, and `GET /api/auth/me`. Dashboard, project, report, and simulation routes require an authenticated cookie session. Local workspace and workflow prototype data are namespaced by the authenticated user ID.

Public routes are `/`, `/login`, and `/register`. Registration requires a name, email, password of at least 6 characters, and matching password confirmation.

IDs beginning with `demo-` always use local demonstration data and timers. Backend-created quick demos keep using backend workflow data and interactions. The pilot project discussion form remains a prototype interaction and does not send or save data.

From the repository root, `make full-up` builds the production frontend image and serves it through Nginx at `http://localhost:5173`. Nginx provides SPA route fallback and proxies `/backend/*` to the FastAPI container.

The default PAKAR business flow is upload → description → start analysis.
`/business/new` creates/uploads the project and starts `quick-analysis`, then
navigates directly to progress/results. Optional context, engine and round controls
are under additional settings. No separate claim approval/discovery/profile clicks
are needed. Existing project source/profile editors remain available for inspection.
See `../docs/PAKAR_TRIAL_GUIDE.md` for the current trial flow.

New quick runs default to threaded swarm discussion. Additional settings expose
customer perspectives, rounds and pairwise mode. The discussion tab shows replies,
access labels and declared stance histories; report appendices reuse that view.
Historical pairwise runs keep their existing tabs. `RUN_BUSINESS_E2E=true` enables
`business-swarm.spec.ts` against the local API/PostgreSQL; the test explicitly
chooses fixture mode and makes no paid inference calls.

## Project chat and ideas

The project `Chat & ide` tab supports named specialist chat, source excerpts, idea files/text, explicit version saves and separate selected-version analysis. Intake can open this workspace before running a simulation; saved results link back to chat. See [workflow and verification](../docs/PAKAR_PROJECT_CHAT_2026-10-31.md).

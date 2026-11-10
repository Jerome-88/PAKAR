# PAKAR

The active business workspace opens without login or registration by default.
`AUTH_REQUIRED=false` uses a shared workspace: visitors can access and edit the
same business projects and saved conversations. Old demo links remain available;
AI calls still require explicit actions and obey the configured budgets. Optional
legacy account mode can be enabled with `AUTH_REQUIRED=true`.

PAKAR is a business co-analyst with stakeholder/persona simulation, analytical specialists, traceable assumptions, evidence and versioned stress tests. The business workspace is at `/business`; the homepage now opens PAKAR. The original policy prototype remains at `/legacy` and its existing routes.

See [PRODUCT.md](PRODUCT.md) for the product contract and [implementation status](docs/PAKAR_IMPLEMENTATION_STATUS.md) for capabilities, setup, verification and remaining live release gates.

For a network-free development run, configure `OASIS_ENABLED=false`, `DEFAULT_SIMULATION_ENGINE=deterministic`, and `EMBEDDED_WORKER=true` for local processes. Apply migrations with `cd backend && python -m alembic upgrade head`, start the API and frontend, then open `/business` and select **Analisis ide sendiri**. Compose deployments use the separate worker instead.

Live business mode retains the bundled OASIS/CAMEL runtime and requires its environment plus a configured model provider. BPS integration additionally requires `BPS_API_KEY` and a curated `PAKAR_BPS_INDICATORS` configuration. Offline fixtures do not establish live model quality, source applicability or production readiness.

## Saved public demo

The Pepsodent example uses the main app's homepage, intake, idea workspace and
three result tabs: **Ringkasan**, **Diskusi** and **Tanya PAKAR**. It reads a real
recorded Groq run on synthetic inputs: ten personas, two rounds, 22 messages
and four completed AI specialist reviews. The shared D3 graph supports node
dragging, canvas panning, zoom, fit and reset, with Executive Summary directly
below. Intake fields are locked; the workspace and Tanya PAKAR display the actual
idea and saved specialist reviews with new-message controls disabled. The demo
makes no new AI calls, uploads or backend API requests. Repeated responses remain
disclosed; the result is a hypothesis for validation. Internal documents and
credentials are excluded from the public snapshot.

Build and preview the isolated static demo without a backend:

```sh
cd frontend
npm install
npm run build:demo
npm run preview:demo
```

Public demo: https://pakar-demo-pepsodent.khakibowl1.chatgpt.site.
The shared-app/network v2 update is published with the existing public audience.

For a local preview, open `http://127.0.0.1:4180/`. `build:demo` sets
`VITE_PUBLIC_DEMO_ONLY=true` and writes `frontend/dist-demo/`; its root opens the
shared homepage without auth-status requests. `?view=intake|workspace|result`
opens the saved surfaces; result `tab=summary|swarm|chat` preserves the selected
tab on reload. **Analisis ide sendiri** is visibly unavailable in the isolated
build. Publish only the generated static directory. The normal `npm run dev` /
`npm run build` app opens saved intake at `/business/demo` and retains
**Analisis ide sendiri** for live intake and chat.

To regenerate the reviewed public snapshot from its frozen archive, run
`python scripts/export-public-demo.py` from the repository root before building.
See [demo provenance, verification and publication status](docs/PAKAR_PUBLIC_DEMO_2026-11-08.md).

## Legacy policy workflow and shared infrastructure

The retained policy workflow uses the shared React frontend and FastAPI backend. Its staged workflow covers source intake, graph construction, environment preparation, simulation, progressive reporting, and evidence-aware follow-up.

## Architecture

- `frontend/`: React 19, TypeScript, and Vite user interface.
- `backend/`: FastAPI application factory, Pydantic request validation, PostgreSQL persistence, local or Firebase document storage, and background jobs served by Uvicorn.

The backend retains a grounded deterministic policy provider for tests and offline use. In the full Docker workflow, stages 02 and 03 can use the bundled OASIS social simulation runtime: graph entities become OASIS agents, Twitter and Reddit worlds run in parallel, actions stream into PostgreSQL, and completed actions update a Zep temporal graph. Uploaded PDF, DOCX, Markdown, and TXT files retain stable local evidence IDs and citations throughout the external runtime.

## Local Run

### One-command Docker

Start the backend with its persistent PostgreSQL database and uploaded-document storage:

```sh
make up
```

Start the full stack instead:

```sh
make full-up
```

The services are available at:

- Frontend: `http://localhost:5173` when using `make full-up`
- Backend API: `http://localhost:5001`
- API documentation: `http://localhost:5001/docs`
- Health check: `http://localhost:5001/health`

Use `make up-d` or `make full-up-d` for detached startup, `make health` to check the services, and `make full-down` to stop them. PostgreSQL data and uploaded documents are retained in separate Docker volumes across shutdowns and image rebuilds.

`make down` and `make full-down` never delete application data. To remove the database and uploaded documents intentionally, run `make reset` and then the displayed confirmation command.

Copy `.env.example` to `.env` to customize host ports, CORS origins, upload limits, job delay, storage, or frontend build variables.

Direct CAMEL/OASIS execution is enabled and selected by default. Business simulations need `LLM_API_KEY` and the installed isolated runtime; legacy graph workflows also need `ZEP_API_KEY`. Set `OASIS_ENABLED=false` and `DEFAULT_SIMULATION_ENGINE=deterministic` to run offline. Enable `LLM_STRUCTURED_OUTPUTS=true` only with a model/provider supporting strict JSON Schema responses. The worker runs its bundled simulation engine locally and requires no external source tree or HTTP simulation sidecar.

To use Firebase Storage instead of local uploaded-document storage, set `STORAGE_BACKEND=firebase`, `FIREBASE_STORAGE_BUCKET=<your-bucket-name>`, and point `FIREBASE_CREDENTIALS_HOST_PATH` at a Firebase service-account JSON file on the host. Compose mounts that file at `GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/firebase-service-account.json` for the API and worker containers. The `secrets/` directory is git-ignored.

### Local processes

Start the backend:

```sh
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
python run.py
```

Start the frontend in another terminal:

```sh
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend uses `http://localhost:5001` by default. IDs beginning with `demo-` continue to use the original local browser demo; newly uploaded projects use the FastAPI service. See `frontend/.env.example` to override this behavior.

## Workflow API

1. `POST /api/projects` uploads project metadata and real source files.
2. `POST /api/simulations/<id>/graph-build` generates a source-grounded ontology and policy graph.
3. `POST /api/simulations/<id>/environment/generate` synchronizes evidence to Zep, creates one OASIS profile per eligible graph entity, and generates time, behavior, event, and platform configuration.
4. `POST /api/simulations/<id>/runs` executes Twitter and Reddit OASIS worlds in parallel, incrementally persists actions, and waits for temporal graph-memory ingestion before completion.
5. `POST /api/simulations/<id>/reports` creates report sections, risks, and evidence references.
6. `POST /api/simulations/<id>/interactions` supports report, persona, evidence, risk, comparison, and revision tools.
7. `POST /api/simulations/<id>/interviews` interviews selected synthetic personas.
8. `POST /api/simulations/<id>/graph/feedback` applies reviewed graph changes and invalidates downstream artifacts.

The frontend-compatible stage endpoint is `POST /api/simulations/<id>/stages/<stage>/start`. Poll `GET /api/simulations/<id>` for a canonical workflow snapshot.

## Verification

```sh
cd backend
.venv/bin/python -m pytest -vv
.venv/bin/python -m compileall -q app

cd ../frontend
npm run lint
npm run build
```

Backend tests cover deterministic generation, all four document types, PostgreSQL persistence and job recovery, upload validation, round configuration, simulation control, cited reports, all interaction tools, and the complete API workflow.

Authentication uses seven-day opaque server sessions in an HTTP-only cookie. Register at `/register` with name, email, and a password of at least 6 characters. Backend projects and workflow artifacts are private to their creator; legacy unowned rows remain inaccessible.

Containerized verification is also available:

```sh
make test
```

Run the deterministic, network-free quality gate with `make evaluation`. It emits JSON and enforces `EVALUATION_FAIL_THRESHOLD` (default `0.8`) for required-concept recall, citation validity, and citation coverage; fixture format and versioning are documented in `evaluations/README.md`.

After `make full-up-d`, run `make smoke` to exercise the production frontend proxy, register/login cookie flow, document upload, all five workflow steps, report citations, and report interaction. The smoke uses bounded timeouts and only attempts to remove the project it creates; set `BASE_URL` to target another deployment.

To run the opt-in browser test against real OASIS, configure `LLM_API_KEY` and `ZEP_API_KEY` in `.env`, install Playwright Chromium with `cd frontend && npx playwright install chromium`, then run:

```sh
./scripts/oasis-e2e.sh
```

The runner starts the production Compose stack, drives Steps 1–5 through Chromium with five profiles and three rounds, and verifies OASIS environment provenance, Twitter and Reddit completion, normalized events, OASIS report generation, report interaction, and persisted raw actions. Set `KEEP_STACK=true` to retain containers after the run or `OASIS_STAGE_TIMEOUT_MS` to override the 15-minute per-stage timeout.

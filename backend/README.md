# PAKAR Backend

Business APIs live under `/api/v1/business`. Apply migration `0015_pakar_business` before startup. Business resources share session auth, PostgreSQL, storage and the leased worker infrastructure, with separate business projects, documents, claims, personas, analyses and events. See [implementation status](../docs/PAKAR_IMPLEMENTATION_STATUS.md) for the current business workflow and live integration limits.

The sections below describe shared infrastructure and the retained policy workflow. Zep remains a requirement for legacy graph operations; business OASIS interactions do not require it at startup.

FastAPI, Pydantic, PostgreSQL, and local/Firebase file storage implementation of the policy workflow. It uses local email/password accounts.

The backend uses a Python application factory and service-oriented structure tailored to policy simulation. PostgreSQL-backed jobs provide leased, retryable task execution, while the grounded deterministic provider supports local use without mandatory AI services.

From the repository root, `make up` builds and starts PostgreSQL and the API. Use `make full-up` to include the frontend. PostgreSQL data and uploaded documents use separate persistent volumes.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Uploaded PDF, DOCX, Markdown, and text documents are stored below `DATA_DIR/uploads` by default, or in Firebase Storage when `STORAGE_BACKEND=firebase`; extracted text and workflow state are durable in PostgreSQL. Set `JOB_DELAY=0` for fast tests. In-progress jobs recover when the app starts.

Run the automated tests with `pytest`. The suite covers authentication and authorization, all document formats, deterministic generation, durable job recovery, validation, simulation controls, and the complete upload-to-report-to-interaction API workflow.

Frontend aliases use `/api/simulations/<id>/stages/<stage>/start`, `/pause`, `/resume`, and `/interactions`. Canonical project, graph, environment, run/event/control, report/evidence, and interaction resources are also exposed.

`python run.py` starts Uvicorn on port 5001. Keep `workers=1`: workflow execution currently uses process-local worker threads. A multi-worker deployment requires leased database jobs or an external queue even though durable state lives in PostgreSQL.

## Configuration

Copy `.env.example` to `.env` to override defaults. `DATABASE_URL` must be a SQLAlchemy PostgreSQL URL using the psycopg driver. Registration is open and automatically creates a seven-day opaque session in the HTTP-only `pakar_session` cookie. `SESSION_COOKIE_NAME`, `SESSION_TTL_SECONDS`, and `SESSION_COOKIE_SECURE` control cookie deployment settings. Set `SESSION_COOKIE_SECURE=true` behind HTTPS.

Set `STORAGE_BACKEND=firebase`, `FIREBASE_STORAGE_BUCKET`, and `FIREBASE_STORAGE_PREFIX` to store uploaded source files in Firebase Storage. Authentication uses Application Default Credentials, so set `GOOGLE_APPLICATION_CREDENTIALS` to a service-account JSON path. In Docker Compose, set `FIREBASE_CREDENTIALS_HOST_PATH` to the host JSON path; it is mounted read-only at `/app/secrets/firebase-service-account.json`.

Compose runs Alembic through a one-shot migration service before the API and worker start. All database timestamps use PostgreSQL `TIMESTAMP WITH TIME ZONE` and application code supplies timezone-aware UTC values. Workflow state and job configuration use `JSONB`.

## Analysis providers

`POLICY_PROVIDER=deterministic` is the default. It derives ontology terms, graph issues, personas, simulation events, reports, interviews, and graph-memory feedback from stored document chunks with reproducible output and structured citations.

Set `POLICY_PROVIDER=openai`, `LLM_API_KEY`, and optionally `LLM_BASE_URL`/`LLM_MODEL` to use an OpenAI-compatible provider for ontology and report generation. Source IDs returned by a model are never trusted; citation provenance is resolved and validated against PostgreSQL document chunks.

For Groq, set `LLM_BASE_URL=https://api.groq.com/openai/v1`,
`LLM_MODEL=openai/gpt-oss-20b`, `LLM_STRUCTURED_OUTPUTS=true`, and put the key
in `FREE_AI_KEY` (or the standard `LLM_API_KEY`). `FREE_AI_KEY` takes precedence
only for the exact Groq hostname, including OASIS child processes. Restart API
and worker processes after changing `.env`. OpenRouter routing/pricing settings
do not apply to Groq, and there is no automatic fallback to the old provider.
Groq quotas remain account-dependent; a successful small call does not establish
that a full multi-agent run fits those quotas.

Groq GPT-OSS stakeholder turns reserve 1,600 completion tokens and use low
reasoning effort so reasoning does not exhaust the old 650-token JSON budget.
Only explicit HTTP 429 rejections with a bounded `Retry-After` may wait and
redispatch; generation errors and other providers are not retried. The outer
process and turn deadlines still apply. Internal specialist requests use a
token-counted context window under `PAKAR_GROQ_REQUEST_TOKEN_LIMIT=6500`
(including output reservation and overhead); omitted source counts remain
explicit in each review's `context_window`. Install the `llm` extra for its
tokenizer dependency. This bound was chosen for an observed 8,000 TPM account;
use a lower ceiling if your account has a lower limit.

Documents are split into deterministic, content-hashed chunks. Graph nodes, report sections, risks, and interaction answers expose structured evidence. Internal storage paths are not returned by project or evidence APIs.

The API only enqueues workflow stages in normal deployments. `worker.py` claims jobs with PostgreSQL `FOR UPDATE SKIP LOCKED`, leases, heartbeats, retries, and stale-revision checks. Tests use the embedded worker for speed.

## OASIS runtime

Direct CAMEL/OASIS execution is enabled and selected by default. Business simulations require `LLM_API_KEY` and the installed isolated runtime; legacy graph workflows additionally require `ZEP_API_KEY`. Set `OASIS_ENABLED=false` and `DEFAULT_SIMULATION_ENGINE=deterministic` for offline operation. The worker remains authoritative for leases and retries. Tests use deterministic or local scripted providers and do not spend LLM credit.

Set `LLM_STRUCTURED_OUTPUTS=true` only when the selected model/provider supports strict JSON Schema output. Business turns constrain actor/state IDs and reviews constrain source references, role and unvalidated status. The server reducer and finding validator still check every response. OpenRouter requests require a compatible endpoint and do not switch models on failure. The response mode is frozen with the analysis snapshot and inherited by scenarios.

New quick business runs use bounded `reactive-v2` discussion. Directed questions
activate their recipient; compact responses bind metadata to a visible trigger.
The `choice_dialogue` protocol lets the model choose a valid interaction and
message/participant number together, while the original reducer still validates
the action. Structural dialogue diagnostics are included in the saved report;
they do not establish semantic answer quality. Legacy snapshots retain their
frozen policy. See [reactive implementation evidence](../docs/PAKAR_REACTIVE_SWARM_RESULTS_2026-10-31.md).

`GET /health` reports process liveness. `GET /ready` also verifies that PostgreSQL accepts queries and is used by the container health check.

`GET /api/v1/business/analyses/{id}/report` returns the authenticated, read-only eight-section PRD report, including source excerpts, causal interaction chains, validation owners and baseline/scenario deltas. The HTML export endpoint renders this same projection as a readable printable document. Existing saved analyses can use the new report without rerunning models or changing saved results. The polling analysis response keeps a compact report manifest.

`CORS_ORIGINS` must list explicit browser origins; wildcard origins are rejected because credentialed CORS is enabled. Unsafe authenticated browser requests are accepted only from those origins. The defaults allow the local Vite origins. Health endpoints, OpenAPI documentation, and `/api/auth/*` are public; all project, simulation, run, report, and interaction endpoints require authentication and expose only resources owned by the current user.

Auth endpoints are `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, and `POST /api/auth/logout`. Install `.[llm]` only when implementing an OpenAI-compatible provider; the current engine intentionally remains deterministic and offline.

## Test

```sh
.venv/bin/python -m pytest -vv
.venv/bin/python -m compileall -q app
.venv/bin/python -m app.evaluation
```


## Business analysis deadlines and usage

Business attempts share one monotonic deadline across BPS, OASIS startup/turns and specialist review, reserving a short finalization window. External BPS/specialist calls run in isolated killable processes; business-stream execution no longer adds 30 seconds. On deadline or cancellation, children are killed and reaped. This bounds external waits; database availability and host process termination remain operational concerns.

New live business jobs use one attempt to avoid repeating already-billed inference after a failure or lost worker. Start a new analysis explicitly after inspecting the cause. Fixture jobs retain retries. Default tests isolate developer credentials; installed OASIS integration checks use a local scripted provider.

`result.usage` aggregates per-call phase/role, model, attempt, duration, tokens and provider-reported costs. Missing cost stays unknown, with a separate reported subtotal and coverage count. Failed calls retain conservative token reservations. Runtime usage is also available in the simulation and progress audit events. The audit frontend falls back to simulation usage for older analyses.

Optional `PAKAR_OPENROUTER_MAX_PRICE` is a JSON object with prompt/completion maxima in USD per million tokens and an optional per-request maximum in USD. When configured, expensive routes are excluded and provider fallback is disabled. This is a routing ceiling, not an account spending limit; inspect current provider prices and reserve a session budget before paid verification. No API credentials belong in client config, URLs returned to users, logs or audit artifacts.

BPS curated entries may include explicit `selection` codes (`vervar`, `turvar`, `turtahun`). The adapter checks returned variable/period/unit/dimensions, retains raw scale and historical freshness, and never turns contextual official observations into verified business demand. See `../docs/PAKAR_EXECUTION_RESULTS_2026-10-30.md` for measured scope and remaining gates.

## Specialist reviews and publication validation

New analyses freeze `review_policy=paired-v2`, prompt `pakar-1.2` and
`review_concurrency` (default 1, optional 2) in their input snapshot. Market/Finance
share a frozen peer window, followed by Legal/Risk with validated prior results.
Merges follow role order. Default transport is serial following an inconclusive
two-request live trial; mode 2 remains opt-in. Runtime reserves review time,
specialist calls have bounded output/time, and shared token reservations use a
lock. Existing snapshots retain their original policy. OpenRouter specialist
requests prefer latency within the configured price ceiling; this does not change
the model or enable provider fallback.

`POST /api/v1/business/projects/{id}/quick-analysis` is the default automatic
workflow. After upload it queues a leased job immediately. The worker accepts
source claims as assumptions, keeps duplicate/incompatible numerical inputs
unknown, and generates personas without marking human review complete. Discovery
has a 25-second process boundary and consumes the same attempt token/time budget
as simulation and review. Contextual fallback is labeled explicitly. Roles/names
are grounded in document role mentions and basic business perspectives; model
goals remain hypotheses. A fenced preparation checkpoint freezes the resolved
snapshot once and saves profiles for inspection. Scenarios reuse those IDs and
inputs. Idempotent re-submission does not enqueue another live job.

The manual discovery route returns safe 504/502 responses for provider timeout
or invalid responses rather than an uncaught 500. Automatic discovery is not a
human approval: raw project claims keep their review states; the prepared snapshot
records automatic input acceptance and `human_reviewed=false` explicitly.

Call workers and OASIS children watch the original parent process and exit when
it dies. Lease recovery fences stale workers and does not automatically repeat
live inference. Stopping a local child cannot guarantee an upstream refund.

Optional curated `publication_comparison` metadata records an official BPS
publication URL, checksum and table/page with matching selection/unit/period.
Conflicting numbers remain separate with status `CONFLICTING` and scalar
`value=null`; numerical agreement alone does not verify a business claim.

Finding admission rejects false explicit same-currency numeric comparisons.
For historical results, API/report/export apply a read projection that holds
those findings, updates published counts/tasks and labels disagreements referring
to held findings. Raw stored results remain immutable. This is a narrow arithmetic
check, not a semantic fact checker. See
`../docs/PAKAR_FOLLOWUP_RESULTS_2026-10-30.md` for measured outcomes and limitations.

## Threaded stakeholder swarm

Quick analysis defaults to `interaction_mode=swarm`, `customer_count=4`, at most
eight personas and three rounds. Profiles expand into explicitly synthetic
customer lenses, with IDs frozen once before execution. Config/interaction policy
is inherited by scenarios; absent mode fields keep historical pairwise behavior.

`SwarmSimulation` adds public/private threads, reply access checks and declared
stance histories over the existing financial reducer. Message/stance actions
cannot update financial inputs. Participant prompts receive only visible events
and no other actor's private state dump. Quiet rounds respect scheduled shock
start/expiry; budget stops remain partial. Agreement never terminates a run as
validated consensus. OASIS/CAMEL still performs each scheduled persona call through
the business adapter. Specialist context and report/export retain the discussion.

Tests use the installed isolated runtime with a local scripted HTTP provider and
fixture API/browser flows. See `../docs/PAKAR_SWARM_RESULTS_2026-10-31.md` for
evidence and limits; no paid swarm-model validation has been performed.

Runtime interruptions after committed interactions now replay the validated
event stream into a partial simulation, retaining the original remaining review
budget. Unknown interrupted usage reserves the whole runtime token allocation.
Historical timeout failures can expose a read-only partial report without
rewriting stored results or starting model calls; specialist AI review is marked
as not run. Swarm request timeouts and admission checks complement the parent
process boundary. See `../docs/PAKAR_TIMEOUT_RECOVERY_2026-10-31.md` for the
observed live failure, recovery guarantees and limits.

`POST /api/v1/business/analyses/{id}/specialist-review` explicitly queues a
bounded continuation of an original partial AI run whose specialist calls have
not started. Authentication and `Idempotency-Key` are required. The frozen
discussion/evidence and source result hash travel in the new snapshot; no new
discovery, simulation or evidence request is made. Source-wide deduplication
under the project lock prevents duplicate paid jobs even with different keys.
New usage counts reviewer calls only. Scenario creation removes this review
seed. See `../docs/PAKAR_SPECIALIST_CONTINUATION_2026-10-31.md` for live results
and the three outstanding provider rate-limit failures.

The subsequent saved live demo completed all four reviews; see
`../docs/PAKAR_LIVE_DEMO_2026-10-31.md`. Optional
`PAKAR_OPENROUTER_PROVIDER_ORDER` pins a JSON list of provider names while keeping
price caps and disabled fallback intact. Provider identity is recorded on calls.
Completed fully reported runtime usage now settles reservations before review;
unknown usage still reserves conservatively. Specialist continuation accepts
explicit `retry_failed=true` to inherit accepted reviews and call only remaining
roles. Each continuation records source lineage and bills only its new calls.
Scenario creation clears both the frozen review seed and selected reviewer list.

## Project conversations

Apply Alembic head (`0016_business_conversation`) for persistent one-agent chat, immutable idea revisions and explicit revision-based swarm runs. Sending a turn invokes the provider; reading history, uploading sources and saving ideas do not. Queue leasing, ownership and no automatic paid retry remain enforced. See [implementation and verification](../docs/PAKAR_PROJECT_CHAT_2026-10-31.md).

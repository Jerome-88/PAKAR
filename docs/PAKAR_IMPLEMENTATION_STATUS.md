# PAKAR implementation status

Implemented against proposed v1.1. This is a development MVP; live effectiveness and pilot release gates remain to be measured.

Next execution plan: [30 October 2026 — BPS, runtime budgets and end-to-end demo](PAKAR_EXECUTION_PLAN_2026-10-30.md). This is planned work, not a record of completed verification.

## Available

- `/` opens PAKAR and `/business` opens the authenticated workspace. `/legacy` opens the previous policy landing; existing policy routes remain available.
- Project context/classification, file upload, paragraph/table-aware parsing, source offsets and editable claims.
- Claim/persona approval before freezing an analysis snapshot. Later edits do not rewrite baseline output.
- Contextual stakeholder candidates offline; a schema-validated LLM discovery adapter for live operation. Persona identities are isolated by project.
- Separate simulation and analytical layers. Live specialist reviews retain failures and disagreements.
- Actions validated by actor/target, role, revision, visible causal parents and response strategy. Offers require acceptance. Private cost messages do not reach customer personas.
- PostgreSQL queue extended with business analysis targets, leases, heartbeats and fenced publication. Attempts have separate runtime namespaces. Progress/event APIs support SSE and cursors; the workspace currently polls.
- BPS adapter with curated numeric paths, fixed official host, no redirects, response bounds, cache and explicit unavailable/partial status. Observations are not automatically verified business claims.
- Decimal unit economics, conditional margin/break-even, missingness, findings registry, source/event inspection, report and HTML export.
- Default final-report view with eight PRD sections, source and causal-chain disclosures, proposed validation tasks/owners, numeric scenario comparison and readable printable HTML. Report projection uses saved inputs/results and makes no model calls.
- Separate-run scheduled supplier-cost, competitor-price and regulation shocks. Comparison includes metrics, states, shock context, new/shared findings and source access.
- Relationship graph with keyboard nodes, mobile persona selector, causal event links and profile provenance.

## Run

Use the existing PostgreSQL setup; install `backend/.[test,llm]`. Run `python -m alembic upgrade head` before API/worker startup. Migration `0015_pakar_business` adds business resources and a business job target without deleting policy artifacts.

Offline development configuration:

```text
OASIS_ENABLED=false
DEFAULT_SIMULATION_ENGINE=deterministic
EMBEDDED_WORKER=true
```

Start `python run.py` in `backend` and `npm run dev` in `frontend`. Register, choose **Coba proposal sintetis**, review claims/personas, then select **Fixture sintetis** in analysis configuration.

Compose production uses the separate worker with the embedded worker disabled. The Docker image retains the pinned OASIS/CAMEL dependency environment.

Live business mode requires `OASIS_ENABLED=true`, `LLM_API_KEY`, `LLM_MODEL`, optional `LLM_BASE_URL`, and the installed isolated OASIS environment. Legacy graph workflows still use Zep; the business interaction adapter maintains scoped memory/state/relationships without a Zep graph at startup.

BPS uses `BPS_API_KEY` and `PAKAR_BPS_INDICATORS`: a JSON list of records with `region`, numeric `domain`, numeric `variable`, numeric `period_code`, `period_label` and `unit`. Verify real catalog IDs; time codes must not be guessed from calendar years. Keys never belong in frontend config or persisted source URLs. Official documentation: https://webapi.bps.go.id/documentation/ .

Default limits: 20 MiB/file, 32 MiB/request, configured project/file quotas, up to 24 personas and 12 rounds. Lower deployment limits remain authoritative. Conservative token reservations can stop a run early with partial status. Runtime billing remains unknown if not supplied.

## Verification

Backend tests cover authorization, private-message visibility, source spans, claim edits/version conflicts, project isolation, idempotency, fixture analysis, scenario deltas, baseline immutability and export. The OASIS bridge is tested against a protocol fake with an environment/SQLite action log; this does not establish live model quality.

The browser test drives real API/database requests through upload, claim/persona review, fixture analysis, timeline and comparison:

```text
RUN_BUSINESS_E2E=true
PLAYWRIGHT_BASE_URL=http://127.0.0.1:5173
PLAYWRIGHT_SKIP_WEBSERVER=1
npx playwright test business-workflow.spec.ts --project=chromium
```

The synthetic example has price 30,000/unit, variable cost 12,000/unit and fixed costs 36,000,000/month: break-even 2,000 units/month. An explicitly selected match-price strategy after a 20% competitor price cut gives 3,000 units/month. Both are conditional calculations; demand remains unknown.

## Remaining release gates

1. Expand live OASIS/model coverage beyond the two-persona/two-round baseline and scenario smoke below. Complete exact runtime billing instrumentation and strict end-to-end wall-clock enforcement; measure validity/latency across cases and seeds.
2. Extend the catalog-confirmed national BPS sample below to the actual project regions/indicators and validate numeric scale, freshness and claim applicability. Successful retrieval does not automatically issue verified statistical claims.
3. Build an independently reviewed business dataset and compare single LLM, single LLM with tools, specialists without personas, and full PAKAR under comparable budgets. No measured superiority is claimed.
4. Exercise process-termination recovery and business retention/deletion operations before real company documents. Enterprise controls are outside this pilot.
5. Validate industry-specific action semantics beyond the initial supplier/operator/customer model. Regulation shocks introduce hypotheses/questions, not legal decisions.

Live checkpoint forks, arbitrary Python execution, ERP/CRM, advanced graph layouts, PDF export and numerical feasibility scoring are not implemented here.

## Recorded verification (27 October 2026)

- Frontend unit tests: 54 passed with two workers, including private-cache isolation on login/logout. ESLint and the production TypeScript/Vite build also passed.
- Backend: 152 passed, 2 skipped (isolated OASIS environment absent locally; Windows symlink privilege unavailable).
- Business browser workflow: passed against real FastAPI/PostgreSQL with the explicitly labeled fixture engine, including a frozen baseline and 2,000-to-3,000 unit break-even comparison.
- Alembic schema check: no drift. Python compilation and Compose configuration validation passed.
- Frontend finish review: **ship** after the following material fixes. Live OASIS/BPS effectiveness remains outside this verdict.

| Review finding | Verdict |
| --- | --- |
| Product brief describes policy instead of PAKAR | Resolved |
| Scenario comparison lacks reviewable context/findings | Resolved |
| Graph lacks causal-event inspection | Resolved |
| Miniature mobile graph lacks accessible controls | Resolved |
| Persona approval omits profile attributes | Resolved |

The inherited UI system and PAKAR extension are recorded in `frontend/DESIGN.md` and its surface brief. The one detector pass found 48 advisory palette/type-ramp items and no non-advisory items.

## OpenRouter connectivity check (28 October 2026)

Local credentials were moved from the example file to ignored `backend/.env`; the example key is empty and the endpoint is `https://openrouter.ai/api/v1`. No tracked file contains the configured key.

A small `openrouter/free` request authenticated successfully and reported cost 0, but selected `nvidia/nemotron-3.5-content-safety:free` and failed the application's JSON response contract. Separate small checks of `google/gemma-4-26b-a4b-it:free` and `liquid/lfm-2.5-2.6b:free` returned HTTP 429. No paid fallback was used; the configured model remains `openrouter/free`.

This verifies credentials/connectivity only. The isolated local OASIS Python environment is still absent, and a complete live simulation has not been verified. Do not interpret the free-router connectivity result as model compatibility or simulation readiness.

## Paid Nemo adapter check (28 October 2026)

The user selected `mistralai/mistral-nemo`; this selection was copied from the example file into ignored `backend/.env`. Two bounded live calls through the actual `BusinessLLM` adapter passed, with automatic retries disabled:

- Exact JSON connectivity response: passed, 91 tokens, 2.53 seconds.
- Synthetic coffee-shop stakeholder discovery: passed the application's persona schema and returned six unreviewed candidates, 2,124 tokens, 58.79 seconds. This checks integration/schema compatibility; relevance and completeness still require human review.

OpenRouter reported a combined cost of **USD 0.000064668** for these two calls. This is measured adapter-test usage, not a price estimate for a complete simulation. No project or user document was sent. The isolated OASIS runtime remains absent and the complete live simulation release gate remains open.

## Local OASIS startup check (28 October 2026)

After the user installed the isolated runtime, imports of OASIS and CAMEL passed under Python 3.12.16 with `camel-oasis==0.2.5` and `camel-ai==0.2.78`. The backend selects that isolated interpreter.

The old backend was stopped and restarted with the ignored local configuration: PostgreSQL at `127.0.0.1:55432`, `mistralai/mistral-nemo`, OASIS enabled, default simulation engine `oasis`, and embedded worker enabled. Using the explicit IPv4 address avoids a stalled localhost/IPv6 PostgreSQL handshake on this machine. `/health` and `/ready` returned HTTP 200; readiness reported schema revision `0015_pakar_business` and local storage. This startup check did not make LLM calls or verify a complete live simulation.

## Response-contract hardening (29 October 2026)

The previous live two-persona/two-round Nemo baseline reached report generation with status **partial**: one accepted interaction, three rejected actions, and four specialist responses that did not pass the finding validator. A separate prompt check produced two valid offers and two rejected responses. These results establish connectivity and execution, not acceptable live model quality. The observed key-usage delta for the baseline was USD 0.000119151; this is an account observation, not complete per-call billing instrumentation.

The follow-up implementation adds opt-in `LLM_STRUCTURED_OUTPUTS=true`. Each turn's JSON Schema restricts actor, target, state version and visible parent IDs; specialist schemas restrict reference IDs, author and `NEEDS_VALIDATION` status and bound output to two findings. Server validation still applies. Schema size contributes to token reservation, response mode is frozen with the analysis snapshot and inherited by scenarios, and rejected actions force partial status with an explicit limitation. Specialist cost is recorded when supplied by the provider; unavailable runtime billing stays unknown. API and worker Compose services expose the same flag.

The OpenRouter adapter requires an endpoint supporting the requested parameters and keeps the selected model. Provider support is endpoint-specific and does not replace server checks: [official structured-output documentation](https://openrouter.ai/docs/guides/features/structured-outputs).

The bridge now uses UTF-8 explicitly for stdin/stdout JSON on Windows and disables SDK retries. A regression test executes the **installed OASIS/CAMEL runtime and actual SDK** against a local scripted HTTP provider: two rounds produce four valid offer/accept interactions with per-turn schemas, state changes and causal references. This test spends no OpenRouter credit and is not a live-model evaluation.

The next real OpenRouter preflight returned **HTTP 401, API key expired**. No new successful live inference was made after the schema changes. Replace `LLM_API_KEY` in ignored `backend/.env`, then restart the backend/worker before the next bounded live baseline and scenario checks. Subsequent release gates remain live BPS indicator validation, independently reviewed business cases/ablations, and recovery/retention validation.

Verification for this checkpoint: full backend suite **162 passed, 2 skipped**; after the final rejection-diagnostic/UTF-8 changes, the affected API and bridge suites **32 passed, 1 skipped**. Python compilation, Compose validation and diff checks passed. The restarted backend returned HTTP 200 from `/health` and `/ready` with schema `0015_pakar_business`. No nonignored repository file contains the configured key; the example key remains empty.

## Live baseline and scenario verified (29 October 2026)

The user replaced the expired key in ignored `backend/.env`. A bounded Nemo JSON Schema preflight passed (provider-reported cost USD 0.000004986), and the backend was restarted with the replacement credentials. A subsequent partial run exposed a role-invalid operator proposal, so turn schemas now also restrict available action kinds by role. The server reducer remains authoritative.

For the explicitly selected `match_price` policy, the operator must apply the scenario comparator price when it differs from its own price. The schema retains the exact decimal amount. This is a controlled user-selected response strategy, not an emergent behavioral prediction. Observe mode does not prescribe a price adjustment.

| Check | Baseline | Competitor-price scenario |
| --- | --- | --- |
| Analysis | `analysis_c59c9cc09f574b4e9c18` | `analysis_2fe0718f62f344ef9c53` |
| Model / response mode | `mistralai/mistral-nemo` / `json_schema` | Same frozen mode/model |
| Personas / rounds | 2 / 2 | 2 / 2 |
| Status | completed | completed |
| Accepted / rejected actions | 4 / 0 | 4 / 0, plus one scheduled shock |
| Specialist reviews completing validation | 4 | 4 |
| Candidate findings | 3 | 4 |
| Conditional contribution margin | IDR 18,000/unit | IDR 12,000/unit |
| Conditional break-even | 2,000 units/month | 3,000 units/month |
| Elapsed time | 171.382 seconds | 310.443 seconds |
| Provider-reported specialist cost | USD 0.000397591 | USD 0.000420792 |

Both runs used real OASIS/CAMEL and live model calls. All published findings passed reference validation and remain `NEEDS_VALIDATION`. The scenario used a separate runtime namespace, injected a 20% competitor price reduction at round 2, and applied the selected matching-price policy. The baseline result digest remained unchanged. Demand and profit remain unknown; external BPS evidence was unavailable.

At the final check, cumulative usage recorded against the replacement key was **USD 0.001543111**, including preflight, the earlier partial run and both completed runs. This is a time-of-check account reading that can settle after individual responses, not an exact runtime per-call breakdown. Specialist costs above come directly from response usage; runtime per-call billing remains unavailable.

The scenario's measured 310.443 seconds exceeds its configured 300-second budget: synchronous provider timeouts do not yet guarantee a strict total wall-clock deadline. This remains a release gate, alongside broader live cases, BPS source validation and independent benchmarking. No claim of business feasibility or multi-agent superiority follows from this smoke test.

Affected business/API/runtime regression suites: **28 passed** after these final changes. Generated exports, run JSON, comparison and verification metadata are in ignored `backend/data/runtime-audit/` (`live-smoke-report.html`, `live-scenario-report.html`, `live-scenario-comparison.json`, `live-integration-verification.json`). Authentication credentials in that directory are local test artifacts and must not be published.

## Final report aligned with PRD (29 October 2026)

The analysis workspace now opens **Laporan akhir** by default. It presents all eight sections in PRD v1.0 §5.6, supported by the v1.1 interaction/scenario trail. Findings are prioritized by severity with affected source excerpts, evidence/gaps, causal ancestors, uncertainty, an explicit unknown impact when it cannot be estimated, and proposed validation actions with named owners. Disagreements are retained verbatim; an empty disagreement registry does not imply consensus. No voting verdict or numerical feasibility score is introduced.

`GET /api/v1/business/analyses/{id}/report` is owner-authenticated and synthesizes the view from frozen inputs and saved results. Existing reports can be read in the new format without new model calls or database rewrites. New jobs retain only a compact manifest in the polling response; the report endpoint expands the appendices on demand. Scenario reports resolve the authorized baseline and show before/after/delta metrics, stakeholder-state changes and new findings.

HTML downloads now contain readable narrative, source quotes, tables, interaction/relationship and calculation trails, provenance and print styles instead of raw JSON sections. User text is escaped and unsafe URL schemes are not linked. App and export preserve unknown profit, unavailable evidence and conditional numbers. Metric tables support labeled keyboard scrolling and visible mobile instructions.

Verification: full backend **165 passed, 2 skipped**; full frontend **57 passed**. After final scoped accessibility/manifest edits, affected report/API tests **11 passed**, report component tests **3 passed**, ESLint and production build passed. The real-API/PostgreSQL fixture browser test passed all eight sections, source-event navigation, 2,000-to-3,000 conditional comparison, mobile viewport containment, keyboard horizontal scrolling and rendered export. No added paid inference was used for this work.

Existing live baseline/scenario `analysis_c59c9cc09f574b4e9c18` / `analysis_2fe0718f62f344ef9c53` were re-exported as report v2. Each has eight sections; the scenario includes the 2,000 → 3,000 unit/month comparison. Saved-result digests remained unchanged. Exports are `backend/data/runtime-audit/pakar-report-baseline.html` and `pakar-report-scenario.html`; projection verification is in `report-implementation-verification.json`.

Finish-review disposition: **ship**.

| Material finding | Verdict |
| --- | --- |
| Hidden mobile Delta column needs visible scrolling instruction and keyboard access in app/export | Resolved |

The single detector run found six advisory type-ramp items and no non-advisory findings; sizes were aligned with existing steps. The reviewer inspected refreshed desktop/mobile app and rendered-export captures. The documenter recorded the report extension in the frontend design/surface records. Existing BPS, strict runtime-deadline and independent-evaluation release gates remain open.

## BPS credential and live adapter check (29 October 2026)

The user supplied `BPS_API_KEY` in ignored `backend/.env`. The official province-domain endpoint returned HTTP 200 / `status=OK`. Catalog discovery followed the [official OpenAPI reference](https://webapi.bps.go.id/documentation/openapi.yaml); credentials were never passed to browsing tools or included in persisted public URLs.

The indicator catalog was initially empty. One bounded national test entry was configured locally from returned catalog metadata: region **Indonesia**, domain `0000`, variable `1975` (Jumlah Penduduk Pertengahan Tahun), period id `126` / label **2026**, unit **Ribu Jiwa**. The period id was read from the API rather than inferred from the year. The former household series inspected during discovery had an old latest period and was not configured.

The actual `BPSEvidence.retrieve("Indonesia")` adapter returned **PARTIAL** with one official observation and a source checksum. Eight live assertions passed: nonempty observations, matching period, variable/unit metadata, national dimension label, cache hit, no national-data fallback for the unmapped city Bandung, no credential in the returned evidence, and no automatic promotion to VERIFIED. Raw values/dimensions are retained without scaling or treating population as customer demand. The raw population value and its declared unit still need numeric-scale/interpretation review; metadata agreement alone is not statistical verification.

Only the exact national region is currently curated. Bandung and Jakarta are not silently mapped to national data or a guessed administrative level. Their real domain, indicator, period and units must be selected separately. Existing frozen reports retain their original evidence snapshots; this configuration applies to future matching live analyses.

The backend was restarted after confirming zero active jobs. This check used no LLM inference. Sanitized local proof is in `backend/data/runtime-audit/bps-live-verification.json` and `bps-evidence-live.json`; the configured key remains only in ignored local configuration.


## Execution on 30 October 2026: DKI evidence, budgets and four-persona live demo

See [execution results](PAKAR_EXECUTION_RESULTS_2026-10-30.md) for scope, evidence, costs and limitations. A curated DKI Jakarta series (domain 3100, variable 144, period 124 / 2024) now supports explicit dimension selection, raw-unit checks and historical freshness. Evidence remains PARTIAL; publication reconciliation and business applicability are open.

One attempt-wide deadline covers BPS, runtime startup and specialists. External waits have kill/reap boundaries; business-stream no longer receives an extra 30 seconds. Cancellation and lease loss stop dispatch/waits, and new live jobs do not automatically retry. Per-call usage, partial billing coverage and optional OpenRouter routing price ceilings are implemented. Default tests isolate developer credentials.

Nemo baseline `analysis_1c5e5c6f273d4080b9c2` completed with four personas / two rounds, eight accepted / zero rejected actions, four specialist reviews and six candidate findings in 280.173 seconds. Scenario `analysis_41fb945dd53f45008365` was partial at 298.011 seconds: eight accepted / zero rejected actions and three of four specialists completed; Risk Agent hit the remaining deadline. Both stayed below 300 seconds. The final tighter 60-second specialist process ceiling was locally tested without another paid run. Baseline remained unchanged.

An accepted synthetic supplier offer changed variable cost from IDR 12,000 to 15,000. Conditional break-even was 2,400 units/month in baseline and 4,000 under the explicitly selected 20% matching-price strategy. These differ from the fixed fixture's 2,000 / 3,000 results. Demand/profit remain unknown. Both reports retain eight PRD sections; all findings require validation.

Latest observed session key-usage delta: USD 0.001775575, including USD 0.000161095 from old tests that inherited developer configuration before isolation was fixed. This is a time-of-check reading; the interrupted Risk attempt has unknown exact per-call cost. The USD 0.02 session budget was not increased. No credentials were persisted with audit proof.

Verification: full backend 184 passed / 2 skipped; final structured/budget guards 17 passed; frontend 65 passed; build/lint passed; real-API/PostgreSQL four-persona fixture browser passed, and live desktop/mobile browser passed. Three synthetic cases/rubric remain drafts, not independently reviewed ground truth. Broader live cases, ablations, publication reconciliation and operational recovery/retention validation remain release gates.

## Follow-up on 30 October 2026: completed reviewers, conflicting BPS and immutable publication checks

The [follow-up plan](PAKAR_FOLLOWUP_PLAN_2026-10-30.md) was implemented; see
[measured results](PAKAR_FOLLOWUP_RESULTS_2026-10-30.md). New snapshots freeze two
peer-review waves with compact, source-scoped context and time reserved for all
four specialists. Transport defaults to one active request after an inconclusive
parallel-provider trial; parallel mode remains explicit and the failed trial is
retained. There is no automatic paid retry or model change.

New baseline `analysis_c751c17a692640b39a6b` completed in **137.460 seconds** and
scenario `analysis_ab708c6916804bce82d3` in **102.135 seconds**. Both had four
personas / two rounds, 8 accepted / 0 rejected actions and **4/4 specialist
responses including Risk**. Conditional BEP remains 2,400 → 4,000 units/month;
profit and real demand remain unknown. These are execution results, not evidence
of business feasibility or improved analytical accuracy.

The official DKI publication was obtained and its table checked against the API:
2,794,485 vs 2,764,456 Rupiah. New evidence is **CONFLICTING**, `value=null`, with
both numbers and provenance retained. Method/survey-period reconciliation remains
open; historical evidence snapshots are unchanged. Worker-crash tests now stop a
blocked SDK child, exercise lease recovery and reject stale publication. Business
retention/deletion remains a separate documented implementation gap.

A clearly false baseline finding (Rp30,000 below Rp12,000) led to a narrow
deterministic arithmetic guard. Canonical API/report/export hold that finding,
publish 6 of 7 baseline findings (scenario 9 of 9), label referencing disagreement
notes and retain all eight report sections. Raw result hashes remain unchanged.
Publications were regenerated with zero inference. Other semantic correctness
still requires review; a completed run does not validate every claim.

Full backend verification: **217 passed, 2 skipped**. Final affected checks and
browser verification are recorded in the follow-up results. No frontend source
changes were needed; earlier frontend 65 tests/build/lint remain applicable.
Observed cumulative key-usage delta since the original preflight is
**USD 0.004329811**, below the unchanged USD 0.02 ceiling; this is time-of-check
usage, with settlement uncertainty on earlier interrupted/failed requests.

## Local input/output trial preparation (30 October 2026)

The intake example now offers coffee, bakery and vehicle-service proposals with
editable source text and a TXT download. Context/region follows the selected
template; uploaded content follows the edited proposal. A short disclosure
explains claim/persona review, fixture versus live inference, and that live
stakeholder discovery also uses the model.

Three fixture cases plus missing-price and conflicting-price cases exercise the
actual API/PostgreSQL lifecycle. Unknown profit, source locations, eight report
sections, scenario arithmetic and baseline immutability are checked. Five cases
passed; the affected backend suite passed 30 checks. Frontend 65 tests, ESLint and
production build passed. Real-API browser regression report and final editable
input-to-report trial each passed. No paid inference or backend logic changes
were added. The existing large-bundle build warning remains.

See [trial guide](PAKAR_TRIAL_GUIDE.md) for the exact input, expected conditional
outputs and manual assessment questions, and [trial readiness results](PAKAR_TRIAL_READINESS_2026-10-30.md)
for verification. These checks prepare a synthetic user trial; model insight
quality, duplicate findings and usefulness still need human assessment.

## Simplified automatic flow after user feedback (30 October 2026)

The default flow is now **upload → description → start analysis**. The intake
navigates directly to progress/results, without mandatory claim approval or
persona setup. Optional context/engine controls are collapsed. Existing projects
have an automatic-analysis action for reuse of uploaded documents.

The old discovery 500 was an unhandled process-budget timeout. Manual discovery
now returns safe 504/502 errors. Automatic preparation runs in the leased job,
within the same token/deadline budget, with a 25-second discovery boundary and
explicitly labeled contextual fallback. Names are business-role labels; allowed
roles follow document context plus basic operator/customer perspectives. Model
goals remain hypotheses. Sources, human-review state, fencing/idempotency and
scenario identity are preserved. OASIS and the interaction reducer are unchanged.

One automatic live run produced an eight-section report in 127.515 seconds with
zero manual intake-review steps. Status remained **partial**: 7 accepted/1
rejected action, 3/4 specialists, Legal HTTP 429. Its early v2 persona output led
to the final v3 normalization, tested locally without another paid full run.
Historical artifacts were retained. Full backend 230 passed/2 skipped; final
affected suite 33 passed, last quick-analysis checks 9 passed; frontend 65 passed,
build/lint passed; automatic-flow browser 3 passed plus report regression 1 passed.

See [automatic flow results](PAKAR_AUTOMATIC_FLOW_2026-10-30.md) and the
[current trial guide](PAKAR_TRIAL_GUIDE.md). Final observed cumulative usage since
the original preflight: USD 0.005186023, below the unchanged USD 0.02 ceiling,
with time-of-check/partial billing coverage limitations retained.

## Threaded stakeholder swarm (31 October 2026)

The [swarm plan](PAKAR_SWARM_PLAN_2026-10-31.md) is implemented and verified
locally; [results](PAKAR_SWARM_RESULTS_2026-10-31.md) record scope and limits.
New quick runs default to four synthetic customer lenses, up to eight personas
and three rounds. Public/private threads, replies and declared stance histories
extend the existing OASIS/CAMEL business adapter and financial reducer. Legacy
snapshots retain pairwise semantics. Scenarios preserve persona identity and
baseline immutability. The UI/report/export expose discussion and disagreements
without turning consensus into factual evidence.

The saved fixture example has seven personas, sixteen public messages, eleven
customer-to-customer replies and one stance revision after an initial position;
final stances remain conditional/opposed/undecided. Twenty-one actions passed
validation, none were rejected. The eight-section report and conditional 2,000
→ 3,000 break-even scenario are traceable to source/events. Profit remains unknown.
This fixture is programmed behavior, not live model validation or a market survey.

Full backend suite: 243 passed/2 skipped before final guard/finishing changes;
final swarm/API/runtime 15 passed and final swarm/API/quick/report 23 passed.
Installed OASIS/CAMEL + SDK was exercised through a local scripted HTTP provider.
Frontend final 68 passed, build/lint passed. Four browser regressions passed;
the new swarm browser flow passed after fixing tab state across run IDs, including
mobile, replies, stance history, export and scenario identity. One legacy
five-stage integration test now has a 15-second total budget for its intentional
fallback polls, with assertions unchanged. No paid inference was used.

Local review artifacts are in ignored
`backend/data/runtime-audit/2026-10-31/swarm/`, including `demo-report.html`.
The model credit ceiling was not reset. Live swarm argument quality, provider
latency/rate limits, independent evaluation, BPS reconciliation and business
retention remain separate gates; no production-readiness claim is made.

## Runtime timeout recovery (31 October 2026)

A subsequent user live run reached the simulation phase deadline after six
committed interactions. The failure path skipped its reserved review phase.
[Timeout recovery](PAKAR_TIMEOUT_RECOVERY_2026-10-31.md) now replays validated
committed events for a partial report and allows future interrupted runs to use
their remaining original review budget. Historical timeout reports are read-only
projections, explicitly marked as lacking specialist AI review; raw failed
results remain unchanged. The affected run yields six original events and eight
report sections without new model calls. No paid inference was used for this
repair. Live swarm quality and completion time remain unvalidated.

## Specialist continuation (31 October 2026)

The [continuation workflow](PAKAR_SPECIALIST_CONTINUATION_2026-10-31.md) now
supports an explicit four-specialist review of a recovered original discussion,
with immutable source lineage, a separate report and new-call-only accounting.
Cross-key submissions reuse the existing review; model changes and automatic
paid retry remain disallowed. Project edits cannot change the frozen source.

One authorized live continuation dispatched four serial reviewer requests:
Market completed, while Finance, Legal/Compliance and Risk returned HTTP 429.
Its eight-section report remains partial, preserving all six source events and
the unchanged raw original result. The three incomplete reviews remain an
external provider gap. The known new billing subtotal is USD 0.00018918, with
three calls' per-call billing unknown. Observed cumulative session usage at
08:49:08 UTC was USD 0.006806851, under the unchanged USD 0.02 ceiling.

## Completed saved live demo (31 October 2026)

Following the user's explicit authorization to fix, call the model and save a
demo, the [live demo package](PAKAR_LIVE_DEMO_2026-10-31.md) is now completed:
five stakeholders, two rounds, ten valid/zero rejected interactions, four
accepted specialist reviews and eight report sections. Market/Finance are
explicitly inherited from the same frozen discussion; only Legal/Risk were
called in the final continuation. Earlier partial runs remain immutable.

The local Nemo route is pinned to Parasail within unchanged price caps.
Fully reported runtime usage settles token reservations before review;
incomplete usage remains conservative. Reply templates preserve causal IDs
without prescribing opinions. Explicit failed-only continuation preserves
accepted reviewers/findings, with separate new-call billing and no automatic
paid retry. UI labels inherited success and has a paid unfinished-review action.

Run `analysis_be0b0b4f0ccf44889954` is saved for replay in the owning account.
Offline HTML/JSON/events/verification and a checksum-verified ZIP are saved under
ignored `backend/data/demo/`. Offline browser checks make zero network requests;
read/report/export checks enqueue zero jobs. Observed new usage for the task was
USD 0.00378228 at 16:37:36 WIB, with USD 0.187867758 remaining on the key limit.
Known BPS conflicts and unknown volume/profit remain explicitly unresolved.

## Reactive dialogue follow-up (31 October 2026)

The older completed demo establishes technical completion, not dialogue depth:
manual review found seven near duplicates among ten messages. The new
[reactive dialogue implementation and evidence](PAKAR_REACTIVE_SWARM_RESULTS_2026-10-31.md)
adds bounded recipient activation, exact trigger replies, role-specific OASIS
templates, server-bound interaction choices and visible structural limitations.
Historical runs and their reports remain immutable. Four Nemo trials and the
first Qwen trial still fail the human standard for a good debate; they are saved
as partial results rather than substituted with authored speeches.

The user explicitly authorized an additional USD 0.01 for Qwen testing, raising
the cumulative ceiling to USD 0.03. Experiments pin Nebius in their own process;
the main environment model remains unchanged. The final saved Qwen result is
`analysis_aaee63ab18d447ba9594`: eight valid messages, two customer-peer replies,
four accepted specialist reviews (three inherited, one new) and eight report
sections. It remains partial: three near duplicates, incomplete rounds and
semantic issues recorded in the linked results. All Qwen trials cost USD
0.00699490; cumulative session usage settled at USD 0.026226281 with USD
0.172230608 remaining on the key. No inference occurs on reading saved artifacts.
No production-readiness or live-debate-quality claim is made.

## Project chat and idea revisions (31 October 2026)

[Project conversation implementation](PAKAR_PROJECT_CHAT_2026-10-31.md) adds persistent, owner-scoped one-agent turns, supporting-data/idea document labels, immutable user-approved idea versions and explicit new analysis runs. Queue/lease/cancellation and idempotency reuse the existing infrastructure. Local regression and browser fixtures pass; two real Qwen follow-up turns are saved in the owner Pepsodent project. General semantic quality remains unvalidated; no automatic revision or swarm dispatch occurs from chat. Main model settings remain unchanged.


## Paid-run guard and Pepsodent public-brief validation (3 November 2026)

See [execution and limits](PAKAR_SPENDING_AND_LIVE_2026-11-03.md). Persistent, atomic OpenRouter dollar reservations now cover business analysis, discovery and project chat, retaining unknown charges and a configured credit floor. A new 8-persona / 3-round Pepsodent run completed with 27 messages, 10 customer-peer replies, four specialist reviews and eight report sections under public-brief-v1. All 27 actual stakeholder SDK marker audits were clean. Dialogue remains partly repetitive and contains unsupported claims; these results establish integration, not robust debate quality or business approval. Saved reports replay without inference. Total task usage after billing settled: USD 0.020471140; key balance USD 0.120258468. Local defaults use Qwen/DeepInfra, a USD 0.01 new-run cap and USD 0.10 credit reserve. Existing results remain unchanged.

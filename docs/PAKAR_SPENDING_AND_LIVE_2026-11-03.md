# PAKAR: paid-run guard and Pepsodent validation ? 3 November 2026

Scope authorized: validate the latest public/internal information boundary with live Pepsodent discussion, improve participant replies, and add application dollar limits while retaining credit.

## Execution budget

Initial key balance: USD 0.140729608. Total live-test ceiling for this task: USD 0.03, with at least USD 0.10 retained. Each experiment is explicit; there is no automatic paid retry, fallback model, or replacement of old results.

The live provider experiment uses Qwen3 235B Instruct on DeepInfra with explicit maximum prompt/completion prices, USD 0.09/0.55 per million tokens and zero request fee. These are routing ceilings checked against the current official endpoint catalog, not a guaranteed final run price. Main app model configuration is recorded separately from experiments.

## Application guard

`AnalysisInput.max_cost_usd` defaults to USD 0.03; specialist continuation defaults to USD 0.01. The deployment maximum `PAKAR_MAX_RUN_COST_USD` defaults to USD 0.03, and `PAKAR_CREDIT_RESERVE_USD` defaults to USD 0.10. Manual discovery and project-chat turns each reserve at most USD 0.005 under the deployment cap. Request values cannot raise the deployment maximum. Existing UI launches receive these server defaults.

Before paid OpenRouter inference, a bounded subprocess reads credit from the fixed official API. Invalid/missing prices, unknown balance or insufficient headroom block dispatch. A credential digest identifies the shared spend account without storing the API key in the ledger. Migration `0017_provider_spending` creates persistent accounts and reservations; PostgreSQL row locks make admission atomic across concurrent jobs.

The whole run reserves its cap before discovery, simulation or review. Discovery and all specialists share one in-process dollar ledger. Runtime gets a bounded share, preserving review capacity, and measures the real SDK messages before every dispatch. Conservative prompt bounds use UTF-8 bytes plus schema/system overhead and maximum output tokens. The provider receives matching no-fallback price ceilings. This follows the official [provider-routing price-cap contract](https://openrouter.ai/docs/guides/routing/provider-selection#max-price).

Reported costs settle reservations. Missing or failed-call invoices retain an upper bound. Interrupted runtime recovery retains the whole allocated phase cap when trustworthy settlement is unavailable. A dead process leaves the durable reservation held; it is not silently refunded. Successful finalization refunds only the difference between cap and charged/reserved usage. Reusing a spend scope cannot dispatch paid work again. The local available balance also retains past charges so delayed provider billing cannot make spent credit appear available again.

Saved results include `usage.spending`, per-call upper bounds and a visible report limitation describing the dollar cap. Hitting this guard is distinguished from a runtime timeout. Historical reports are not rewritten.

Limits: this guard covers PAKAR business analysis, manual discovery and project chat on OpenRouter. Other applications sharing the same key can spend independently; this is not an account-level provider spending policy. Top-ups and unresolved crashed reservations require explicit reconciliation rather than an automatic speculative refund. Non-OpenRouter local/test adapters bypass remote credit checks. Legacy policy inference is outside this business guard.

## Reply quality and information boundary

New prompt version `pakar-1.10` freezes reasoned-exchange guidance, including a two-sentence/360-character target and explicit caution that missing information is not evidence of absence. Assigned replies address the original argument first, state a personal constraint/tradeoff, and avoid asking the same question back. Unknown facts remain unknown; a product facilitator can offer explicitly conditional design proposals without inventing specifications. Customer-to-customer scheduling remains bounded by the existing agenda.

Every actual external SDK request additionally checks known internal source IDs, long source excerpts and financial-value markers not explicitly present in the public brief. Usage records contain a body digest and clean/match counts, never source marker text. This supplements the allowlist; exact-marker checks are not semantic DLP or proof of response truth. Internal specialist context still includes the original documents.

A structural metric records question-like answers for manual review. Structural reply links alone do not establish a substantive or factually correct answer.

## Verification and saved live result

Full backend regression: 311 passed, 2 environment skips before the final heartbeat/status and fixture adjustments. The final focused suite has 34 passes, covering spending, terminal failure, source boundaries, quick flow and repository behavior. Real installed OASIS/SDK scope/budget tests also passed. Compose validation and ESLint passed. Browser fixture intake/scenario and three disclosure-retry checks pass; the chat fixture cancellation correction passes two consecutive browser runs. Scripted responses skip only requests that Chromium explicitly reports aborted; other interception errors still fail the test. Local fixtures use isolated test credentials and databases. No production deployment or historical-result rewrite is part of this task.

## Operational corrections found during verification

- The first eight-persona live trial committed nine messages, then lost the final publication lease. Its key-usage delta was USD 0.006516390. Its events and failed attempt are retained; it is not presented as a completed run. A replacement-run setup caught a mismatched runner worker identity before any inference (USD 0); that attempt was explicitly cancelled.
- Business analysis/chat heartbeat checks now run at most ten seconds apart. A terminal, owned job failure atomically marks a still-active business analysis failed as well, preserving raw results/events; it cannot remain falsely running after final publication was fenced. A stale or different worker cannot use this path to fail somebody else's job.
- The existing chat browser test intercepted aborted React requests using route.fetch/fulfill. Its passthrough reads now use the isolated API request context; the chat workflow passes again without paid inference or application UI changes.
- The replacement live experiment explicitly reuses the same eight frozen automatic perspectives to compare guidance without repeating discovery. It does not claim a second successful LLM persona-discovery call or human approval of those profiles.

## Saved completed live example

- Analysis: `analysis_e0df3ea75fb04b649832`, owning Pepsodent project `business_75c6d7e057ea4b99b9b0`.
- Model/provider: Qwen3 235B Instruct / DeepInfra; prompt `pakar-1.10`; public-brief policy `public-brief-v1`.
- Eight automatic perspectives, three completed rounds, 27 accepted messages, zero rejected actions, 18 directed reply pairs, seven reciprocal pairs and ten customer-to-customer replies.
- Four specialist reviewers completed and the saved report contains all eight PRD sections. This is technical completion, not business approval or verified clinical/regulatory conclusions.
- Every one of the 27 actual stakeholder SDK calls recorded a clean exact-marker audit with the explicit public brief present. Internal data remained available to specialist review. Exact-marker coverage supplements the server allowlist and cannot prove semantic non-disclosure or prevent model hallucinations.
- One near-duplicate supplier message and one structurally unanswered question remain. Manual reading also found repeated requests for mechanism/evidence and unsupported competitor claims about formula imitation/patents (events 8, 17, 26); the facilitator repeated a regulatory-safety inference (event 20). These assertions are not validated by the simulation. Reply links do not establish substantive answer quality, and repeated conditional agreement is not evidence of market consensus.
- No message in the completed run reaches the 600-character schema cap. Shorter guidance removed the observed clipped-sentence issue from the first trial.

Artifacts: ignored `backend/data/demo/pepsodent-public-2026-11-03-v3/` contains the immutable saved analysis, events, readable `report.html`, report JSON and verification. Read/report/export use saved data and enqueue no jobs. Original Pepsodent analysis/event hashes from 1 November remain unchanged.

The first immediate replacement-run reading was USD 0.011353410; provider billing had not fully settled. The later settled replacement cost is USD 0.013954750, matching its 31 distinct provider generation records (no duplicate billing records). Final settled task delta: USD 0.020471140, below USD 0.03. Final observed key balance: USD 0.120258468. Conservative ledger charges can be greater than observed billing because unknown invoices retain bounds; they are not presented as actual cost.

The local application now defaults to the tested Qwen/DeepInfra route. For the remaining small balance, ignored local configuration caps NEW runs at USD 0.01 with a USD 0.10 credit floor. The completed example had an explicitly authorized USD 0.02 cap. Future smaller-cap runs can be partial; neither a credit increase nor a provider/model fallback happens automatically.

New source: `backend/app/business/spending.py`, `backend/migrations/versions/0017_provider_spending.py`, `backend/tests/test_business_spending.py`. Modified: business contracts/agents/service/conversation/information/discussion/OASIS bridge/call worker/tables, shared repository failure finalization, test isolation/schema/runtime checks, Compose/env examples, and the existing chat browser fixture. No UI redesign or OASIS/CAMEL library change.

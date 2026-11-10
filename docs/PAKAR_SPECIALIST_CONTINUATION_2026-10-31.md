# Specialist continuation after partial swarm recovery

## Scope and execution plan

This completes the outstanding workflow after the user's timeout: preserve the
six committed messages, run the four specialist reviewers without repeating the
debate, save a separate traceable report, and verify the complete path locally.
It does not expand the earlier swarm package into demographic representation,
population prediction, independent business evaluation or large-scale operation.

1. Check the original cumulative USD 0.02 credit ceiling and configured provider
   price limits. Do not reset that ceiling or change the model automatically.
2. Add an explicit owner-scoped specialist-review operation using the frozen
   simulation, persona IDs, input revision and evidence of an eligible original
   partial run. Keep all original records immutable.
3. Store the continuation as a separate leased job/report, with source ID and
   result hash, separate usage accounting, no simulation/discovery/evidence calls,
   and no automatic paid retry. Deduplicate even submissions with different keys.
4. Show the explicit paid action, existing follow-up link, lineage and actual
   reviewer outcomes. Distinguish rate limits, validator rejection and unknown
   failure details. Preserve the existing enterprise UI.
5. Exercise locally, attempt the authorized live review once within the existing
   budget, and record incomplete provider outcomes honestly.

Steps above are implemented. The live attempt is finished; **three specialist
reviews remain incomplete because the provider returned HTTP 429**. No further
paid attempts have been made to obtain a successful status.

## API and data behavior

`POST /api/v1/business/analyses/{id}/specialist-review` requires authentication,
an `Idempotency-Key`, and a bounded body (defaults: 100,000 tokens, 300 seconds,
one concurrent request). It only accepts an original partial OASIS run with
saved interactions and no earlier specialist call. It rejects another owner's
run, a scenario, a continuation, changed model or incompatible duplicate limits.

The existing JSON snapshot holds `review_source`: source analysis ID, original
raw-result SHA-256, simulation and evidence. The project lock serializes
submissions. A second key for the same source and limits returns the existing
continuation, including a failed one; reading, refreshing or exporting never
restarts inference. Newer project edits cannot alter these frozen inputs.

No database migration is needed. The new run is labeled as a specialist review,
not a scenario. A subsequent explicit scenario removes the review seed and runs
the actual changed conditions. Reports and exports preserve the eight PRD
sections, source references and incomplete-discussion limitation. New usage only
counts continuation reviewer calls; inherited simulation usage is historical.

## Observed live result

Source: `analysis_c52e1c736c9c4356a0b7`.
Continuation: `analysis_d3efde2bfdcd4e52b86e`.

| Reviewer | Outcome |
| --- | --- |
| Market | Model response completed; 6,306 tokens reported |
| Finance | HTTP 429, `rate_limit` |
| Legal/Compliance | HTTP 429, `rate_limit` |
| Risk | HTTP 429, `rate_limit` |

The attempt took 17.171 seconds. All four requests were dispatched once through
the existing serial two-wave reviewer policy. Rate limits occurred despite
serial requests; this does not identify whether the provider limit concerns
requests, tokens, upstream capacity or another constraint.

The continuation has eight report sections and remains **partial**. Six original
interaction events are unchanged; the raw original result is unchanged. A model
response alone is not a verified market finding, and repeated synthetic opinions
do not become independent evidence. No raw document or message text is copied
into this document or the sanitized verification artifacts.

## Budget evidence

Model remained `mistralai/mistral-nemo`. Existing routing caps remained USD 0.03
per million prompt/completion tokens, zero request charge and no provider
fallback. Before dispatch, observed cumulative usage since the original preflight
was USD 0.006617671. The conservative new allocation was USD 0.003 plus USD 0.001
headroom, within the original USD 0.02 session ceiling.

Only Market returned a per-call cost: **USD 0.00018918**. Three failed calls have
unknown token/cost records; report totals remain partial/unknown. The key-level
check at **2026-10-31 08:49:08 UTC** showed cumulative usage of USD 0.006806851
since the original preflight and remaining key limit around USD 0.191650038.
This is a time-of-check observation, not proof of final billing on every call.

Sanitized local artifacts are in ignored
`backend/data/runtime-audit/2026-10-31/specialist-continuation/`:
`preflight.json`, `dispatch.json`, `verification.json`, `credit-after.json`.
No key, cookie, request credential, source document or raw debate is stored there.

## Verification and remaining limits

Local API tests cover all four reviewer calls, no discovery/runtime/evidence
execution, frozen identity and revision, owner isolation, idempotency across
keys, model/eligibility guards, immutable original results, report/export and
scenario seed removal. The browser test uses a real synthetic fixture project
and mocks the paid continuation route; it does not spend model credit.

- Full backend after implementation: **250 passed, 2 skipped** (252 collected,
  197.094 seconds). The earlier timeout-recovery-only full pass also completed
  successfully with 248 passed/2 skipped.
- Affected API/recovery/report suite: **29 passed**.
- Full frontend: **73 passed** with one worker. The final status-truth refinement
  added one more case; its targeted continuation/status suite is **6 passed**.
- Browser: **1 passed**, covering real synthetic project setup, mocked paid
  submission, immutable-run links, duplicate-button removal, 429 explanations,
  validator/timeout/budget distinctions and mobile page containment.
- Desktop/mobile screenshots inspected. Impeccable finish review: **ship**;
  the one material finding (ambiguous failure cause copy) is **resolved**, with
  no remaining findings. No visual redesign or token changes were introduced.
- Production build and ESLint pass; the pre-existing bundle-size warning remains.
  `git diff --check` passes.

Implementation files: backend business `contracts.py`, `api.py`, `service.py`,
`repository.py`, and new `test_business_specialist_continuation.py`; frontend
business API client, `BusinessAnalysisPage.tsx`, `BusinessPages.tsx`, `Business.css`,
new `SpecialistContinuation.tsx` and `SpecialistReviewStatus.tsx` with unit tests,
and the new specialist-continuation browser test. Documentation/status/trial guide
and the existing surface brief record behavior and verification.

Completing the three live specialist reviews remains dependent on provider
availability/rate limits and a separately authorized paid attempt. Existing
automatic-retry restrictions remain. Independent evaluation, conflicting BPS
publication methodology, scale testing and business-data retention/purge remain
outside this workflow package; no production-readiness claim is made.

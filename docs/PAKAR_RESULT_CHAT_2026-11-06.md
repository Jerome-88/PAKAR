# Follow-up chat from saved results

The analysis page now exposes **Tanya PAKAR** directly beside **Ringkasan**. The
graph remains the default result. Chat previously existed in the project workspace
but its result-page link was buried inside **Status dan detail proses**.

`AnalysisConversation.tsx` loads the authorized project/capabilities and reuses
`ProjectConversation.tsx` in a slim result mode. It fixes the analysis context and
the idea version frozen in that analysis. An analysis without an idea does not
silently inherit the project's latest idea. Follow-up messages shown in this view
belong to this result; backend history retrieval also isolates the selected result.
The project-wide active-turn restriction and paid-action guard remain in force.

Users can ask the facilitator or explicitly select Market, Finance, Legal/Compliance
or Risk. One sent message invokes one selected role, rather than all four agents.
The three starter questions fill the composer only. No model calls run on tab
open, refresh or graph selection. Draft text, selected recipient and ambiguous
request identity survive switching to the graph and back. Saved replies remain
available after navigation/reload. AI reply Markdown/known JSON text envelopes use
the same safe renderer as the result summary.

`conversation.py` supplies bounded, labeled source candidates for the saved
persona stance summary, individual recorded reasons and accepted interactions.
Only explicit stance declarations count; missing data stays unrecorded, saved
final state takes precedence, rejected actions cannot change the count, and
financial actions are not votes. The summary remains in the bounded context so
an omitted excerpt cannot change the denominator. Other excerpts are selected
within the existing 14-source and byte budget. All these sources remain synthetic,
not independent market evidence. Source IDs are validated against the supplied
snapshot. The chat prompt/context version is `project-chat-1.1`.

This work adds no specialist roles and changes no simulation reasoning, public
stakeholder knowledge boundary, saved vote or analysis result. Clarifications do
not silently update ideas. The existing idea workspace remains the explicit place
to review/save a new idea version and launch a separate simulation. Real chat
sends consume provider credit under the existing spending guard.

Files added: `frontend/src/pages/Business/AnalysisConversation.tsx`,
`frontend/tests/e2e/business-result-chat.spec.ts`, and this note.
Files updated: `BusinessAnalysisPage.tsx`, `ProjectConversation.tsx`,
`ProjectConversation.css`, `ProjectConversation.test.tsx`,
`backend/app/business/conversation.py`, `backend/tests/test_business_conversation.py`,
`PRODUCT.md`, and the analysis-page surface brief.

One design detector pass returned no findings. Two bounded screenshot rounds
retained the incumbent Plex, flat neutral surfaces and square blue controls.
Independent finish disposition: **ship**, no material fixes. Final captures are
under `backend/data/runtime-audit/2026-11-06/result-chat/`; mobile composer behavior
was inspected in source and browser tests, not fully visible in the supplied
initial-viewport screenshot.

Final verification:

- 105 frontend unit tests passed across 19 files; ESLint and final TypeScript/Vite
  production build passed. The existing shared-bundle warning remains (~1.19 MB
  before gzip).
- 12 backend conversation tests passed against an isolated `_test` database and
  local provider. They cover selected-result history, immutable saved results,
  stance/missing/rejected-event truth, authorization, single-call dispatch,
  idempotency, lease/cancellation and reference validation.
- Four read-only/scripted browser workflows passed: result chat and three graph
  regressions (including mobile and 120 personas). The chat test checks preserved
  draft/request key across graph navigation, explicit retry after a scripted 503,
  frozen idea version, single named recipient, citations, reload and absence of
  automatic simulation or other writes.
- Three authenticated local API/PostgreSQL browser workflows passed: existing
  project chat/versioned ideas, result summary and full report/export/scenario.
- Backend restarted after confirming zero active jobs; readiness returned 200.

No paid model calls were made to implement or test this change; local/scripted
providers test the interaction boundaries, not live answer quality.

# Result presentation refinement — 7 November 2026

Scope: polish the existing saved-analysis view after a real Pepsodent follow-up
test, preserving the IBM Plex/Carbon identity and the graph-first workflow.

## Changes

- `BusinessOverview.css`: align tabs, graph and stance counts; white graph canvas,
  neutral selected-person panel, clearer typography, responsive summary columns.
- `BusinessExecutiveSummary.tsx`: group the saved verdict and next actions in a
  two-column desktop layout, stacked on tablet/mobile. Keep three initial findings,
  expansion, full reasons and existing source-selection rules.
- `ConversationAnswer.tsx` and `citationReferences.ts`: display explicit resolvable
  `(sumber: ...)` references as numbered controls. Opening one reveals and focuses
  its saved quotation. Unknown or ambiguous references retain the original text.
- `BusinessText.tsx`: allow scoped Markdown renderers while retaining HTML/image
  safety behavior. `ProjectConversation.tsx` reuses the new answer renderer.
- `ProjectConversation.css`: improve reading width, spacing, source controls and
  composer layout without adding decorations or changing provider actions.
- `ConversationAnswer.test.tsx`, `ProjectConversation.test.tsx` and
  `business-result-graph.spec.ts`: verify citation integrity/focus and the preserved
  result workflow. The summary scroll test permits the document-bottom clamp while
  still requiring a visible heading and focused section.

No backend, simulation, reasoning, model configuration or stored result changes.
No new inference was requested during this refinement.

## Evidence

`backend/data/runtime-audit/2026-11-07/result-polish/verification.json` records an
authenticated check against the actual saved analysis, with no API interception.
The temporary owner session is passed through stdin and deleted afterward.

- Actual API HTTP 200; eight graph personas and unchanged frozen input/result.
- Desktop 1440px, tablet 900px and mobile 390px: no horizontal overflow.
- Executive Summary link/focus and four-finding expansion work.
- The saved live follow-up appears in chat; source selection opens the matching
  quotation and classification. An unsent draft survives result-tab changes.
- Zero application writes, additional paid calls or browser page errors.

Corresponding graph, summary, chat, citation and composer screenshots are in that
directory. One mechanical detector scan found five advisory occurrences, limited
to local compact heading/count sizes and previously documented semantic colors.
These are local presentation choices; global design tokens were not changed.

The prior paid chat test is recorded in
`backend/data/runtime-audit/2026-11-06/live-ai-followup/verification.json`: one
completed Qwen3 235B call through DeepInfra, 3,740 tokens, provider-reported cost
$0.00055556, approximately 46 seconds, five citations, saved after reload. This
was a follow-up chat, not a rerun of the swarm. Its answer summarizes concerns but
does not fully satisfy the requested separation of the added nozzle hypothesis
and next-step recommendations. This UI refinement preserves that original answer.

## Final validation

- 108 frontend unit tests across 20 files passed, including two citation-integrity
  regressions; the legacy simulation fixtures still emit existing MSW warnings.
- All four Playwright workflows passed: count filters/keyboard/Back, 120 nodes,
  saved Pepsodent summary/deep links, and saved-result chat/draft/retry behavior.
- ESLint and TypeScript/Vite production build passed. The existing shared bundle
  size warning remains (approximately 1.16 MB before gzip).
- Frontend port 5173 and backend `/ready` on port 5001 both returned HTTP 200.
- Independent five-section Impeccable finish review: **SHIP**, no material findings.
  No additional browser or detector pass was required by the reviewer.

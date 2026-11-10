# Graph as the primary result

The default analysis summary now shows compact stance counts and an interactive
persona graph. Selecting an avatar or the accessible persona selector opens its
recorded stance and reason. The interpretation and three priority checks follow
the graph. The full discussion, report, HTML export and advanced interaction graph
remain available through their existing navigation.

The same `responseSummary` projection drives counts, filters and node membership.
Each active persona counts once; missing stance remains separate from undecided
or opposition. Local DiceBear portraits keep the existing stable persona IDs.
Recorded direct targets and explicit reply references supply edges. Broadcasts do
not create all-to-all edges, rejected actions do not create edges, and proposed
profile relationships are not shown as recorded discussions. Reciprocal messages
share one undirected line; it indicates interaction, not agreement or influence.

Small desktop groups use a circular arrangement. Narrow screens and larger groups
use a readable grid with internal scrolling; selection brings a dense node into
view without scrolling the result page. Graph selection supports Enter/Space and
the native selector. Longer reasons retain the existing safe Markdown disclosure.
The existing detailed interaction graph remains unchanged.

This change reads saved results. It changes no input, reasoning, orchestration,
simulation result, stance, billing or report export. No new inference is required.
Repeated identical limitations are deduplicated in the rendered disclosure only;
the saved limitations remain unchanged.

The inherited IBM Plex, flat neutral surfaces and square blue controls remain.
Two local semantic marker shades (`#198038`, `#8e6a00`) are intentional detector
exceptions for visible small stance markers on neutral backgrounds; they do not
change the global design system. The one detector pass is saved under
`backend/data/runtime-audit/2026-11-06/graph-results/detector.json`.

Verification:

- Full frontend suite: 102 tests passed before the final measurement regression
  was added. Final focused summary/graph suite: 10 tests passed, including that
  regression. ESLint and final TypeScript/Vite build passed. The existing shared
  bundle-size warning remains (about 1.18 MB JavaScript before gzip).
- Three read-only browser checks passed: mixed stance counts and keyboard
  selection, mobile graph visibility and no page overflow, 120-persona scrolling,
  and the saved Pepsodent result (eight undecided, four in the customer subset).
- Two authenticated browser workflows against local PostgreSQL/API passed:
  summary filters/full-report access; eight report sections, evidence/export,
  scenario comparison and legacy graph/avatar identity, including 120 nodes.
- Health/readiness and frontend-to-backend proxy returned HTTP 200. Local
  PostgreSQL, backend port 5001 and frontend port 5173 were started for preview.
- No paid model calls were made. The API workflows used the labeled fixture
  engine. Saved Pepsodent screenshots replay its existing JSON; they do not
  establish a new live inference run or improve its semantic discussion quality.

Independent finish disposition: **Accept**.

| Original finding | Status | Evidence |
|---|---|---|
| Graph prominence | Resolved | Final real-data captures place the canvas around y523 desktop/y582 mobile. Larger fixture captures pass desktop <600/mobile <700 checks. |
| Scope-label cascade and surplus spacing | Resolved | Explicit scoped row direction; compact navigation and filter spacing. |
| Empty-to-populated measurement | Resolved | Measurement observes the stage when personas appear; regression passes. |

Files added: `BusinessResultGraph.tsx`, `business-result-graph.spec.ts`, and this
note. Files updated in this task: `BusinessOverview.tsx`, `BusinessOverview.css`,
`BusinessOverview.test.tsx`, `resultSummary.ts`, `BusinessAnalysisPage.tsx`,
`business-overview.spec.ts`, `PRODUCT.md`, and the analysis-page surface brief.
The wider working tree contains prior uncommitted development.

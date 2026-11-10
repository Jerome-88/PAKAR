---
version: 2
slug: "src-pages-business-businessdemopage-tsx"
primary_target: "src/pages/Business/BusinessDemoPage.tsx"
related_targets: ["src/pages/Business/BusinessHomePage.tsx", "src/pages/Business/BusinessPages.tsx", "src/pages/Business/ProjectConversation.tsx", "src/pages/Business/BusinessResultTabs.tsx", "src/pages/Business/BusinessOverview.tsx", "src/pages/Business/BusinessResultGraph.tsx", "src/pages/Business/resultNetwork.ts", "src/pages/Business/SwarmDiscussion.tsx", "src/config/publicDemo.ts", "src/App.tsx"]
---

# PAKAR public recorded-run demo

Mode: **Operate**. Visitors use the main app's homepage, intake, idea workspace
and result composition with the saved Pepsodent example. Extend the incumbent
IBM Plex, flat white/neutral, square-control and blue-action system. Root
`PRODUCT.md` owns product truth; frontend `DESIGN.md` remains visual authority.
No global tokens change.

## Flow and content truth

`BusinessDemoPage` composes `BusinessHomePage`, `BusinessIntakePage` through
`savedDemo`, `SavedProjectConversation`, shared `BusinessResultTabs`,
`BusinessOverview` and `SwarmDiscussion`. The dedicated replay page and stylesheet
were removed. Locked intake shows the actual frozen idea and public brief;
internal documents are not published and upload is unavailable. The primary
intake action opens saved results; the workspace action opens the saved idea and
four actual specialist review bodies. Result tabs match the main app:
**Ringkasan**, **Diskusi**, **Tanya PAKAR**. Saved reviews are labeled as such and
new-message controls are disabled; this is not a fabricated chat history.

Source `analysis_0c966db47157420b932f` is archived under
`../backend/data/demo/pepsodent-groq-10p-2r-2026-11-08/`. Its 22 events, persona
IDs and final stances match original frozen simulation
`analysis_e50d61963e794cfaac38`: ten personas, two rounds, seven conditional, one
opposed and two undecided. Market/Finance reviews are inherited; Legal/Compliance
and Risk completed through review continuations. No discussion was regenerated.
Four completed reviews do not remove partial discussion quality: six very similar
messages and one unanswered question. Keep the visible repetition/validation
warning. Synthetic responses are hypotheses, not consumer research or market
decisions. V2 preserves source and counts without new AI calls.

## Routes, states and interactions

The isolated `VITE_PUBLIC_DEMO_ONLY=true` build opens the shared homepage at `/`;
**Analisis ide sendiri** remains visible but unavailable. Public query views are
`?view=home|intake|workspace|result`, with result `tab=summary|swarm|chat`.
Navigation, reload and browser history preserve these surfaces. Normal
`/business/demo` opens saved intake, while normal live intake and chat remain
available. Both demo variants read the public JSON. Loading, error and explicit
retry states remain available. Public interactions start no API requests, writes,
uploads or AI calls; auth bootstrap is skipped.

Ringkasan uses the same D3 network as normal results. Circular stable portraits
carry name, role and stance; actual recorded direct interactions/replies supply
the edges. Users drag nodes, pan the canvas, zoom by wheel or buttons, fit the
network and reset positions. Graph node Enter/Space and the native selector open
the recorded reason. Arrow keys pan the focused stage; Home fits it. Selection
recenters an offscreen persona. Stance/customer filters retain their normal
semantics. No line implies a proposed or inferred relationship.

The ten-person demo initially fits the whole network on desktop and mobile;
users zoom and pan for closer inspection. The graph retains a bounded 480px stage; its white inspection panel sits alongside
at desktop and below at 1000px and narrower. Mobile retains the interactive graph,
selector and detail. Compact controls wrap with 40px mobile targets; blue focus
outlines and a distinct node focus ring remain visible. Executive Summary is
directly below the graph, reached by its visible link. These are surface patterns,
not new global palette, radius or typography tokens.

## Verification and disposition

Supplied final v2 checks: 112 frontend unit tests, nine normal browser cases
(eight from the broad run plus the corrected focused pan case), one isolated
public workflow, lint and both builds passed. Coverage includes shared surfaces,
three tabs, the saved idea and four review bodies, graph selection/drag/pan/zoom/
fit/reset, recorded-edge semantics, mobile containment and no public API requests.
The existing shared bundle warning (about 1.16 MB) remains.

The retained detector report has nine advisory type/palette findings in Home and
Overview, with no failures. Do not expand global ramps to make them disappear.
Final reviewer-fix captures are
`../backend/data/runtime-audit/2026-11-08/public-demo-v2/review-fix/public-result-desktop.png`
and `public-result-mobile.png`. Documentation inspected source and retained
evidence without browser, detector, test or model execution.

V2 is published at `https://pakar-demo-pepsodent.khakibowl1.chatgpt.site`, confirmed
by native Sites success with the existing PUBLIC audience. Exact deployment
identity is in `../deploy/public-demo.json`. All 44 build assets matched the
verified frontend copy. Final reviewer disposition: **ship**; mobile framing and
stale documentation were resolved, and all ten avatars fit on initial mobile view.
Covered behavior does not establish general live quality, external factual
validity, market feasibility or production readiness.

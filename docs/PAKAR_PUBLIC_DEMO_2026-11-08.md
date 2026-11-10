# Recorded Pepsodent public demo - 2026-11-08

Publication status: shared-app/network v2 **succeeded**, confirmed by native
Sites deployment with the existing PUBLIC audience at
https://pakar-demo-pepsodent.khakibowl1.chatgpt.site.
`deploy/public-demo.json` records the exact source, version and deployment IDs.

The demo reuses the main app homepage, intake, idea workspace and result surfaces.
The isolated public root opens the shared homepage; **Coba demo** opens the locked
Pepsodent intake. **Mulai analisis** opens saved results, and **Buka ruang ide
dahulu** opens the saved idea workspace. Results use the same **Ringkasan**,
**Diskusi** and **Tanya PAKAR** tabs as the main app. The workspace and Tanya PAKAR
show the actual frozen idea and four saved specialist reviews, labeled as reviews
from the recorded run; they are not a newly generated conversation. New-message
controls are disabled. Source fields remain locked and documents cannot be
uploaded. The main app retains live intake and chat.

Ringkasan reuses the main app's D3 network: circular portrait nodes, node dragging,
canvas panning, wheel/button zoom, fit and reset. Selecting a persona exposes its
recorded stance and reason; the native selector provides the same inspection.
The ten-person demo starts with the whole network fitted on desktop and mobile;
users zoom and pan to inspect it. Edges represent actual recorded direct
interactions or replies only. Executive
Summary sits directly below the graph. Stance and customer filters keep their
existing saved-result semantics. No demo interaction makes a new AI call or
backend API request.

## Source and limits

The source archive is
`backend/data/demo/pepsodent-groq-10p-2r-2026-11-08/`, containing `analysis.json`,
`report.json`, `report.html` and `verification.json`. Final analysis
`analysis_0c966db47157420b932f` preserves the 22 events, persona IDs and final
stances of original simulation `analysis_e50d61963e794cfaac38`: ten personas,
two rounds, seven conditional, one opposed and two undecided. Market/Finance
reviews are inherited; Legal/Compliance and Risk completed in new review
continuations. No persona discussion was regenerated for those continuations.
The v2 interface does not change this source or these counts.

The run used real Groq calls with synthetic case inputs. Discussion quality
remains partial: six messages are very similar and one question is unanswered.
Four completed specialist reviews do not establish complete discussion quality.
The UI discloses repetition and the need for validation. These are simulated
opinions, not consumer research or a market decision.

## Files and build

- `scripts/export-public-demo.py` creates
  `frontend/public/demos/pepsodent.json` from the reviewed archive. It requires
  synthetic classification and public events; internal documents, evidence
  bodies, operational usage and credentials are excluded.
- `BusinessDemoPage.tsx` composes shared `BusinessHomePage`, `BusinessIntakePage`
  through its `savedDemo` prop, `SavedProjectConversation`, `BusinessResultTabs`,
  `BusinessOverview` and `SwarmDiscussion`. The separate `BusinessDemoReplay.tsx`
  and `BusinessDemo.css` were removed.
- `BusinessResultGraph.tsx` and `resultNetwork.ts` implement the shared interactive
  network used by normal and demo results, with recorded edges only.
- `frontend/src/config/publicDemo.ts`, `App.tsx`, auth and shell/brand integration
  isolate public navigation and suppress the `/me` read. **Analisis ide sendiri**
  stays visible but unavailable in the isolated public homepage.
- `frontend/scripts/build-demo.mjs` sets `VITE_PUBLIC_DEMO_ONLY=true` and builds
  `frontend/dist-demo/`. `npm run preview:demo` serves only that static output at
  `http://127.0.0.1:4180/`, accepting GET/HEAD. The normal build remains the full
  app; `/business/demo` opens saved intake.

Public query views are `?view=home|intake|workspace|result`, with result
`tab=summary|swarm|chat`. Query navigation, reload and browser history retain
these surfaces. Loading, error and explicit retry states remain available.

Run `python scripts/export-public-demo.py` from the root to refresh the snapshot;
then in `frontend`, run `npm run build:demo` and `npm run preview:demo`.
The sanitized Sites source copy is `sites/pakar-demo-pepsodent/`, with output
normalized to its canonical `dist/` root. Source commit
`f31ac2c1cd6e24c76b603caba1e6ea02d44fb83b` was pushed and packaged before
publication. All 121 source files, five public files and 44 build assets matched
the tested frontend copy; no configured credential values were found in assets.

## Verification

Supplied final v2 checks passed: 112 frontend unit tests, nine normal browser
cases (eight from the broad run plus the corrected focused pan case), one
isolated public-demo browser workflow, lint, normal build and public build.
Covered behavior includes shared intake/workspace/result navigation, saved idea
and four review bodies, three result tabs, graph selection/drag/pan/zoom/fit/reset,
recorded-edge semantics, mobile containment and no public API requests. The
existing shared bundle warning (about 1.16 MB) remains.

The retained detector report contains nine advisory findings for type/palette
alignment in Home and Overview, with no failures. These findings do not authorize
new global type or color tokens. Retained v2 screenshots are in
`backend/data/runtime-audit/2026-11-08/public-demo-v2/review-fix/`:
`public-result-desktop.png` and `public-result-mobile.png`. Documentation inspected
source and retained evidence without new browser, detector, test or AI execution.
The final public browser rerun additionally verifies all ten avatars fit inside
the initial mobile canvas. Finish reviewer disposition: **ship**, after mobile
framing and stale documentation were corrected. No new AI calls were made.
These checks prove covered saved-demo behavior, not general live analytical
effectiveness or production readiness.

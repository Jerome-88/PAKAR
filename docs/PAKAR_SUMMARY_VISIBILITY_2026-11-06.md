# Executive Summary visibility correction

The user reported the summary missing on the real saved Pepsodent URL. The served
frontend already contained the section, but actual authenticated browser checks
placed its heading below the initial viewport: y1051 on a 1440x1000 desktop and
y1480 on a 390x844 phone. Earlier existence/DOM-order checks did not establish
initial-viewport visibility. The legacy interaction graph also lacked the section.

The main graph now exposes **Lihat Executive Summary** above its canvas. The
summary remains below the graph; the link scrolls to and focuses it. A shared
`BusinessExecutiveSummary.tsx` renders the same content under both main and legacy
interaction graphs. `#executive-summary` links scroll/focus after asynchronous
analysis loading, and result tabs follow the URL and browser Back/Forward instead
of retaining stale local tab state.

This extracts the existing summary content and projection without changing saved
findings, positions, filtering, simulation behavior or model calls. The three
primary tabs and sidebar-free business shell remain. The normal pointer/keyboard
target is a native link and the destination has a focus outline and sticky-header
scroll offset.

Real application verification used the existing API and PostgreSQL row, with no
intercepted data response. A 120-second local verification session was conveyed
only through subprocess stdin and deleted afterward. No raw cookie or API key was
printed or stored. The saved input/result were equal before and after; zero API
writes and zero paid inference calls occurred. Both viewport checks place the
heading at y105 after the link completes, and the direct hash link also works.
Evidence: `backend/data/runtime-audit/2026-11-06/summary-visibility/` contains actual
entry/summary captures and `live-verification.json`.

Four browser workflows check the jump link, direct asynchronous hash navigation on
both graph variants, browser Back, count/filter/120-node behavior and existing chat
draft/retry behavior. The one detector pass retains three existing advisories for
the semantic marker colors and mobile header size; no new visual tokens were
introduced. Full frontend verification passed: 106 tests across 19 files, ESLint
and the TypeScript/Vite build (with its existing bundle-size warning). The four
browser workflows passed with the new jump/deep-link/Back assertions. Independent
finish disposition: **ship**, no material fixes.

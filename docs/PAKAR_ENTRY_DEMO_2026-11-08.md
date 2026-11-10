# Public entry and saved Pepsodent demo — 2026-11-08

`/` and `/business` now offer **Coba demo** or **Analisis ide sendiri**.
`/business/demo` shows a backend-independent saved real-AI study on synthetic
inputs: eight personas, 27 messages, all eight undecided. **Ringkasan** and
**Diskusi** inspect the recording without inference, live chat or new AI credits.
`/business/new` retains actual intake and default shared access without login.
Visible business project/run history, including the project run list, is removed;
**Pengaturan analisis** keeps launch settings. Saved records, direct real results,
chat and export remain available.

## Changed files

- New: `frontend/src/pages/Business/BusinessDemoPage.tsx`;
  `frontend/public/demos/pepsodent.json`;
  `scripts/export-public-demo.py`; `frontend/tests/e2e/business-entry.spec.ts`.
- Updated: `frontend/src/App.tsx`, `frontend/src/App.test.tsx`;
  `frontend/src/components/AppShell/AppShell.tsx`,
  `frontend/src/components/Header/Header.tsx`;
  `frontend/src/pages/Business/BusinessHomePage.tsx`, `BusinessHome.css`,
  `BusinessPages.tsx`, `Business.css`,
  `BusinessOverview.tsx`, `BusinessAnalysisPage.tsx`.
- Documentation: `PRODUCT.md`;
  `frontend/.impeccable/surfaces/src-pages-business-businesshomepage-tsx.md`;
  this report. Existing `frontend/DESIGN.md` and design sidecar were not rewritten.

## Snapshot truth

`scripts/export-public-demo.py` exports
`backend/data/demo/pepsodent-public-2026-11-03-v3/analysis.json` to
`frontend/public/demos/pepsodent.json`. Original persona/event/finding IDs,
recorded events and stances, and finding text were verified identical for the
exported fields. The public payload excludes documents, claims, model debug,
billing and internal persona profiles. No source archive or database mutations,
backend changes or new AI calls were made for this task. The recording is
synthetic and does not establish consumer opinion or market acceptance.

## Verification

Full unit suite: **110 passed**; after final test-mock changes, App suite:
**nine passed**. Final Playwright entry + graph + chat selection: **seven passed**.
An initial ambiguous test locator was corrected with an exact match. Lint and
production build passed; the existing approximately 1.155 MB shared-bundle
warning remains.

One detector pass: **seven advisory, zero non-advisory** findings, covering
inherited/local fluid-font, caption, hover and selection values. Screenshot
inspection used at most two rounds. Finish-review disposition: **SHIP**, no
material fixes. Verification covers the exercised frontend behavior and snapshot
fidelity, not live model quality or deployment readiness.

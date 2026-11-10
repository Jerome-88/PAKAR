---
version: 1
slug: "src-pages-business-businesshomepage-tsx"
primary_target: "src/pages/Business/BusinessHomePage.tsx"
related_targets: ["src/pages/Business/BusinessHome.css", "src/pages/Business/BusinessDemoPage.tsx", "src/pages/Business/BusinessPages.tsx", "src/App.tsx"]
---

# PAKAR entry and saved demo

Mode: **Operate**. Help visitors choose between inspecting a saved example and
starting their own analysis. Root `PRODUCT.md` owns product truth; frontend
`DESIGN.md` owns the incumbent visual system. This brief adds no global tokens.

## Routes and flow

- In the full app, `/` and `/business` offer **Coba demo** and **Analisis ide sendiri**.
- `/business/demo` opens **Input contoh → Analisis → Hasil**, preserving the step
  and result tab in query parameters. See the dedicated
  `src-pages-business-businessdemopage-tsx.md` brief for replay/result behavior.
- `/business/new` opens actual intake through the existing protected route. The
  default shared workspace requires no login. Entry alone starts no analysis.
- The separate `VITE_PUBLIC_DEMO_ONLY=true` build opens the demo at `/`, hides
  live intake/account navigation and skips auth-status requests. Normal
  `/business/demo` retains **Analisis ide sendiri**.
- Business project lists and run history remain absent from visible entry.
  Saved records and direct project/result, chat and export flows remain.

## Saved and live boundary

The example packages a real recorded Groq run using synthetic Pepsodent inputs:
ten personas, two rounds, 22 messages; seven conditional, one opposed and two
undecided final positions. Four AI specialist reviews completed. The frozen
discussion and positions are preserved through review continuations.
Repetitive responses keep discussion quality partial and are disclosed.

The demo reads `public/demos/pepsodent.json` without backend result requests,
writes, inference or new AI credits. The full app may read existing auth status;
the isolated public build makes no API request. Internal documents, operational
data and credentials are excluded. The example has no live composer;
**Analisis ide sendiri** leaves it for real intake.

## Incumbent visual rules

Retain IBM Plex Sans, a light entry heading, white/neutral flat surfaces, square
geometry, hairline separation, blue actions and visible keyboard focus. The
first viewport presents both linked choices, side by side on desktop and
stacked on mobile. The actual-analysis choice uses the incumbent blue action
treatment. Local fluid type and interaction values remain surface observations.

## Verification and disposition

Supplied final reviewer disposition: **SHIP**, no material fixes. Supplied final
checks: 110 frontend unit tests, eight normal browser workflows and one isolated
public-demo browser workflow passed; lint and both builds passed. Public proof
recorded zero API requests or writes, 404 for API/environment paths and 405 for
POST on the static server. The existing shared bundle warning remains. One
detector pass returned `[]`; screenshot review stayed within two rounds.

Final result desktop/mobile copies are under
`../backend/data/runtime-audit/2026-11-08/public-demo/public-demo-result-*.png`.
Input/process captures were removed by Playwright cleanup and were source
checked by the reviewer. Documentation inspected source and retained result
copies without another browser or AI run. Publication is tracked separately in
`../docs/PAKAR_PUBLIC_DEMO_2026-11-08.md`; these checks establish covered
saved-demo behavior, not analytical effectiveness or deployment readiness.

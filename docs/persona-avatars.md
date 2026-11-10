# Dynamic persona avatars

PAKAR renders avatar SVGs locally with the official DiceBear JavaScript packages:
`@dicebear/core@10.7.0` and `@dicebear/styles@10.6.0`. The v10 API uses reusable
`Style` instances and `new Avatar(style, options).toDataUri()`. Only the Personas
and Fun Emoji JSON definitions are imported. No avatar service, API key, database
migration, or backend change is required.

## Identity and rendering

`frontend/src/components/PersonaAvatar/avatar.ts` is the single source generator.
An available `persona.id` is the deterministic seed; editable name, role,
revision, selected state, component size, list position, and run ID do not affect
that seed. The same saved persona ID produces the same avatar after reload or
across a baseline and scenario. A newly created persona gets its portrait as soon
as its server-assigned ID is displayed; images do not need to be stored.

Human stakeholders use **Personas**. Analytical and system agents use **Fun
Emoji**, selected explicitly by `kind: "agent"`. Analytical run records currently
expose roles rather than entity IDs, so `agentAvatarId(role)` provides a stable,
case/whitespace-normalized `pakar:agent:` namespace shared by findings, audit
records, and messages. Graph system nodes that have an ID use that ID directly.
Any future explicit agent ID should likewise take precedence over role labels.

For missing IDs, a deterministic, normalized name/role tuple supplies a fallback;
fully anonymous or invalid metadata gets a stable generic identity. Numeric IDs
are accepted when finite. No render-time random number or array index supplies
identity. Older message DTOs without IDs reuse a saved persona ID only when
name/group matching is unambiguous. Duplicate indistinguishable records without
IDs may share a fallback portrait; unique stable IDs remain the identity contract.

The fixed, non-realistic blue/lavender/teal skin palette and restricted component
choices are illustrative. Age, ethnicity, gender, or other demographic traits
are not inferred from names or occupations. Facial hair, infant mouths, and
wrinkle variants are excluded. Role does not select facial characteristics.

Two `Style` instances are shared. A 2,048-entry LRU cache stores SVG data URLs,
keyed by style kind and seed. Cache eviction affects memory only: regeneration
produces the same portrait. All display sizes use one 64px SVG coordinate space;
SVG scales without raster blur. The memoized `PersonaAvatar` component uses a
decorative `<img>` beside the visible name. SVG graphs use the same cached source
in `<image>`. No SVG is injected into HTML. Rendering/decoding errors have a local
generic SVG fallback. Generated SVGs retain DiceBear's license metadata.

**Keep the pinned package versions and generator options stable.** Changing
either can change portraits for existing IDs. Treat such updates as an explicit
avatar-version migration rather than an incidental dependency update.

## Integration boundaries

- Business persona review, graph nodes and inspector, timeline actors, report
  stakeholder appendix, and scenario state changes share persona IDs.
- Findings, disagreements, and specialist audit records share analytical-agent
  identities and Fun Emoji portraits.
- Legacy Persona Studio, environment lists, simulation feed, interaction profile,
  multi-persona selection, interviews, and analytical messages use the same
  helper. Optional `persona_id` in existing event payloads is carried through the
  frontend presentation DTO. Name/group matching is the conservative fallback.
- The existing legacy D3 graph adds portraits only for matching personas or
  explicitly typed person/system nodes. Policy issues and institutional knowledge
  entities retain their existing symbols. Dragging, zoom, selection, connections,
  and force-layout behavior are preserved.
- The business graph retains its circular layout and keyboard interactions.
  Dense graphs have an expanded, scrollable canvas to preserve readable labels;
  initial display and selection center the chosen node before paint. A focus-key
  guard preserves manual panning across unchanged snapshot refreshes. Mobile
  retains the native stakeholder selector and avatar detail panel.

No changes were made to backend persona generation, reasoning, memory,
orchestration, simulation actions, stopping rules, or engine limits. Backend HTML
report exports remain text reports; the frontend report includes avatars.

## Licensing

Personas by [Draftbit](https://personas.draftbit.com/) and Fun Emoji by
[Davis Uche](https://www.figma.com/community/file/968125295144990435) use
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution identifies
the original work, author, license, DiceBear remix, and PAKAR's color/component/
framing adaptations. Each app shell exposes **Kredit ilustrasi avatar**. The
public `frontend/public/avatar-licenses.txt` includes complete notices and the
DiceBear core MIT license and is copied into the production build.

## Validation

- Frontend suite: **65 passed**, including seven identity/cache/fallback/license
  tests and a **120-node** graph test checking cached rendering, keyboard
  selection, detail consistency, connections, and event navigation.
- Real FastAPI/PostgreSQL fixture Playwright report workflow: **1 passed**,
  with desktop/mobile screenshots, successfully decoded local avatars, matching
  identity in persona list/graph/inspector/report/scenario, and no external avatar
  requests. This workflow makes **zero LLM calls**.
  A browser-only intercepted read response additionally exercises 120 nodes,
  proving selected-node visibility initially, after native selection, and after
  keyboard selection, plus mobile detail identity. Engine limits are untouched.
- Local Chromium generator benchmark: **500 unique avatars**, approximately
  **95 ms** cold generation and **1.5 ms** cached retrieval. These are local
  measurements of SVG generation, not a simulation throughput guarantee.
- `npm run lint`: **passed**. `npm run build`: **passed** (TypeScript and Vite).
  Vite retains the existing shared-bundle size advisory.
- One Impeccable detector run: 38 advisory findings in incumbent UI rules
  (18 type-ramp, 20 palette); zero non-advisory findings and none in the new
  shared avatar component. The detector was not repeated.

Independent finish review disposition: **ship** after one material fix batch.

| Recorded finding | Final verdict |
| --- | --- |
| Dense graph initially exposed an empty corner and selection remained offscreen | Resolved: initial display and selection reveal the selected portrait and readable labels. |

No material findings remain. Desktop/mobile proof is in
`frontend/test-results/business-report-PRD-report-f9f11--trails-and-scenario-deltas-chromium/`.

## Files added

- `frontend/src/components/PersonaAvatar/avatar.ts`
- `frontend/src/components/PersonaAvatar/PersonaAvatar.tsx`
- `frontend/src/components/PersonaAvatar/PersonaAvatar.css`
- `frontend/src/components/PersonaAvatar/avatar.test.tsx`
- `frontend/src/pages/Business/BusinessGraph.test.tsx`
- `frontend/public/avatar-licenses.txt`
- `docs/persona-avatars.md`

## Existing files modified for this task

- `frontend/package.json`, `frontend/package-lock.json`
- `frontend/tsconfig.app.json`
- `frontend/src/components/AppShell/AppShell.tsx`
- `frontend/src/pages/Business/BusinessPages.tsx`
- `frontend/src/pages/Business/BusinessGraph.tsx`, `Business.css`
- `frontend/src/pages/Business/BusinessAnalysisPage.tsx`
- `frontend/src/pages/Business/BusinessReport.tsx`
- `frontend/src/pages/PersonaStudio/PersonaStudioPage.tsx`
- `frontend/src/pages/SimulationWorkflow/SimulationWorkflowPage.tsx`
- `frontend/src/pages/SimulationWorkflow/WorkflowComponents.tsx`
- `frontend/src/pages/SimulationWorkflow/SimulationWorkflow.css`
- `frontend/src/pages/SimulationWorkflow/workflowTypes.ts`
- `frontend/src/pages/SimulationWorkflow/backendWorkflow.ts`
- `frontend/src/api/client.ts`
- `frontend/tests/e2e/business-report.spec.ts`
- `frontend/DESIGN.md`, `frontend/.impeccable/design.json`

Design documentation added:

- `frontend/.impeccable/surfaces/src-components-personaavatar-personaavatar-tsx.md`

Design documentation is updated by the independent finish handoff. Unrelated
pre-existing workspace changes are not part of this avatar implementation.

---
version: 1
slug: "src-components-personaavatar-personaavatar-tsx"
primary_target: "src/components/PersonaAvatar/PersonaAvatar.tsx"
related_targets: ["src/components/PersonaAvatar/avatar.ts", "src/components/PersonaAvatar/PersonaAvatar.css", "src/pages/Business/BusinessGraph.tsx", "src/pages/Business/BusinessPages.tsx", "src/pages/Business/BusinessAnalysisPage.tsx", "src/pages/Business/BusinessReport.tsx", "src/components/AppShell/AppShell.tsx", "src/pages/PersonaStudio/PersonaStudioPage.tsx", "src/pages/SimulationWorkflow/SimulationWorkflowPage.tsx", "src/pages/SimulationWorkflow/WorkflowComponents.tsx", "../docs/persona-avatars.md"]
---

# Persona identity across the workspace

Scope: shared avatar presentation across PAKAR and legacy persona workflows. Visitor mode: Operate, with Read report surfaces. Business Analysts use repeated portraits to recognize stakeholders and distinguish analytical agents while inspecting assumptions, interactions and evidence. This is an incumbent extension: the direction contract in `index.html` remains authoritative. No new visual world, composition exploration or FORM draw was required.

Direction: preserve IBM Plex, white/neutral flat surfaces, blue actions and square controls. Circular portraits at 24–40px are localized identity affordances beside visible names. Personas represents human stakeholders; Fun Emoji represents analytical/system agents. Non-realistic blue/teal/lavender skin and restricted friendly variants convey illustration without demographic inference. Names, roles, labels, source provenance and synthetic-hypothesis notices remain readable; portrait differences imply neither evidence nor analytical confidence.

Observed implementation: React 19/Vite uses official `@dicebear/core@10.7.0` and `@dicebear/styles@10.6.0`, importing only local Personas and Fun Emoji JSON definitions through reusable `Style` and `Avatar` APIs. Stable persona IDs seed identity independently of editable metadata. Analytical roles without entity IDs use the normalized `pakar:agent:` namespace; explicit system graph IDs are used directly. Missing IDs fall back to a normalized name/role tuple, then stable anonymous identity. Ambiguous legacy names do not acquire another person's ID. Duplicate records without distinguishable IDs may share a fallback portrait.

Two shared styles, a 2,048-entry LRU and a memoized decorative image component reuse one 64px SVG data URI across list, graph, inspector, report, timeline and scenario views. Graph SVG images use the same source helper. A safe local generic SVG handles generation/decoding failure. Pinned packages and generator options are part of visual identity; change them through an explicit avatar-version migration. AppShell and the legacy workflow expose original-author CC BY 4.0 credits and PAKAR adaptation notices; `public/avatar-licenses.txt` also includes core MIT. The complete integration/file manifest is `../docs/persona-avatars.md` from the frontend root.

Graph behavior: preserve the business graph's circular layout, connections and Enter/Space selection. Dense graphs expand into a scrollable canvas rather than shrinking portraits and labels. Before paint, first display, selection changes and canvas-size changes center the selected node; a focus-key guard preserves manual panning during unchanged snapshot refreshes. Mobile retains the native stakeholder selector and avatar detail. The legacy D3 graph keeps its forces, dragging, zoom and connections; only matching personas or explicitly typed person/system nodes receive portraits. Policy and knowledge symbols remain as implemented.

Boundaries: presentation only. No backend, persona generation, reasoning, memory, orchestration, simulation-action/stopping-rule or engine-limit changes. Exported HTML remains text. Identity/interaction proof does not establish live discovery or simulation quality, BPS applicability, production readiness or business feasibility.

Finish evidence supplied by the implementation and independent review: **SHIP** after one fix batch. The sole material finding was resolved; none remain.

| Finding | Final verdict |
| --- | --- |
| Dense canvas initially opened on an empty corner with the selected node offscreen | Resolved: initial display and selection reveal the selected portrait and readable labels; unchanged snapshot refresh preserves manual panning. |

Verification: frontend **65 passed across 12 files**, including seven identity/cache/fallback/license checks and one 120-node graph check; lint and production TypeScript/Vite build passed. The existing 500k shared-bundle advisory remains. Real FastAPI/PostgreSQL fixture Playwright **1 passed** with local SVG decoding, shared identity across persona list/graph/inspector/report/scenario, zero external avatar requests and zero LLM calls. A browser-only intercepted 120-persona read response confirmed initial selected-node visibility, native p60 selection, keyboard Space p61 selection and mobile identity without changing engine caps. Local generator-only benchmark: 500 unique avatars about 95ms cold and 1.5ms cached; this is not simulation-throughput evidence.

Detector: exactly one run at `../backend/data/runtime-audit/avatar-design-detector.json`, with 38 advisory incumbent items (18 type, 20 palette), zero non-advisory findings and none in the shared avatar component. No second run. This avatar-specific record extends the earlier workspace/report review without replacing it.

Rendered proof under `test-results/business-report-PRD-report-f9f11--trails-and-scenario-deltas-chromium/`: `avatar-persona-desktop.png`, `avatar-persona-mobile.png`, `avatar-graph-desktop.png`, `avatar-graph-mobile.png`, `avatar-dense-initial-desktop.png`, `avatar-dense-selected-desktop.png`, `avatar-dense-mobile.png` and `report-finding-desktop.png`.

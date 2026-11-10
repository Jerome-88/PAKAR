# PAKAR

PAKAR is a business co-analyst for Business Analysts and Strategic Planning teams. It combines stakeholder perspectives, analytical specialists, source evidence, and scenario stress tests to identify blind spots and the next questions to validate.

The application opens at `/` or `/business` with two public choices: **Coba
demo** and **Analisis ide sendiri**. `/business/demo` packages a read-only saved
real-AI Pepsodent study using synthetic inputs: ten personas, two rounds and 22
recorded messages. Final positions are seven conditional, one opposed and two
undecided; four internal AI specialist reviews completed. The demo reuses the
main app homepage, intake, idea workspace and three result tabs: **Ringkasan**,
**Diskusi** and **Tanya PAKAR**. Locked intake fields preserve the original idea
and public brief. The idea workspace and Tanya PAKAR show that idea and four
actual saved specialist reviews, with new-message controls disabled. The shared
interactive graph supports dragging nodes, panning, zooming, fit and reset;
Executive Summary sits directly below it. All demo content reads saved output
without inference, new AI credit use, uploads or backend API requests. Repetitive
messages remain disclosed, so the run retains partial quality status.
`VITE_PUBLIC_DEMO_ONLY=true` builds a static visitor experience whose root opens
the shared homepage; it skips auth bootstrap and disables new analysis. It needs
no backend or provider key. Normal `/business/demo` opens the saved intake.
`/business/new` opens the actual intake through the
existing protected-route mechanism and the **shared workspace without
registration or login**
(`AUTH_REQUIRED=false`, the default). Everyone using the application can read and
edit business projects, saved analyses and conversations. Existing records retain
their original ownership fields; the shared API resolves those fields internally
so saved demo links remain usable without rewriting results. New projects use a
stable internal workspace identity, with no session cookie. Account controls are
absent, and old login/register links open their intended workspace destination.
Optional legacy account mode remains available with `AUTH_REQUIRED=true`.
AI calls remain explicit and retain the existing spending and runtime limits.

Visible business project lists and run history are removed, including the run
list in project settings; that tab is now **Pengaturan analisis**. Underlying
records remain saved, and direct project/result links, real-result chat and HTML
export remain available. The public demo does not expose those live actions.

The product follows `docs/PAKAR_PRD_REVISION_v1.1.md`. The policy product remains available through legacy workflows; its brief is archived in `docs/PAKAR_PRODUCT_LEGACY.md`.

## User workflow

1. Upload PDF, DOCX, TXT or Markdown, enter an analysis name and describe the business decision. Industry, region and target customer are optional additional settings; unspecified values stay unknown.
2. Start analysis directly. A leased background job prepares source-linked assumptions and contextual personas. Profiles are not marked human-reviewed; ambiguous numerical inputs remain unknown. Parsing failures remain visible.
3. Live discovery uses a bounded schema with document-supported business roles and display labels. If it fails, contextual role selection is explicitly labeled as a fallback. Default quick runs use three rounds, four customer perspectives and up to eight personas. Threaded swarm discussion records replies, access boundaries and declared stance changes; older snapshots retain pairwise behavior. Synthetic demo mode makes no model calls.
4. Freeze prepared inputs once, then run bounded analysis. Personas propose interactions; the server validates actions and changes state. Specialists examine assumptions, findings and evidence gaps. Manual source/profile review remains available through project settings, rather than blocking the default workflow.
5. Review blind spots by priority/category. Follow findings to source claims, interaction chains, conditional calculations and validation tasks.
6. Create a separate scenario with a scheduled shock. Compare calculations, stakeholder states and findings against the unchanged baseline.
7. Download an HTML report with assumptions, evidence, findings, disagreements, calculations and limitations.

The business workspace uses a single top header and local page navigation, with no product sidebar, mobile drawer or hamburger. Completed results expose three tabs: **Ringkasan**, **Diskusi** and **Tanya PAKAR**. Ringkasan opens the shared D3 network with circular portrait nodes, node dragging, canvas panning, zoom controls, fit and reset, plus compact counts of active simulation personas supporting, opposing, supporting conditionally or undecided. Select a persona to read its recorded reason beside the graph (below it on mobile); stance and customer-only filters narrow the graph. Lines represent recorded direct interactions or replies, never proposed profile relationships or inferred broadcast conversations. Missing stance data is shown separately, never counted as opposition. Each persona counts once; analytical specialists are outside the denominator. Counts are synthetic positions, not market shares or a business approval score.

**Executive Summary** sits directly below both the main graph and the legacy interaction graph. A visible **Lihat Executive Summary** link above either graph moves to that section; `#executive-summary` also works when analysis data loads asynchronously. Result tabs follow the URL and browser Back/Forward navigation. The summary groups the short stance headline and **Yang masih kurang**: up to three priority findings linked to accepted recorded interactions, each with a short next action and optional full reason. Further discussion-linked findings expand inline. It reads saved results without another model call. Generic assumption-register and missing-input checks do not occupy this short discussion view. No finding is invented when the discussion has no recorded summary. Diskusi retains the actual messages, replies and reasons without quality metrics, dispatch diagnostics or repeated final-position tables. The normal result interface removes assumption registers, full-report navigation, the advanced menu, completed process/profile/provenance disclosures and the complete limitations block. Incomplete runs retain their actionable failure/recovery controls.

The **Unduh** link retains the archived eight-section HTML report and its report API, reconstructed from frozen inputs and saved results without another model call or change to the baseline. Existing explicit technical URLs for findings, timeline, evidence, scenario and audit remain compatible; they are outside the normal three-tab navigation. The old report tab opens the summary instead. Legacy policy pages retain their own existing shell.

## Two complementary layers

- Simulation personas represent stakeholder perspectives: customers, suppliers, competitors, operators, employees, regulators, partners and indirect stakeholders. Configurable persona counts do not represent population shares.
- Analytical specialists cover Market, Finance, Legal/Compliance and Risk. Their number is separate from simulation personas. Orchestration and report synthesis coordinate the workflow.

OASIS/CAMEL remains the live runtime. A business adapter supplies scoped interactions and server-authoritative state transitions. An offer is separate from acceptance. Financial calculations use typed decimal inputs.

## Truth boundaries

- Persona behavior is a synthetic hypothesis. Source support for a profile attribute does not verify generated behavior.
- Simulated agreement, repetition or graph ingestion is not independent factual evidence.
- User approval confirms the analysis input, not external claim validity.
- Evidence must match geography, period, units and meaning; an official URL alone is insufficient.
- Missing values remain unknown. Numerical outputs are conditional on recorded inputs/formulas.
- A competitor price shock does not automatically change own price or demand. Matching is an explicit strategy assumption.
- Legal findings require qualified review. PAKAR does not certify compliance or predict business success.

## Current capabilities and limits

The implementation includes a shared business workspace, traceable intake/claim review, persona review, leased analysis jobs, interaction reducer, OASIS bridge, specialist adapters, findings/report/export, basic relationship graph and versioned scenario comparison.

Project workspaces also include persistent **Chat & ide**. Users distinguish
supporting documents from idea files, discuss a selected idea or saved analysis
with one named facilitator/specialist per message, and explicitly save immutable
idea revisions. A chosen revision starts a separate swarm run; chat does not
silently change ideas or start simulations. Replies cite supplied excerpts with
source classifications and uncertainty. New intake can open this workspace
before analysis. One active turn per project and no automatic paid retry bound
the pilot. General answer quality, OCR and individual-persona chat remain separate
limitations.

Analysis results also expose **Tanya PAKAR** beside the default graph summary.
This reuses project chat with a pinned saved analysis and its frozen idea version,
showing follow-up turns for that result. Users explicitly send to the facilitator
or one of the four internal specialists. Saved stance counts, recorded reasons
and accepted interactions can be cited as synthetic sources, within the bounded
chat context. A chat does not change votes, update the saved result or start a new
swarm. Drafts and pending request identity survive switching between result tabs;
saved replies remain in the project. Editing an idea and starting another run stay
separate actions in the idea workspace.

The result view uses a neutral canvas around white reading surfaces. Graph nodes
group each stable portrait, name, role and stance marker; the selected person's
recorded reason sits in a white inspection panel. A two-column Executive Summary
stacks on smaller screens and opens the existing chat through **Diskusikan hasil
ini**. The bounded conversation separates its reading area from the composer.
Chat renders resolvable source IDs as numbered controls that open and focus the
original saved quotation. Unmatched or ambiguous references stay as written;
this presentation does not rewrite the answer or infer extra sources.

Offline fixtures are restricted to synthetic projects and visibly labeled. Without an LLM, contextual persona candidates come from a bounded role catalog and require human review; this does not demonstrate live discovery quality.

Live mode requires a configured model provider and installed OASIS runtime. BPS retrieval requires an API key and curated indicators. Retrieved data remains partial until applicability is checked; source outages remain unavailable. Offline tests do not establish live effectiveness or production readiness.

Privacy scope is public, synthetic or non-confidential documents. A configured provider may receive scoped context during live analysis. Enterprise roles, private inference, ERP/CRM, large-data analytics, advanced visualizations and calibrated feasibility scoring remain later work.

See `docs/PAKAR_IMPLEMENTATION_STATUS.md` for verification and remaining release gates.

New business runs separate internal analysis from the stakeholder room. Users
explicitly supply a public stakeholder brief; internal research, the full idea,
business inputs and document-derived persona attributes are not forwarded to
stakeholder models. External personas use bounded synthetic role/lens profiles
and visible discussion messages. The product facilitator in that room also has
only the public brief. Internal specialists cross-check reactions against the
original sources. Run snapshots retain the disclosed brief and stable persona IDs.
Customer base turns can target another customer's contribution from round two,
without forcing consensus or increasing the all-pairs call count. Historical runs
remain unchanged and are labeled when they predate this separation. Ambiguous
launch failures freeze the original brief, body and idempotency key across intake,
project and idea-workspace flows. This isolates simulated-role context; it is not
enterprise user RBAC or automatic DLP for text explicitly put in the public brief.
See `docs/PAKAR_INFORMATION_BOUNDARIES_2026-11-01.md` for implementation and limits.

---
version: 1
slug: "src-components-header-header-tsx"
primary_target: "src/components/Header/Header.tsx"
related_targets: ["src/components/Header/Header.css", "src/components/AppShell/AppShell.tsx", "src/pages/Auth/AuthPage.tsx", "index.html", "public/pakar-mark.svg"]
---

# PAKAR shared branding

Scope: the shared brand presentation for the public home, legacy landing page, authentication screens and workspace shell. This record documents the branding rename to PAKAR. `../PRODUCT.md` from the frontend root supplies product context; `DESIGN.md` remains the visual-system authority. This surface record adds no global design tokens or new design rules.

Direction contract for this change:

- **THESIS:** present a consistent PAKAR identity across shared brand entry points.
- **OWN-WORLD:** retain the incumbent IBM Plex Sans, white/neutral flat surfaces, square blue geometry and enterprise material treatment.
- **STORY:** preserve existing journeys and navigation.
- **FIRST VIEWPORT:** show the PAKAR wordmark beside the P monogram wherever the shared brand is presented.
- **FORM:** a local prescribed extension of the existing identity; no new-world seed or composition exploration applies.

## Observed implementation

`src/components/Header/Header.tsx` exports the shared `Brand` component. The visible wordmark is PAKAR. Its home link has the accessible name `PAKAR, kembali ke awal`; clicking it navigates to `/` and requests a smooth scroll to `utama` when that element exists. The adjacent image is decorative (`alt=""`, `aria-hidden="true"`) so the parent link supplies the accessible name.

`public/pakar-mark.svg` is the shared image source and favicon. It has a square 48-unit view box, a flat blue background using the existing primary color, and white P linework with three white nodes. The SVG title is PAKAR. The base shared-header stylesheet displays the image at 32px beside an 18px, weight-600 wordmark with a 12px gap. These are observations of `Header.css`; contextual sizing remains owned by the consuming stylesheets. IBM Plex Sans, spacing, layout and existing responsive rules remain the incumbent treatment.

`AppShell.tsx` consumes `Brand` in both the sidebar and mobile drawer. `AuthPage.tsx` consumes the same component and names PAKAR in its login/register headings. `index.html` points the favicon to `/pakar-mark.svg`, names PAKAR in the page description and sets the document title to `PAKAR — Business Co-Analyst`. The SVG asset, shared component, auth headings and HTML metadata are the implementation sources of truth for these observations.

The public shared header keeps its existing responsive navigation: at 800px and below the desktop navigation/auth area yields to the menu control. The rename introduces no separate mobile identity or alternative mark.

## Finish evidence and limits

Independent finish-review disposition supplied for this change: **SHIP**, with no material fixes. The review found the wordmark, typography, material, favicon, title and responsive presentation consistent with the prescribed direction.

Evidence is recorded under `../backend/data/runtime-audit/2026-11-01/branding/` from the frontend root:

- `browser-checks.json`: all six route/viewport checks passed for `/`, `/legacy` and `/login` on desktop and mobile, recording the PAKAR title, visible brand and loaded icon.
- Rendered captures: `home-desktop.png`, `home-mobile.png`, `legacy-desktop.png`, `legacy-mobile.png`, `login-desktop.png` and `login-mobile.png`.
- `detector.json`: the single detector pass returned `[]`; no second pass was run.

Authenticated shared-header integration was reviewed in source only. The screenshots and route checks establish the listed public presentations, not rendered authenticated coverage. This document records the supplied review evidence; no browser, detector or test run was performed during documentation. The branding record makes no product-behavior, analytical-quality or release-readiness claim.

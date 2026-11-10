# PAKAR branding — 1 November 2026

The application brand is **PAKAR** across the business workspace and retained policy routes. The product contract remains [PRODUCT.md](../PRODUCT.md).

## Updated names

- Shared wordmarks, accessible names, authentication copy, legacy-page copy, browser titles and favicon use PAKAR. `frontend/public/pakar-mark.svg` replaces the old RK asset with a P monogram using the existing blue-and-white visual system.
- Frontend package/lock metadata, backend package metadata, bundled runtime metadata, API service names, loggers and metrics use `pakar`. Prometheus queries should use the `pakar_` prefix.
- New session cookies use `pakar_session`. Browser workspace, intake, workflow and presentation keys use the `pakar-` prefix.
- Examples, CI, Docker image/runtime paths and Compose defaults use PAKAR. Default database/user names for a new installation are `pakar`; the container service user remains UID/GID 10001 under the new name.
- The archived policy product brief is now `PAKAR_PRODUCT_LEGACY.md`. Historical policy documentation is explicitly distinguished from the current business product.

## Compatibility and existing data

An identity rename must not move a user's saved work into a new empty store. This change does not rename or delete the existing database/user, uploads, cloud object paths, remote graphs, workspace directory, uploaded source documents, or saved simulation results. Explicit local database and cloud-storage configuration is preserved.

The standard `pakar_session` namespace can read an existing `rk_session` cookie. A present new cookie takes precedence even when invalid. Login issues the new cookie and clears the old one; logout clears both and revokes both supplied tokens. Explicit custom cookie namespaces remain isolated. Origin validation continues to apply to requests using either standard cookie name.

Browser caches migrate on access from the old brand prefix into the corresponding PAKAR key, preserving the account namespace. Existing PAKAR data takes precedence. If browser storage cannot write, the old entry remains readable. Clear operations remove both names to prevent stale data returning.

The OASIS bridge accepts the old runtime-path environment name for existing launchers, preferring `PAKAR_OASIS_RUNTIME_PATH`. Zep batch reconciliation reads both the old and new operation markers; new batches use `pakar_operation_id`. These old strings are intentional read-compatibility aliases, not displayed branding.

Before upgrading an existing Compose deployment, retain its explicit `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`, storage prefix and cookie settings as appropriate. Set `BACKEND_VOLUME_NAME` and `POSTGRES_VOLUME_NAME` to the existing physical volume names. Fresh installations default to `pakar_backend_data` and `pakar_postgres_data`. Keep the existing Compose project identity with `docker compose -p <existing-project>` when updating existing containers; changing the project name alone can create a second stack. The GitHub deployment workflow accepts repository variable `DEPLOY_PATH`; set it to the existing checkout location when that location differs from `/opt/pakar`.

Third-party attribution, immutable historical artifacts and dependency caches are retained. No reasoning, persona generation, orchestration or simulation algorithm is changed by this rename.

## Verification

- Frontend: 93 tests pass; ESLint and TypeScript/Vite production build pass. The existing shared-bundle size warning remains.
- Six desktop/mobile browser branding checks pass across homepage, login and legacy landing: wordmark, title, SVG loading and brand viewport containment.
- UI detector: no findings; finish reviewer disposition **ship**, no material fixes. Authenticated shared-header rendering is covered separately by the synthetic workflow check.
- `docker compose config --quiet` passes.
- Backend: 301 tests pass, 2 checks skip according to environment requirements (303 collected).
- Browser: smoke, project-conversation and complete synthetic workflow checks pass. The synthetic workflow covers automatic personas, interaction trace, report and a separate versioned scenario.
- Backend restart completes; `/health`, `/ready` and frontend-proxied health return HTTP 200 with service name `pakar`. Both saved Pepsodent analysis records and their events retain their pre-restart hashes; no active jobs remain.
- Npm and bundled Python runtime lock root names match their manifests. `uv` is unavailable locally, so a full `uv lock --check` was not run.

Local audit evidence is under `backend/data/runtime-audit/2026-11-01/branding/`. Verification uses fixtures/local providers and does not spend AI credit.

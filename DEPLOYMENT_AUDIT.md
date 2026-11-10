# PAKAR Production Deployment Audit & VPS Deployment Plan
**Target Environment:** 2 vCPU, 2 GB RAM — Ubuntu 24.04 LTS (x86_64)  
**Orchestration:** Docker Compose  
**Repository:** PAKAR (`RekaKebijakan`)  
**Role:** Senior DevOps / Infrastructure Engineer  
**Date:** November 2026  

---

## Executive Summary & Feasibility Assessment

This audit evaluates the deployment readiness of the **PAKAR** application onto a single **2 vCPU, 2 GB RAM Ubuntu 24.04 VPS** using Docker Compose.

### Feasibility Verdict: **Conditional / Constrained**
Deploying PAKAR on a 2 GB RAM host is **technically feasible** for small-scale pilot or demo workloads, but **severely constrained**. The repository authors previously noted in `deploy/README.md` that 2 vCPU / 4 GB RAM is the recommended baseline starting point, with 4 vCPU / 8 GB recommended for comfortable build and runtime execution. 

On a 2 GB RAM VPS:
1. **Host Build Bottleneck:** Executing `docker compose build` directly on the VPS (compiling Vite with React Compiler via Babel in Node 22, plus installing Python packages and running `uv sync` for the OASIS multi-agent engine) will exceed physical memory and crash the server with Out-Of-Memory (OOM) errors unless a 4 GB swap file is configured or pre-built container images are utilized.
2. **Runtime Memory Pressure:** Running PostgreSQL 17, Caddy, Nginx, FastAPI (Backend), Celery/Background Worker, and child Python processes (OASIS simulation engine and LLM call worker subprocesses) simultaneously pushes peak memory consumption to **1.5 GB – 1.9+ GB**.
3. **Deployment Package Readiness:** The repository already contains a dedicated, production-hardened Compose configuration under `deploy/compose.vps.yaml`, an Edge reverse proxy configuration (`deploy/Caddyfile`), an Nginx VPS configuration (`deploy/nginx.vps.conf`), and a deployment wrapper (`deploy/pakar.sh`).

---

## 1. Service Inventory & Architecture

The PAKAR platform comprises six distinct services when deployed to production via Docker Compose:

```text
                     [ Public Internet ]
                              |
                     Ports 80 / 443 (TCP)
                              v
                  +-----------------------+
                  |     edge (Caddy)      | <--- Automatic Let's Encrypt / ZeroSSL TLS
                  +-----------------------+
                              |
                     Internal HTTP (:80)
                              v
                  +-----------------------+
                  |   frontend (Nginx)    | <--- Serves React 19 SPA static assets
                  +-----------------------+
                              |
                     Proxy /backend/ -> :5001
                              v
                  +-----------------------+
                  |   backend (FastAPI)   | <--- REST API & Business Logic
                  +-----------------------+
                        |           |
             Internal SQL (:5432)   | Shared Docker Volume (backend_data)
                        |           |
                        v           v
           +-----------------+ +-----------------+
           | database (PG17) | | worker (Python) | <--- Spawns OASIS engine & call_worker
           +-----------------+ +-----------------+      Subprocesses for LLM & BPS APIs
```

### 1.1 Service Catalog

| Service Name | Container / Image | Purpose & Role | Runtime Model & Dependencies |
|---|---|---|---|
| **`edge`** | `caddy:2-alpine` | Public TLS termination & HTTP/HTTPS edge reverse proxy. Enforces HTTPS and routes host traffic to `frontend:80`. | Daemon. Depends on `frontend` (healthy). Publishes host ports `80:80` and `443:443`. |
| **`frontend`** | `pakar-frontend:vps` (built from `frontend/Dockerfile`) | Serves compiled React 19 SPA assets via Nginx 1.29-alpine; reverse proxies `/backend/` requests to `backend:5001`. | Daemon. Mounts `deploy/nginx.vps.conf`. Depends on `backend` (healthy). No host port published. |
| **`backend`** | `pakar-backend:vps` (built from `backend/Dockerfile`) | FastAPI REST API server running Uvicorn (`workers=1`). Handles document intake, user management, and simulation orchestration. | Daemon. Depends on `migrate` (completed successfully). Runs non-root (`pakar`, UID 10001). Healthchecked via `/ready`. |
| **`worker`** | `pakar-backend:vps` (built from `backend/Dockerfile`) | Background task processor (`python worker.py`). Polls PostgreSQL queue, leases jobs, and executes simulations. | Daemon. Depends on `migrate` (completed successfully). Spawns OASIS/CAMEL subprocesses. |
| **`database`** | `postgres:17-alpine` | Relational database holding users, projects, simulations, document metadata, chunks, and audit logs. | Daemon. Healthchecked via `pg_isready`. Persists data to named volume `postgres_data`. No host port published. |
| **`migrate`** | `pakar-backend:vps` (built from `backend/Dockerfile`) | Database schema migration executor running `alembic upgrade head`. | One-shot initialization container (`restart: "no"`). Depends on `database` (healthy). Exits 0 on completion. |

---

## 2. Dockerfiles, Compose Configurations, Ports, and Volumes

### 2.1 Compose Files Analysis

The repository contains three Docker Compose configurations serving different environments:

1. **`compose.yaml` (Development / Backend Focus):**
   - Defines: `database`, `migrate`, `backend`, `worker`, and `backend-test` (profile `test`).
   - **Dev Security Flaw:** Publishes PostgreSQL (`5432:5432`) and FastAPI (`5001:5001`) directly to host `0.0.0.0`.
   - Lacks frontend and reverse proxy.
2. **`compose.full.yaml` (Development / Full Stack Overlay):**
   - Extends `compose.yaml` with the `frontend` service.
   - Publishes Vite/Nginx frontend port `5173:80` directly to the host.
3. **`deploy/compose.vps.yaml` (Production VPS Standalone):**
   - **The authoritative production configuration.**
   - Unifies all six services: `database`, `migrate`, `backend`, `worker`, `frontend`, and `edge` (Caddy).
   - Uses Docker Compose anchor `&app` to share build and environment definitions between `backend`, `worker`, and `migrate`.
   - **Strict port isolation:** Only `edge` binds to host ports (`80` and `443`). `database`, `backend`, `worker`, and `frontend` communicate exclusively over internal Docker networks.
   - Configures Docker logging rotation (`max-size: "10m"`, `max-file: "3"`).

### 2.2 Dockerfile Specifications

#### Backend Dockerfile (`backend/Dockerfile`)
- **Base Stage (`base`):** `python:3.12-slim`
  - Sets `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, `PIP_NO_CACHE_DIR=1`.
  - Copies `pyproject.toml`, `README.md`, `app/`, `alembic.ini`, `migrations/`, and `oasis_engine_runtime/`.
- **Production Stage (`production`):**
  - Installs system libraries: `gcc`, `libc6-dev`, `libcairo2`.
  - Installs backend dependencies: `pip install ".[llm,firebase]" uv`.
  - Installs OASIS engine runtime virtualenv: `uv sync --project /opt/pakar/oasis_engine_runtime --frozen --no-dev`.
  - Creates non-privileged user and group: `pakar:pakar` (UID 10001, GID 10001).
  - Copies `run.py` and `worker.py`.
  - Sets `USER pakar`, `EXPOSE 5001`, `CMD ["python", "run.py"]`.
- **Test Stage (`test`):** Installs `.[test]` and runs `pytest -vv`.

#### Frontend Dockerfile (`frontend/Dockerfile`)
- **Dependencies Stage (`deps`):** `node:22-alpine`
  - Copies `package.json`, `package-lock.json`, runs `npm ci`.
- **Build Stage (`build`):**
  - Ingests build arguments: `VITE_API_URL=/backend`, `VITE_DEMO_MODE=false`.
  - Executes `npm run build` (`tsc -b && vite build` which runs `@rolldown/plugin-babel` with `reactCompilerPreset`).
- **Production Stage (`production`):**
  - Base: `nginx:1.29-alpine`.
  - Copies `nginx.conf` to `/etc/nginx/conf.d/default.conf`.
  - Copies compiled HTML/JS/CSS from `/app/dist` to `/usr/share/nginx/html`.
  - `EXPOSE 80`.

### 2.3 Ports & Networking Mapping

| Service | Internal Port | Host Port (`deploy/compose.vps.yaml`) | Host Port (`compose.yaml` / dev) | Exposure Level |
|---|---|---|---|---|
| `edge` (Caddy) | 80, 443 | **`80:80`, `443:443`** | N/A | **Public** (Internet accessible) |
| `frontend` (Nginx) | 80 | *None* | `5173:80` | Internal container network only |
| `backend` (FastAPI) | 5001 | *None* | `5001:5001` | Internal container network only |
| `database` (PostgreSQL) | 5432 | *None* | `5432:5432` | Internal container network only |
| `worker` (Python) | N/A | *None* | *None* | Internal process only |
| `migrate` (Alembic) | N/A | *None* | *None* | One-shot process |

### 2.4 Volumes & Persistent Mounts

| Volume Name | Type | Mount Target | Description & Purpose |
|---|---|---|---|
| `backend_data` | Named Docker Volume (`pakar_vps_backend_data`) | `/app/data` (in `backend`, `worker`) | Stores uploaded project documents (`/app/data/uploads`) and OASIS simulation artifacts (`/app/data/oasis/simulations`). Must be backed up. |
| `postgres_data` | Named Docker Volume (`pakar_vps_postgres_data`) | `/var/lib/postgresql/data` (in `database`) | Stores PostgreSQL database cluster files. Critical production persistence. |
| `caddy_data` | Named Docker Volume | `/data` (in `edge`) | Stores TLS certificates issued by Let's Encrypt / ZeroSSL and ACME account keys. |
| `caddy_config` | Named Docker Volume | `/config` (in `edge`) | Stores Caddy runtime configuration cache. |
| Bind Mount | Host File | `./Caddyfile:/etc/caddy/Caddyfile:ro` | Edge proxy configuration. |
| Bind Mount | Host File | `./nginx.vps.conf:/etc/nginx/conf.d/default.conf:ro` | Frontend Nginx configuration (preserves HTTPS scheme and proxies `/backend/`). |

---

## 3. Required Environment Variables

The table below lists all required and optional configuration keys across the platform. In accordance with operational security guidelines, **no secret values are displayed**.

| Variable Name | Required? | Default in Repository | Purpose & Component |
|---|---|---|---|
| `PAKAR_DOMAIN` | **Yes (Prod)** | *None* (e.g. `pakar.example.com`) | Hostname used by Caddy for TLS issuance, CORS matching, and HTTP Host header validation. |
| `POSTGRES_DB` | Optional | `pakar` | Name of the PostgreSQL database. |
| `POSTGRES_USER` | Optional | `pakar` | PostgreSQL administrative username. |
| `POSTGRES_PASSWORD` | **Yes (Prod)** | *Required in deploy/.env* | PostgreSQL password. Must be generated randomly (e.g., 64-character hex). |
| `DATABASE_URL` | Derived | Constructed in Compose | Full connection URL (`postgresql+psycopg://...`). |
| `PRODUCTION` | **Yes (Prod)** | `false` (set `true` in VPS) | Enables production security policies (HSTS headers, strict session flags). |
| `AUTH_REQUIRED` | Optional | `false` | When `false`, operates in open shared-workspace mode. When `true`, enforces user authentication. |
| `SESSION_COOKIE_NAME` | Optional | `pakar_session` | Name of the session cookie. |
| `SESSION_COOKIE_SECURE`| **Yes (Prod)** | `false` (must be `true` in Prod) | Enforces the `Secure` attribute on cookies. Mandatory if `PRODUCTION=true` and `AUTH_REQUIRED=true`. |
| `SESSION_TTL_SECONDS` | Optional | `604800` (7 days) | Session expiration time in seconds. |
| `AUTH_MAX_FAILURES` | Optional | `10` | Maximum login failures before IP/account rate-limiting triggers. |
| `AUTH_WINDOW_SECONDS` | Optional | `300` (5 minutes) | Time window for authentication rate-limiting. |
| `CORS_ORIGINS` | **Yes (Prod)** | `https://${PAKAR_DOMAIN}` | Allowed CORS origins for API requests. Must contain explicit HTTPS domain. Wildcard `*` is blocked by backend. |
| `TRUSTED_HOSTS` | **Yes (Prod)** | `${PAKAR_DOMAIN},localhost,127.0.0.1,backend` | Allowed HTTP Host headers enforced by `TrustedHostMiddleware`. |
| `LLM_BASE_URL` | Optional | `https://api.groq.com/openai/v1` | Base URL for LLM inference (compatible with Groq or OpenRouter). |
| `LLM_API_KEY` | Optional | *Empty* | Primary LLM API key. Required if running live AI simulations. |
| `FREE_AI_KEY` | Optional | *Empty* | Secondary/fallback Groq API key automatically selected when endpoint is `api.groq.com`. |
| `PAKAR_ALLOWED_LLM_HOSTS`| Optional | `api.groq.com` | Strict whitelist of allowed LLM outbound hostnames to prevent SSRF and key leakage. |
| `PAKAR_GROQ_REQUEST_TOKEN_LIMIT` | Optional | `7500` | Token ceiling per Groq request to stay within rate-limit windows. |
| `LLM_MODEL` | Optional | `openai/gpt-oss-120b` | Model identifier requested from the provider. |
| `LLM_STRUCTURED_OUTPUTS` | Optional | `true` | Request JSON Schema constrained outputs from the model. |
| `LLM_FALLBACK_POLICY` | Optional | `raise` | Failure mode when model call fails (`raise` or `deterministic`). |
| `LLM_MAX_OUTPUT_TOKENS` | Optional | `2500` | Output token generation ceiling. |
| `PROVIDER_TIMEOUT_SECONDS` | Optional | `120` | Maximum time allowed for provider operations. |
| `LLM_REQUEST_TIMEOUT_SECONDS` | Optional | `90` | Maximum HTTP socket timeout for an individual LLM request. |
| `PAKAR_MAX_RUN_COST_USD` | Optional | `0.01` (vps) / `0.03` (dev) | Hard dollar spend limit per analysis run. |
| `PAKAR_CREDIT_RESERVE_USD` | Optional | `0.10` | Required pre-run credit reserve before inference is dispatched. |
| `PAKAR_OPENROUTER_MAX_PRICE` | Optional | *Empty* | JSON object defining price ceiling per million tokens on OpenRouter. |
| `PAKAR_OPENROUTER_PROVIDER_ORDER` | Optional | *Empty* | Explicit provider routing preferences on OpenRouter. |
| `OASIS_ENABLED` | Optional | `true` | Enables the OASIS direct multi-agent simulation engine. |
| `DEFAULT_SIMULATION_ENGINE` | Optional | `oasis` | Default simulation engine (`oasis` or `deterministic`). |
| `ZEP_API_KEY` | Optional | *Empty* | API key for Zep Cloud temporal knowledge graph integration. |
| `BPS_API_KEY` | Optional | *Empty* | API key for official Indonesian Badan Pusat Statistik (BPS) Web API. |
| `PAKAR_BPS_INDICATORS` | Optional | `[]` | JSON array of curated BPS indicator mappings. |
| `STORAGE_BACKEND` | Optional | `local` | Upload storage backend (`local` or `firebase`). |
| `STORAGE_PATH` / `UPLOAD_DIR` | Optional | `/app/data/uploads` | Path for uploaded documents on local disk. |
| `EMBEDDED_WORKER` | **Yes (Prod)** | `false` | Must remain `false` in production so the dedicated `worker` service processes queue jobs. |
| `WORKER_POLL_SECONDS` | Optional | `0.5` | Polling frequency for the worker task loop. |
| `WORKER_LEASE_SECONDS` | Optional | `180` | Lease duration for distributed worker fencing. |
| `BACKEND_VOLUME_NAME` | Optional | `pakar_vps_backend_data` | Custom named volume for backend uploads. |
| `POSTGRES_VOLUME_NAME`| Optional | `pakar_vps_postgres_data` | Custom named volume for PostgreSQL data. |
| `VITE_API_URL` | Build-time | `/backend` | Frontend API proxy path compiled into the SPA bundle. |
| `VITE_DEMO_MODE` | Build-time | `false` | Disables client-side mocked demo mode. |

---

## 4. Development vs. Production Settings Differential

The table below contrasts default development values with the required production settings for the VPS:

| Setting / Config Item | Development Default | VPS Production Target | Technical Rationale & Impact |
|---|---|---|---|
| **`PRODUCTION`** | `false` | **`true`** | Activates `Strict-Transport-Security` (HSTS) in `RequestSecurityMiddleware` and enforces secure session cookies. |
| **`SESSION_COOKIE_SECURE`** | `false` | **`true`** | When `false`, browsers transmit cookies over unencrypted HTTP. Production enforces `Secure; HttpOnly; SameSite=Lax`. |
| **`AUTH_REQUIRED`** | `false` | **`false` (or `true`)** | In `deploy/compose.vps.yaml`, PAKAR defaults to a shared public workspace (`AUTH_REQUIRED=false`). If user isolation is required, set to `true`. |
| **`CORS_ORIGINS`** | `http://localhost:5173,http://127.0.0.1:5173` | **`https://${PAKAR_DOMAIN}`** | Rejects browser requests from unapproved domains. Wildcards (`*`) cause FastAPI startup validation to crash. |
| **`TRUSTED_HOSTS`** | `localhost,127.0.0.1,testserver` | **`${PAKAR_DOMAIN},localhost,127.0.0.1,backend`** | Prevents HTTP Host Header poisoning. Blocks unapproved Host headers at ASGI middleware. |
| **`POSTGRES_PASSWORD`** | `pakar` (hardcoded default) | **Random 64-char Hex** | Default credentials present extreme vulnerability if port is leaked. Hex avoids URL-encoding failures. |
| **Host Port Bindings** | `5432` (PG), `5001` (API), `5173` (UI) | **None** (Only Caddy `80` & `443`) | Isolates database and application containers from raw internet port scans. |
| **Docker Log Driver** | Default unbounded logging | **`json-file` (10m max, 3 files)** | Prevents Docker container logs from consuming 100% of the VPS root filesystem disk space. |
| **Reverse Proxy** | None (direct port exposure) | **Caddy + Nginx** | Caddy provides automated ACME TLS certificates and HTTP-to-HTTPS redirect. |
| **`EMBEDDED_WORKER`** | `true` (in local backend `.env`) | **`false`** | Prevents the API web process from executing long-running simulation jobs internally. |

---

## 5. Storage, Migrations, Uploads, and Backup Architecture

### 5.1 Database Migrations
- **Engine:** Alembic with SQLAlchemy Core.
- **Migration History:** 17 migrations located in `backend/migrations/versions/` (from `0001_initial_postgresql.py` through `0017_provider_spending.py`).
- **Execution Strategy:** The `migrate` service runs `alembic upgrade head` inside container networking before `backend` or `worker` start.
- **Production Caveat:** Docker Compose `depends_on: { migrate: { condition: service_completed_successfully } }` only fires when the `migrate` container runs. During rolling updates or `git pull` updates, `migrate` does not re-run automatically if the container is already exited. The deployment procedure must explicitly execute:
  ```bash
  sudo sh deploy/pakar.sh run --rm migrate
  ```

### 5.2 Persistent Storage & Uploaded Documents
- **Physical Location:** Mounts `backend_data` volume to `/app/data` inside backend and worker containers.
  - Documents: `/app/data/uploads/business/<project_id>/<doc_id>.<ext>`
  - OASIS Artifacts: `/app/data/oasis/simulations/<simulation_id>/`
- **User Permissions:** Non-root user `pakar` (UID 10001, GID 10001). When restoring files from external hosts, ownership must be reset using `chown -R 10001:10001 /app/data/uploads`.
- **Intake Pipeline & Limits:**
  - Supported file types: `.pdf`, `.docx`, `.txt`, `.md`.
  - Scanned PDF limitation: PyMuPDF extracts text streams; image-only scanned PDFs fail extraction with `needs_ocr`.
  - Quotas: `MAX_FILE_UPLOAD_BYTES=20971520` (20 MB), `MAX_UPLOAD_BYTES=33554432` (32 MB), `MAX_FILES_PER_PROJECT=20`, `MAX_PDF_PAGES=200`, `MAX_EXTRACTED_CHARS=2000000`.

### 5.3 Backup & Recovery Procedures

#### 1. Automated PostgreSQL Dump
PostgreSQL custom-format dump (`pg_dump -Fc`) produces consistent, compressed binary backups without requiring service stoppage:
```bash
# Execute directly inside the database container
sudo sh deploy/pakar.sh exec -T database sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl --file=/tmp/pakar-backup.dump'

# Copy backup to secure host backup directory
sudo mkdir -p /srv/pakar-backups
sudo chmod 700 /srv/pakar-backups
sudo sh deploy/pakar.sh cp database:/tmp/pakar-backup.dump /srv/pakar-backups/pakar-$(date +%Y%m%d_%H%M%S).dump
sudo sh deploy/pakar.sh exec -T database rm -f /tmp/pakar-backup.dump
```

#### 2. Storage Volume Snapshot
The uploaded files and simulation artifacts residing in `backend_data` must be archived alongside the database dump:
```bash
sudo tar -czf /srv/pakar-backups/pakar-data-$(date +%Y%m%d_%H%M%S).tar.gz -C /var/lib/docker/volumes/pakar_vps_backend_data/_data .
```

#### 3. Database Restore
To restore data into a clean deployment:
```bash
sudo sh deploy/pakar.sh cp /srv/pakar-backups/pakar-backup.dump database:/tmp/pakar.dump
sudo sh deploy/pakar.sh exec -T database sh -c \
  'pg_restore --clean --if-exists --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/pakar.dump'
```

---

## 6. Security Audit Findings

| Category | Finding / Risk | Severity | Repository Status & Recommendation |
|---|---|---|---|
| **Public Ports** | Direct host exposure of PostgreSQL (5432) and API (5001) in root `compose.yaml`. | **HIGH** | `deploy/compose.vps.yaml` mitigates this completely by publishing **only ports 80 and 443**. Never run root `compose.yaml` on the public VPS. |
| **Authentication** | Default deployment operates with `AUTH_REQUIRED=false`. | **HIGH** (if unintended) | Shared-workspace mode allows any visitor to read/modify projects and trigger LLM inferences. If private accounts are needed, set `AUTH_REQUIRED=true` and `SESSION_COOKIE_SECURE=true`. |
| **Rate Limiting** | `LoginRateLimiter` is held in-memory (`threading.Lock` + `defaultdict(deque)`). | **MEDIUM** | In-memory limiter resets if the backend container restarts. Acceptable for single-container deployment; would require Redis if backend were scaled horizontally. |
| **CORS Policy** | Strict origin validation via `OriginValidationMiddleware`. | **LOW (Good)** | The backend rejects requests containing `*` or unregistered origins for state-changing HTTP methods. `deploy/compose.vps.yaml` correctly sets `CORS_ORIGINS=https://${PAKAR_DOMAIN}`. |
| **Host Header Attack** | `TrustedHostMiddleware` enforces host validation. | **LOW (Good)** | Unregistered `Host` headers are dropped before reaching application routes. |
| **API Key Protection** | Isolation of LLM credentials from child processes and logs. | **LOW (Good)** | `call_worker.py` and `oasis_direct.py` pass secrets via JSON over `stdin`, preventing argument inspection via `ps aux`. `safe_error()` suppresses URL/body details from error logs. |
| **SSRF Mitigation** | `require_allowed_llm_endpoint()` validates outbound endpoints. | **LOW (Good)** | Hardcoded hostname whitelist `PAKAR_ALLOWED_LLM_HOSTS=api.groq.com` prevents malicious redirection or key exfiltration to unauthorized endpoints. |
| **HTTPS / TLS** | Edge routing managed by Caddy 2. | **LOW (Good)** | Automatic certificate provisioning via Let's Encrypt / ZeroSSL with automatic HTTP-to-HTTPS redirect. |
| **Security Headers** | Injected by `RequestSecurityMiddleware`. | **LOW (Good)** | Injects `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and `HSTS` (when `PRODUCTION=true`). |

---

## 7. Memory & Concurrency Analysis on a 2 vCPU, 2 GB RAM VPS

### 7.1 Memory Footprint Breakdown

Running the full PAKAR stack on a 2 GB physical RAM VPS operates at the outer threshold of hardware capacity:

| Process / Component | Typical Resident Memory (RSS) | Peak Memory Under Load |
|---|---|---|
| **Ubuntu 24.04 OS** (Kernel, systemd, journald, containerd, dockerd) | ~350 MB | ~450 MB |
| **PostgreSQL 17** (`database`) | ~80 MB | ~180 MB |
| **Caddy 2** (`edge`) | ~30 MB | ~50 MB |
| **Nginx** (`frontend`) | ~15 MB | ~30 MB |
| **FastAPI Backend** (`backend`, Uvicorn worker) | ~180 MB | ~280 MB |
| **Background Worker** (`worker`, idle loop) | ~190 MB | ~260 MB |
| **OASIS Subprocess** (`oasis_direct_bridge.py` in venv) | ~0 MB (idle) | **~350 MB – 550 MB** (active) |
| **External Call Worker Subprocesses** (`call_worker.py`) | ~0 MB (idle) | **~80 MB – 150 MB** |
| **Estimated Total Consumption** | **~845 MB (Idle)** | **~1,480 MB – 1,950 MB (Active)** |

> [!WARNING]
> **Out-Of-Memory (OOM) Danger:**  
> During an active multi-agent simulation with 8–10 personas and paired specialist reviews, physical RAM consumption reaches ~1.95 GB. Without swap space, the Linux kernel OOM Killer will immediately terminate PostgreSQL, the worker, or the backend process.

### 7.2 Docker Build Memory Bottleneck on 2 GB Host

Attempting to build Docker images on the VPS will crash without specific precautions:
1. **Frontend Build (`npm run build`):** Compiling TypeScript (`tsc -b`) and running Vite with Babel + React Compiler consumes **800 MB – 1.2 GB RAM** during peak bundling.
2. **Backend Build (`pip install` + `uv sync`):** Installing heavy Python wheels (`PyMuPDF`, `lxml`, `psycopg`, `camel-ai`, `camel-oasis`) inside the container consumes **700 MB – 1.1 GB RAM**.
3. **Concurrent Builds:** Running `docker compose build` builds both services simultaneously, requiring >2.2 GB RAM and causing immediate failure.

### 7.3 Concurrency & Simulation Architecture

1. **Worker Queue Isolation:** The worker loop processes jobs sequentially (`workflow.run_once()`). There is only one active simulation job processed at a time per worker instance, preventing unbounded worker queue sprawl.
2. **Internal Simulation Concurrency:**
   - Swarm simulations utilize bounded turns (e.g., 3 rounds, 4 customer lenses).
   - Paired specialist reviews execute with a concurrency of 2 (`review_concurrency: 2`).
   - Groq API rate limiting is actively protected by `groq_limits.py`, which monitors retry headers, enforces backoff delays, and limits request tokens via `PAKAR_GROQ_REQUEST_TOKEN_LIMIT=7500`.
3. **Process Spawning Behavior:**
   - `budget.py: call_worker()` spawns a clean child Python process for individual API calls and kills it immediately upon completion or timeout.
   - `oasis_direct.py` spawns a dedicated streaming subprocess for `business-stream`.

### 7.4 Low-Memory Hardening Measures (Mandatory for 2 GB VPS)

1. **4 GB Swapfile Configuration:** Configure a 4096 MB swap file on the host SSD with `vm.swappiness=10`. This provides a virtual memory safety valve during image compilation and burst simulation phases.
2. **Container Memory Limits:** Add memory caps in Docker Compose to prevent an errant worker subprocess from starving PostgreSQL:
   - `database`: `mem_limit: 384m`, `mem_reservation: 128m`
   - `backend`: `mem_limit: 512m`, `mem_reservation: 200m`
   - `worker`: `mem_limit: 768m`, `mem_reservation: 250m`
   - `frontend`: `mem_limit: 64m`
   - `edge`: `mem_limit: 64m`
3. **Sequential Build Sequence:** Never run parallel builds. Build backend first, then frontend, using `--no-cache` only if necessary.
4. **PostgreSQL Low-Memory Tuning:** In production Compose, pass low-memory configuration parameters to Postgres:
   ```yaml
   command: ["postgres", "-c", "shared_buffers=64MB", "-c", "work_mem=4MB", "-c", "max_connections=30"]
   ```

---

## 8. Step-by-Step Production Deployment Plan

### Phase 1: Host Preparation & Swap Configuration
Execute on the clean Ubuntu 24.04 VPS via SSH:

```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y git ca-certificates curl ufw fail2ban

# 2. Configure 4 GB Swap space (CRITICAL for 2 GB RAM host)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 3. Optimize swappiness for low-memory server
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.d/99-pakar-swap.conf

# 4. Configure UFW Firewall (Only SSH, HTTP, and HTTPS open)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status
```

### Phase 2: Install Official Docker Engine & Compose Plugin

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

### Phase 3: Repository Setup & Environment Provisioning

```bash
# 1. Clone repository to /opt/pakar
sudo mkdir -p /opt/pakar
sudo chown "$USER":"$(id -gn)" /opt/pakar
git clone https://github.com/Jerome-88/PAKAR.git /opt/pakar
cd /opt/pakar

# 2. Initialize environment file from VPS template
cp deploy/vps.env.example deploy/.env
chmod 600 deploy/.env

# 3. Generate a cryptographic PostgreSQL password
PG_PASS=$(openssl rand -hex 32)
sed -i "s/REPLACE_WITH_64_HEX_CHARACTERS/$PG_PASS/" deploy/.env

# 4. Configure domain and API keys
nano deploy/.env
# Set:
# PAKAR_DOMAIN=pakar.yourdomain.com
# LLM_API_KEY=your_actual_key
# FREE_AI_KEY=your_groq_key_if_applicable
```

### Phase 4: DNS Verification & Image Building

```bash
# 1. Verify DNS A-record resolves to the VPS IP
dig +short A pakar.yourdomain.com

# 2. Build images SEQUENTIALLY to prevent compiler OOM on 2 GB RAM
sudo sh deploy/pakar.sh build backend
sudo sh deploy/pakar.sh build frontend
```

### Phase 5: Database Startup & Schema Migration

```bash
# 1. Start PostgreSQL database container
sudo sh deploy/pakar.sh up -d database

# 2. Wait for database healthcheck to report healthy
until [ "$(sudo sh deploy/pakar.sh ps --filter name=database --format '{{.Health}}')" = "healthy" ]; do
  printf '.'
  sleep 2
done
printf 'Database is healthy.\n'

# 3. Execute one-shot Alembic migration
sudo sh deploy/pakar.sh run --rm migrate
```

*(Optional: If importing pre-existing demo data such as the Pepsodent demo, restore the database dump and copy uploaded files to `/app/data/uploads` before launching the web layer, as documented in `deploy/README.md` Section 6).*

### Phase 6: Stack Launch & Verification

```bash
# 1. Launch all production services
sudo sh deploy/pakar.sh up -d

# 2. Check running container status
sudo sh deploy/pakar.sh ps

# 3. Verify container logs
sudo sh deploy/pakar.sh logs --tail=50 edge frontend backend worker

# 4. Verify local ready and health endpoints
curl -I http://127.0.0.1/
sudo sh deploy/pakar.sh exec backend python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5001/ready').read().decode())"
```

### Phase 7: Post-Deployment Smoke Verification & Routine Maintenance

1. **External Endpoint Verification:**
   ```bash
   curl -I https://pakar.yourdomain.com/
   curl --fail https://pakar.yourdomain.com/backend/ready
   ```
2. **Automated Backup Cron:**
   Add a daily cron job (`/etc/cron.daily/pakar-backup`) to execute the database dump and volume archive commands outlined in Section 5.3.
3. **Application Updates Procedure:**
   When updating application code via `git pull`:
   ```bash
   cd /opt/pakar
   git pull --ff-only
   sudo sh deploy/pakar.sh build backend
   sudo sh deploy/pakar.sh build frontend
   sudo sh deploy/pakar.sh stop edge frontend worker backend
   sudo sh deploy/pakar.sh run --rm migrate
   sudo sh deploy/pakar.sh up -d
   ```

---

## 9. Audit Summary & Conclusion

The PAKAR codebase exhibits **mature containerization practices**:
- Clear separation of concerns between API web serving (`run.py`), asynchronous job processing (`worker.py`), database migration (`migrate`), static asset serving (`frontend`), and TLS termination (`edge`).
- Clean abstraction of IPC with isolated child processes communicating via structured JSON on `stdin`/`stdout`.
- Sensitive credentials and API keys are isolated from command-line arguments and excluded from application error payloads.
- An existing production-ready deployment directory (`deploy/`) with a secure Compose configuration (`deploy/compose.vps.yaml`) that binds only ports 80/443.

**Primary Caution for 2 vCPU / 2 GB RAM:**  
Memory is the sole critical constraint. The deployment **must** configure a 4 GB swap file on the host OS and enforce sequential container builds to avoid OOM crashes during deployment and multi-agent simulation workloads.


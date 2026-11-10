# PAKAR — Referensi Teknis Lengkap (Tech Stack & Alur Sistem)

Dokumen ini merekam arsitektur workflow kebijakan lama dan infrastruktur bersama. Produk bisnis aktif PAKAR dijelaskan di [PRODUCT.md](PRODUCT.md) dan [status implementasi](docs/PAKAR_IMPLEMENTATION_STATUS.md).

## 0. Konteks Workflow Kebijakan Lama
PAKAR adalah prototipe platform simulasi skenario kebijakan publik (submisi GEMASTIK 2026, Divisi VI — Kota Cerdas). Produk mengubah dokumen kebijakan (draf regulasi/program) menjadi graf kebijakan terstruktur, menghasilkan persona sintetis pemangku kepentingan, menjalankan simulasi skenario berbatas ronde, lalu menyusun laporan yang seluruh klaimnya tertaut ke sitasi sumber. Prinsip inti: **evidence traceability** — setiap node graf, persona, event simulasi, bagian laporan, dan jawaban interaksi harus bisa ditelusuri ke dokumen asli, event simulasi, atau elemen graf. Model tidak dipercaya begitu saja; klaim sumber divalidasi ulang oleh backend terhadap evidence tersimpan. Produk eksplisit menyatakan diri sebagai *decision-support*, bukan pengganti konsultasi publik/keputusan kebijakan.

Repo adalah monorepo dua workspace utama: `frontend/` (React SPA) dan `backend/` (FastAPI + worker + sub-proyek mesin simulasi `oasis_engine_runtime/`).

---

## 1. Tumpukan Teknologi Lengkap

### 1.1 Frontend (`frontend/`)
| Kebutuhan | Teknologi | Versi | Keterangan |
|---|---|---|---|
| Framework UI | React + ReactDOM | 19.2.7 | Function component + hooks |
| Bahasa | TypeScript | ~6.0.2 | Strict typing |
| Build tool | Vite | 8.1.1 | `@vitejs/plugin-react`, `@rolldown/plugin-babel`, `babel-plugin-react-compiler` |
| Routing | react-router-dom | 7.18.1 | Client-side routing |
| Data fetching/cache | @tanstack/react-query | 5.101.4 | Polling status job, cache respons API |
| Visualisasi graf | d3-force, d3-drag, d3-selection, d3-zoom | 3.x | Render graf kebijakan interaktif |
| Konten | react-markdown + remark-gfm | 10.1.0 / 4.0.1 | Render laporan & jawaban Markdown/GFM |
| Font | @fontsource/ibm-plex-sans | 5.2.8 | Di-bundle, tanpa CDN |
| Lint | eslint + typescript-eslint | 10.6.0 / 8.62.0 | `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh` |
| Unit test | vitest + @testing-library/react + jsdom | 4.1.10 | `@testing-library/jest-dom`, `@testing-library/user-event` |
| Mock API | msw | 2.15.0 | Mock Service Worker untuk test |
| E2E test | @playwright/test | 1.61.1 | `playwright.config.ts`, target Chromium |
| Server produksi | nginx | 1.29-alpine | Serve build statis + reverse proxy |

Struktur `frontend/src/`: `api/` (client.ts, queries.ts), `auth/` (AuthContext, ProtectedRoute, storageNamespace), `components/` (AppShell, CitationDrawer, Header, Markdown), `pages/` (Auth, Dashboard, PersonaStudio, ProjectDetail, ProjectWizard, ProjectsList, Provenance, Reports, ScenarioBuilder, SimulationMonitor, SimulationWorkflow), `data/` (content, dashboard, localWorkspace, projects, scenarios — data demo lokal untuk mode `demo-*`).

### 1.2 Backend (`backend/`)
| Kebutuhan | Teknologi | Versi | Keterangan |
|---|---|---|---|
| Bahasa | Python | ≥3.11 (image: 3.12-slim) | |
| Web framework | fastapi | 0.139–<1 | + uvicorn 0.51–<1 |
| Validasi | pydantic | 2.10–<3 | Skema request/response & kontrak provider |
| Upload multipart | python-multipart | 0.0.22–<1 | |
| Nama file aman | Werkzeug | 3.1–<4 | `secure_filename` |
| Ekstraksi PDF | PyMuPDF (`fitz`) | 1.25–<2 | |
| Ekstraksi DOCX | python-docx | ==1.2.0 | + lxml 6.0–<7 |
| Env file | python-dotenv | 1.0–<2 | |
| Hash password | pwdlib[argon2] | 0.3–<1 | Argon2 |
| ORM/Core | SQLAlchemy | 2.0–<3 | Core (Table/Column), bukan ORM class |
| Driver Postgres | psycopg[binary] | 3.2–<4 | psycopg3 |
| Migrasi | alembic | 1.14–<2 | `backend/migrations/` |
| Test | pytest + httpx | 8.3–<9 / 0.28–<1 | optional-dependency `[test]` |
| LLM client | openai | 1.0–<3 | optional-dependency `[llm]` |
| Firebase | firebase-admin | 6.6–<8 | optional-dependency `[firebase]` |

Modul inti `backend/app/`: `api.py` (>100 route), `auth.py` (register/login/session), `config.py` (Settings terpusat), `database.py` (skema SQLAlchemy), `documents.py` (ekstraksi & chunking), `engine.py`, `errors.py` (ApiError & subclass), `evaluation.py` (gerbang kualitas deterministik), `middleware.py` (4 ASGI middleware), `metrics.py` (Prometheus), `models.py` (28 Pydantic input model), `oasis_direct.py` + `oasis_direct_bridge.py` (jembatan subprocess ke mesin OASIS), `oasis_runtime.py` (normalisasi event/persona OASIS→domain), `provider_contracts.py` (kontrak input/output tiap operasi provider), `provider_errors.py`, `providers.py` (provider deterministik + OpenAI-compatible, 950 baris), `quick_demo.py` (bundle demo publik tanpa upload), `repository.py` (akses data, 1465 baris — terbesar), `service.py` (`WorkflowService`, orkestrator utama, 1371 baris), `storage.py` (abstraksi Local/Firebase Storage).

### 1.3 Mesin Simulasi & AI
| Komponen | Teknologi | Peran |
|---|---|---|
| Provider deterministik | Internal (`providers.py: DeterministicPolicyProvider`) | Offline, stance = hash(simulation_id, ronde, index grup) — reproducible, dipakai test & evaluasi |
| Provider LLM | SDK `openai`, kompatibel base URL apa pun | Ontology/report lebih kaya; default model `gpt-4o-mini`, fallback ke deterministic bila gagal (`LLM_FALLBACK_POLICY`) |
| Mesin sosial | `backend/oasis_engine_runtime/` — sub-proyek Python **terpisah**, dependency dikelola `uv` (punya `pyproject.toml` & `uv.lock` sendiri), berbasis **CAMEL-AI** | Simulasi multi-agent dunia Twitter-like & Reddit-like berjalan paralel |
| Struktur `oasis_engine_runtime/` | `app/api`, `app/models`, `app/services`, `app/utils`, `locales/{id,en}.json`, `scripts/*` | `scripts/run_parallel_simulation.py`, `run_twitter_simulation.py`, `run_reddit_simulation.py`, `activity_schedule.py`, `action_logger.py`, `agent_language.py`, `hard_timeout.py`, `validate_zep_cloud_integration.py` |
| Jembatan proses | `oasis_direct.py: DirectOasisEngine` + `oasis_direct_bridge.py` | Backend memanggil runtime OASIS via `subprocess` menggunakan Python venv OASIS sendiri (`oasis_engine_runtime/.venv/bin/python`), protokol JSON lewat stdin/stdout; ada varian streaming (`_call_stream`) untuk aksi yang di-stream real-time |
| Memori graf temporal | **Zep Cloud** (`ZEP_API_KEY`) | Ingest teks sumber ke graf, entitas jadi node, aksi simulasi memperbarui graf temporal |

### 1.4 Infrastruktur & DevOps
| Komponen | Teknologi |
|---|---|
| Containerization | Docker multi-stage. Backend: `python:3.12-slim` → stage `production` (install `.[llm,firebase]` + `uv sync` untuk oasis_engine_runtime, user non-root `pakar` uid 10001) & stage `test`. Frontend: `node:22-alpine` (deps→build) → `nginx:1.29-alpine` (production), stage `test` terpisah |
| Orkestrasi | Docker Compose. Base `compose.yaml`: `database`, `migrate` (one-shot `alembic upgrade head`), `backend`, `worker`, `backend-test` (profil `test`). Overlay `compose.full.yaml`: tambah `frontend` |
| Volume persisten | `backend_data` (uploads, data oasis), `postgres_data` |
| CI | GitHub Actions `.github/workflows/ci.yml` |
| CD | GitHub Actions `.github/workflows/deploy-backend.yml` — SSH ke VM (appleboy/ssh-action) |
| Hosting frontend alternatif | Vercel (`frontend/vercel.json`, SPA rewrite semua path ke `index.html`) |
| Task runner | `Makefile` (`up`, `up-d`, `full-up`, `full-up-d`, `down`, `full-down`, `test`, `evaluation`, `smoke`, `health`, `reset`) |

### 1.5 Observability & Keamanan
- 4 ASGI middleware kustom (urutan pemasangan): `TrustedHostMiddleware` → `RequestSizeLimitMiddleware` → `OriginValidationMiddleware` → `CORSMiddleware` → `RequestSecurityMiddleware`.
- Endpoint operasional: `GET /health` (liveness sederhana), `GET /ready` (cek koneksi DB + storage + `schema_revision`), `GET /metrics` (format Prometheus text 0.0.4).
- Logger `pakar` (app) & `pakar.access` (request log terstruktur dengan request-id).

---

## 2. Arsitektur Sistem — Alur Request

```
Browser (SPA)
  → nginx (frontend container, port 80→5173 host)
      • / → static React build (SPA fallback: try_files → index.html)
      • /backend/ → proxy_pass ke backend:5001
  → FastAPI (backend container, Uvicorn, port 5001)
      • Middleware chain (lihat 1.5)
      • Router: public_router (/api/health, /api/public/*, /api/pilot/contact),
                auth_router (/api/auth/*),
                router (/api/*, /api/simulations/* — kompatibel-frontend),
                v1_router (/api/v1/* — REST resource)
      • app.state.workflow = WorkflowService  → baca/tulis PostgreSQL via SQLAlchemy+psycopg3
      • app.state.storage = Local/FirebaseStorageBackend
  ⇄ PostgreSQL 17 (service `database`)
  ⇄ worker container (python worker.py) — proses independen menjalankan WorkflowService.run_once()
      • claim_next_job() dari tabel `jobs` (lease-based)
      • jalankan tahap: graph / environment / simulation / report
      • panggil provider: DeterministicPolicyProvider ATAU DirectOasisEngine (subprocess)
      • DirectOasisEngine → oasis_engine_runtime (venv terisolasi) → LLM API + Zep Cloud
      • simpan hasil ke PostgreSQL (state JSONB + tabel ternormalisasi)
```

Backend dan worker berbagi kode `WorkflowService` yang sama persis. Saat `EMBEDDED_WORKER=true` (dipakai untuk test), thread worker berjalan tertanam di proses API — tidak perlu container terpisah.

Model deployment produksi: VM tunggal (GCP) menjalankan `docker compose -f compose.yaml` (backend + worker + db, tanpa frontend container — frontend dideploy terpisah, mis. ke Vercel) ATAU `compose.full.yaml` untuk semua-dalam-satu-VM.

---

## 3. Model Data PostgreSQL (24 tabel, `backend/app/database.py`, versi lewat Alembic)

| Kelompok | Tabel | Kolom/ciri kunci |
|---|---|---|
| Identitas | `users` | id, name, email (unique), password_hash, created_at |
| Identitas | `sessions` | token sesi opak → user_id, TTL |
| Proyek | `projects` | status (`draft/active/archived/pending_delete/deleted`), `version` (optimistic lock), `workflow_mode` (`quick_demo/full_simulation`), `demo_bundle_id`, `idempotency_key` (unique per owner), `delete_after`/`deleted_at` (retensi) |
| Proyek | `audit_events` | jejak audit aksi pada proyek |
| Proyek | `pilot_contacts` | form kontak/pilot publik (`/api/pilot/contact`) |
| Workflow inti | `simulations` | `state` **JSONB** = snapshot kanonik seluruh workflow (project, ontology, graph, environment, simulation, report, interviews, graph_feedback, stages) |
| Workflow inti | `workflow_events` | log append-only (`sequence` Identity, `type`, `payload` JSONB) per simulasi |
| Workflow inti | `artifact_versions` | versi artefak (mis. laporan) untuk perbandingan/riwayat |
| Antrean job | `jobs` | `stage`, `status` (`queued/running/paused/completed/failed/cancelled`), `lease_owner`, `lease_expires_at`, `heartbeat_at`, `attempts`/`max_attempts`, `checkpoint` JSONB (resumable), `execution_token`, `lease_generation`, `cancel_requested_at`/`pause_requested_at`, `error_code`/`error_class`/`retryable`, `next_retry_at` (backoff), `dead_lettered_at`, `idempotency_key`, `input_revision`. Constraint unik: **hanya satu job aktif per simulasi** (`queued/running/paused`) |
| Antrean job | `job_attempts` | histori tiap percobaan eksekusi job |
| Dokumen | `documents` | metadata berkas (media type, size, hash, page count, extraction version) |
| Dokumen | `document_pages` | metadata per halaman (untuk PDF) |
| Dokumen | `document_chunks` | potongan teks bersitasi stabil (document_id, chunk_id, ordinal, char_start, char_end, text) |
| Dokumen | `citations` | objek sitasi terstruktur lintas subjek |
| Skenario (v1) | `scenarios` | skenario ber-versi milik proyek |
| Skenario (v1) | `scenario_revisions` | riwayat revisi konfigurasi skenario |
| Skenario (v1) | `scenario_runs` | run yang dipin ke revisi skenario tertentu |
| Skenario (v1) | `run_events` | event run, dipaginasi via cursor |
| Persona | `custom_personas` | persona buatan pengguna / override manual |
| Interaksi | `interviews` | hasil wawancara persona |
| Interaksi | `graph_feedback_versions` | riwayat feedback graf (accept/reject/comment) yang membatalkan artefak turunan |
| Integrasi OASIS | `oasis_runtime_mappings` | korelasi simulation_id lokal ↔ external_project_id/external_simulation_id/zep_graph_id, `graph_revision`, `status`, `config`/`metadata`/`runtime_status`/`artifacts` JSONB |
| Integrasi OASIS | `oasis_actions` | aksi mentah platform (`platform`, `external_sequence`, `source_identity`, `run_id`) di-stream inkremental |

Pola desain: **JSONB untuk state yang cepat berubah bentuk** (snapshot workflow), **tabel ternormalisasi + FK `ON DELETE CASCADE`** untuk apa pun yang butuh sitasi, replay, atau query lintas simulasi.

---

## 4. Kontrak Provider (Validasi Input/Output, `provider_contracts.py`)

Setiap operasi provider (`ontology`, `graph`, `environment`, `simulate`, `report`, `answer`, `interview`, `graph_memory`) dibungkus decorator `@validated(operation)` di `providers.py` yang:
1. Memvalidasi **input** terhadap `PROVIDER_INPUTS[operation]` (mis. `OntologyInput`, `GraphInput`, `EnvironmentInput`, `SimulateInput`, `ReportInput`, `AnswerInput`, `InterviewInput`, `GraphMemoryInput`) — gagal → `ProviderInputError`.
2. Menjalankan fungsi provider (deterministic atau LLM).
3. Memvalidasi **output** terhadap `PROVIDER_OUTPUTS[operation]` (mis. `OntologyOutput`, `GraphOutput`, `EnvironmentOutput`, `SimulationOutput`, `ReportOutput`, `AnswerOutput`, `InterviewOutput`) — gagal → `ProviderOutputError`.

Model dasar: `Contract` (BaseModel), `InputEntity` → `Project`, `Chunk`, `Ontology`, `GraphNode`, `GraphEdge`, `Graph`, `Persona`, `Event`. Model output granular: `GraphNodeOutput`, `GraphEdgeOutput`, `PersonaOutput`, `EventOutput`, `ReportSection`, `Risk`, `InterviewAnswer`, dll. Ini memastikan **provider apa pun (deterministic/LLM/OASIS-normalized) mengembalikan bentuk data yang identik** ke lapisan service.

---

## 5. Alur Kerja Produk — 5 Tahap (User-Facing)

1. **Source Intake** — metadata proyek (nama, institusi, tujuan analisis) + unggah PDF/DOCX/MD/TXT. Validasi tipe/size/kuota → simpan file (local/Firebase) → simpan project+simulation di Postgres (stage awal = graph) → antre job graph-build.
2. **Graph Build** — ekstraksi ontologi (entity type: Policy/Stakeholder/Issue/Risk/Outcome; relation type: RESPONDS_TO/RAISES/AFFECTS) + konstruksi graf kebijakan bersitasi.
3. **Environment Setup** — pasangkan stakeholder×issue jadi persona sintetis (peran, stance, concern, evidence link); resolve konfigurasi ronde/kanal/seed. Pada OASIS: generate profil Twitter (CSV) & Reddit (JSON) paralel + `simulation_config.json`.
4. **Simulation** — jalankan skenario berbatas ronde. Deterministik: iterasi grup stakeholder per ronde, stance dari hash. OASIS: dua dunia platform berjalan paralel, aksi di-stream & dipersist inkremental, tunggu ingest Zep sebelum selesai.
5. **Report & Interaction** — agregasi event → bagian laporan (ringkasan, temuan, rekomendasi) + entri risiko bersitasi; dukung tool follow-up (report/persona/evidence/risk/compare/revision) dan wawancara persona.

---

## 6. Pipeline Teknis Internal — 11 Tahap (A–K)

| # | Tahap | Input | Proses inti | Output |
|---|---|---|---|---|
| A | Inisialisasi Proyek | metadata + file + user + idempotency key | validasi ≥1 dokumen, cek kuota (files/size/quota), generate ID durable, simpan file, set stage awal, antre job | project, simulation, file tersimpan, job antre |
| B | Ekstraksi & Chunking | file tersimpan | ekstrak teks per tipe (PyMuPDF/python-docx/text), normalisasi metadata, split overlapping chunks, assign metadata stabil | teks, chunk, metadata sitasi |
| C | Evidence Retrieval | query + chunk | tokenisasi, buang stopword, skor by term-count, ranking stabil (relevansi→document_id→ordinal), fallback ke chunk awal jika tak ada match | chunk terurut + citation object |
| D | Ontology Generation | metadata proyek + chunk | ekstrak istilah dominan, definisikan entity/relation type, lampirkan sitasi | versi ontologi + ringkasan |
| E | Konstruksi Graf | project + ontologi + chunk | node policy/stakeholder/issue + sitasi per node + edge by relation type; jalur OASIS: ingest ke Zep (buat graph_id, submit batch, tunggu ingest, fetch node/edge) | graf (node+edge), revisi, provenance |
| F | Environment & Persona | graf + config + simulation_id | pilih node stakeholder/issue, pasangkan jadi persona, assign influence score (deterministic hash), tautkan evidence, resolve config; OASIS: filter entitas dari Zep, generate profil paralel (opsional via LLM), simpan Reddit(JSON)/Twitter(CSV), generate time/activity config | daftar persona + config resolved + file profil (OASIS) |
| G | Scenario Simulation | simulation_id + graf + persona + config | Deterministik: per ronde × grup, pilih persona, stance dari hash(sim,ronde,grup), buat statement+channel+risk narrative. OASIS: load profil, jalankan dunia Twitter&Reddit paralel, stream aksi, normalisasi ke skema event, persist inkremental, tunggu ingest graph-memory | run_id, event terurut, status runtime, aksi tersimpan |
| H | Graph Memory Update | graf saat ini + event | pilih event kritis (stance kritis), ubah concern berulang jadi node risiko memori, tautkan ke node sumber, lampirkan sitasi event pemicu | graf terbarui + revisi memori |
| I | Report Generation | project + chunk + event | hitung/analisis event by stance/grup/concern/risk, identifikasi event kritis & isu berulang, retrieval evidence relevan, generate bagian laporan + entri risiko + sitasi; jalur kaya: loop ReACT (plan outline → fetch context → tool call: search/insight/panorama/interview → generate iteratif, log thought/tool call/hasil) | report_id, versi, judul, section, risiko, sitasi |
| J | Interaksi & Wawancara | pertanyaan user + tool type (report/persona/evidence/risk/compare/revision) + grup persona opsional + state + chunk | pilih event/chunk relevan, pilih strategi jawab sesuai tool, generate jawaban dengan referensi; wawancara: pilih persona target, ambil event terkait, generate jawaban per-perspektif, ringkas lintas persona | jawaban + citation id + jawaban wawancara |
| K | Evaluation | fixture deterministik + required concepts + report claims | bandingkan klaim vs konsep wajib (normalized text match), validasi referensi sitasi ke fixture source id, ukur cakupan sitasi pada klaim yang butuh sitasi | JSON metrik (`concept_recall`, `citation_validity`, `citation_coverage`) + pass/fail vs `EVALUATION_FAIL_THRESHOLD` (default 0.8) |

---

## 7. Siklus Job Asinkron & Mekanisme Worker

- **State mesin job**: `queued → running → (paused|completed|failed|cancelled)`. Hanya **satu job aktif per simulasi** (constraint unik partial index di kolom `simulation_id` where status in queued/running/paused).
- **Lease-based polling**: worker (`worker.py`, atau thread tertanam bila `EMBEDDED_WORKER=true`) memanggil `claim_next_job(worker_id, lease_seconds)` tiap `WORKER_POLL_SECONDS` (default 0.5s). Job disewa (`lease_owner`, `lease_expires_at`, `heartbeat_at`) sehingga worker lain tak bisa mengambilnya sampai lease habis (`WORKER_LEASE_SECONDS`, default 180s) atau job selesai. `lease_generation` mencegah race saat lease diperbarui/direbut.
- **Resumable checkpoint**: kolom `checkpoint` JSONB memungkinkan job melanjutkan dari titik tertentu, bukan mengulang dari awal, pada operasi panjang (mis. simulasi OASIS).
- **Retry & dead-letter**: `attempts`/`max_attempts` (default 3), `error_code`/`error_class`/`retryable`, `next_retry_at` untuk backoff, `dead_lettered_at` bila melebihi batas percobaan.
- **Kontrol pengguna**: `cancel_requested_at` / `pause_requested_at` — worker mengecek flag ini secara kooperatif di tengah eksekusi.
- **Recovery saat startup**: `service.recover()` dipanggil di `lifespan` FastAPI untuk mengambil alih job yang tertinggal setelah crash/restart.
- **Idempotency**: `POST /api/projects` menerima header `Idempotency-Key`; permintaan berulang dengan key sama + user sama mengembalikan state yang sudah ada (tabel `jobs.idempotency_key`, `projects.idempotency_key` unik per owner).
- **Optimistic locking**: `projects`, `scenarios`, persona override, dan run membawa `version` integer; mutasi mengirim `expected_version`/`expected_scenario_version`/`base_environment_revision` → gagal `409 revision_conflict` bila basi.
- **Retensi & purge**: `purge_due_projects()` dipanggil tiap iterasi loop worker, menghapus proyek berstatus `pending_delete` yang telah lewat `delete_after` (dihitung dari `PROJECT_RETENTION_DAYS`, default 30 hari).

---

## 8. Permukaan API Lengkap

### 8.1 Publik (tanpa auth) — prefix `/api`
- `GET /health` — status service.
- `GET /public/quick-demo`, `POST /public/quick-demo/interactions` — demo tanpa login/upload.
- `POST /pilot/contact` (alias `POST /v1/contact-requests`) — form kontak.

### 8.2 Autentikasi — prefix `/api/auth`
- `POST /register`, `POST /login`, `GET /me`, `POST /logout`.

### 8.3 Jembatan tahap kompatibel-frontend — prefix `/api` (dengan `Depends(current_user)`)
- `POST /projects` (multipart create), `GET /projects`, `GET /projects/{id}`, `GET /projects/{id}/chunks`.
- `GET /simulations/{id}`, `GET /simulations/{id}/stream`.
- `POST /simulations/{id}/stages/{stage}/start` (stage ∈ graph/environment/simulation/report) — selalu `202`.
- `POST /simulations/{id}/graph-build`, `GET .../graph`, `GET/POST .../ontology[/generate]`.
- `POST /simulations/{id}/environment/generate`, `GET/PATCH .../environment`, `GET/POST .../personas[/generate]`, `GET/POST .../config[/generate]`.
- `POST /simulations/{id}/runs`, `GET /runs/{id}`, `GET /runs/{id}/events`, `POST .../pause|resume|cancel`.
- `GET /simulations/{id}/oasis/status`, `.../runtime-graph`, `.../posts`, `.../comments`, `.../timeline`, `.../agent-stats`, `POST .../oasis/close`.
- `POST /simulations/{id}/reports`, `GET /reports`, `GET /reports/{id}[/markdown|/agent-log|/console-log|/evidence]`.
- `GET /simulations/{id}/citations`, `POST/GET .../interviews`, `POST/GET .../graph/feedback`, `POST .../interactions` (alias `/reports/{id}/interactions`, `/interactions/{id}/messages`), `GET /interactions/{id}[/messages]`.

### 8.4 REST resource — prefix `/api/v1`
- Projects: `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}`, `POST .../archive|restore|duplicate`, `POST /projects/bulk-actions`, `GET /projects/{id}/provenance`.
- Scenarios: `GET/POST /projects/{id}/scenarios`, `GET/PATCH/DELETE .../scenarios/{sid}`, `POST .../archive|restore|duplicate`, `POST /scenarios/compare`.
- Personas: `GET .../scenarios/{sid}/personas`, `PUT/DELETE .../persona-overrides/{pid}`, `POST .../personas` (custom), `PATCH .../personas/{pid}`, `DELETE .../personas/{pid}`, `POST .../personas/bulk-activation`, `PATCH .../personas/bulk`.
- Runs: `POST .../scenarios/{sid}/run(s)`, `GET .../scenarios/{sid}/runs`, `GET .../scenarios/{sid}/comparison`, `GET /runs/{rid}`, `GET /runs/{rid}/events?cursor=...`, `GET /runs/{rid}/actions|artifacts|provenance|logs`, `POST /runs/{rid}/pause|resume|cancel|reproduce`, `POST /runs/{rid}/interviews|interactions`.
- Graf: `POST /projects/{id}/graph/feedback`.
- Dashboard: `GET /dashboard`.

### 8.5 Amplop error standar
```json
{ "error": { "code": "string", "message": "string", "details": {} }, "message": "string" }
```
Kode error (`errors.py`): `not_found` (404), `stage_locked` (409), `invalid_control` (409), `unsupported_document` (422), `upload_quota_exceeded` (413), `unauthorized` (401), `email_conflict` (409), `rate_limit_exceeded` (429, header `Retry-After`), `revision_conflict` (409), `validation_error` (422), `payload_too_large` (413), `invalid_origin` (403), `provider_{category}` (502/503), `internal_error` (500).

---

## 9. Model Input Pydantic (`models.py`, 28 kelas)
`AuthInput`→`RegisterInput`/`LoginInput`, `ProjectInput`, `ProjectUpdateInput`, `ProjectDuplicateInput`, `ProjectBulkLifecycleInput`, `EnvironmentInput`/`EnvironmentUpdateInput`, `SimulationInput`, `InteractionInput`/`RunInteractionInput`, `InterviewInput`/`RunInterviewInput`, `GraphFeedbackInput`, `ScenarioConfig`, `ScenarioInput`/`ScenarioUpdateInput`, `ScenarioRunInput`, `ScenarioCompareInput`, `PersonaPatch`→`CustomPersonaInput`/`CustomPersonaUpdateInput`, `PersonaOverrideInput`/`PersonaOverrideDeleteInput`, `PersonaBulkInput`/`PersonaBulkPatchInput`, `PilotContactInput`.

---

## 10. Ekstraksi & Chunking Dokumen (`documents.py`)
- Ekstensi diterima: `.pdf` (PyMuPDF/`fitz`), `.docx` (python-docx), `.md`, `.txt`.
- Setiap segmen teks (`TextSegment`) menyimpan `char_start`, `char_end`, dan lokator asal (`page`/`paragraph`/`line`) — dasar dari sitasi presisi-karakter.
- `_assemble()` menggabungkan segmen, menormalkan whitespace, dan menegakkan batas `max_chars` — melempar error bila teks hasil ekstraksi kelewat besar.
- Chunking downstream: `CHUNK_SIZE` default 1200 karakter, `CHUNK_OVERLAP` default 150 (overlapping window, deterministik untuk reproducibility).
- Evidence retrieval (`providers.py: retrieve_chunks`): tokenisasi regex kata ≥4 huruf, buang stopword Bahasa Indonesia (`yang`, `dan`, `atau`, dst.), skor by term-count, ranking stabil `(-skor, document_id, ordinal)`, fallback ke chunk awal bila tidak ada match sama sekali.

---

## 11. Mode Simulasi

| | `deterministic` | `oasis` |
|---|---|---|
| Jaringan | Tidak perlu (offline) | Perlu (`LLM_API_KEY`, `ZEP_API_KEY`) |
| Reproducibility | Penuh (hash-based) | Bergantung model & lingkungan eksternal |
| Sumber persona | Pairing stakeholder×issue statis | Profil agent generated (opsional via LLM), Twitter CSV + Reddit JSON |
| Kanal | Channel generik (forum/sosmed/rapat publik) | Dunia Twitter-like & Reddit-like paralel sungguhan |
| Eksekusi | In-process Python | Subprocess venv terisolasi (`oasis_direct_bridge.py`) |
| Pemicu | `TESTING=true` atau `OASIS_ENABLED=false` | Default (`DEFAULT_SIMULATION_ENGINE=oasis`) bila dikonfigurasi |
| Kegunaan | Test otomatis, `make evaluation`, dev tanpa kredensial | Demo/produksi dengan hasil sosial yang lebih kaya |

---

## 12. Autentikasi & Keamanan

- **Sesi**: token opak 32-byte (`secrets.token_urlsafe`), cookie `HttpOnly`, `SameSite=Lax`, `Secure` (wajib bila `PRODUCTION=true`), TTL `SESSION_TTL_SECONDS` default 604800 (7 hari).
- **Password**: Argon2 via `pwdlib.PasswordHash.recommended()`. Login ke email tak terdaftar tetap menjalankan verifikasi hash dummy (mitigasi timing attack).
- **Rate limiting**: `LoginRateLimiter` sliding-window, dua kunci sekaligus — per-IP klien dan per-akun (SHA-256 email) — `AUTH_MAX_FAILURES` (default 10) dalam `AUTH_WINDOW_SECONDS` (default 300).
- **Middleware ASGI** (urutan): `TrustedHostMiddleware` (whitelist Host) → `RequestSizeLimitMiddleware` (tolak body > `MAX_UPLOAD_BYTES` progresif saat streaming, bukan cuma cek Content-Length) → `OriginValidationMiddleware` (tolak method non-GET/HEAD/OPTIONS/TRACE dari Origin di luar whitelist) → `CORSMiddleware` (`allow_credentials=True`, origin eksplisit — wildcard `*` ditolak validasi startup) → `RequestSecurityMiddleware` (request-id, header keamanan: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy: default-src 'none'`, `Strict-Transport-Security` bila produksi; plus catat metrik & access log).
- **Storage path safety**: `normalize_storage_key()` menolak path absolut, traversal (`..`), backslash, dan null byte; `LocalStorageBackend` memverifikasi hasil resolve tetap di dalam root sebelum I/O.
- **Batas upload/kuota**: `MAX_FILE_UPLOAD_BYTES` 16MB, `MAX_TOTAL_UPLOAD_BYTES` 1GB/proyek, `MAX_FILES_PER_PROJECT` 20, `MAX_ACTIVE_PROJECTS_PER_USER` 100, `MAX_PDF_PAGES` 200, `MAX_EXTRACTED_CHARS` 2.000.000, `MAX_CHUNKS_PER_DOCUMENT` 5.000.
- **Isolasi data**: proyek & artefak workflow privat ke pembuatnya (`owner_user_id`); baris legacy tanpa owner tidak bisa diakses.

---

## 13. Observability

- `GET /health` — liveness sederhana + daftar `simulation_engines` aktif.
- `GET /ready` — cek `repository.ping()`, `storage.healthcheck()`, `schema_revision()` (Alembic).
- `GET /metrics` — Prometheus text format: `pakar_http_requests_total{method,route,status}`, `pakar_http_request_duration_seconds_sum{method,route}`, `pakar_jobs{status}` (queued/running/paused/failed/dead_letter), `pakar_oldest_queued_job_age_seconds`. Path di-normalisasi (`/projects/{id}` dst.) agar cardinality label terkendali.
- Access log terstruktur per request dengan `request_id` (header `X-Request-ID`, auto-generate bila tidak valid).

---

## 14. Konfigurasi Lingkungan (`config.py`, tervalidasi ketat saat startup)

| Grup | Variabel | Default |
|---|---|---|
| Server | `HOST`, `PORT`, `DATA_DIR` | 0.0.0.0 / 5001 |
| Database | `DATABASE_URL` | `postgresql+psycopg://pakar:pakar@localhost:5432/pakar` |
| Sesi | `SESSION_COOKIE_NAME`, `SESSION_TTL_SECONDS`, `SESSION_COOKIE_SECURE` | `pakar_session` / 604800 / false |
| CORS/Host | `CORS_ORIGINS`, `TRUSTED_HOSTS` | wajib eksplisit, tolak `*` |
| Provider | `POLICY_PROVIDER` (`deterministic`\|`openai`), `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_FALLBACK_POLICY` (`deterministic`\|`raise`), `LLM_MAX_OUTPUT_TOKENS` (≥256) | `deterministic` / `gpt-4o-mini` / `deterministic` / 2500 |
| Chunking | `CHUNK_SIZE`, `CHUNK_OVERLAP` | 1200 / 150 |
| Timeout | `PROVIDER_TIMEOUT_SECONDS`, `LLM_REQUEST_TIMEOUT_SECONDS`, `OASIS_PREPARE_TIMEOUT_SECONDS`, `OASIS_REPORT_TIMEOUT_SECONDS` | 120 / 90 / 900 / 900 |
| Report agent | `REPORT_AGENT_MAX_TOOL_CALLS`, `REPORT_AGENT_MAX_REFLECTION_ROUNDS` | 2 / 1 |
| Worker | `EMBEDDED_WORKER`, `WORKER_POLL_SECONDS`, `WORKER_LEASE_SECONDS`, `JOB_DELAY` | false / 0.5 / 180 / 0.08 |
| Storage | `STORAGE_BACKEND` (`local`\|`firebase`), `STORAGE_PATH`, `FIREBASE_STORAGE_BUCKET`, `FIREBASE_STORAGE_PREFIX`, `GOOGLE_APPLICATION_CREDENTIALS` | local |
| Produksi | `PRODUCTION` (wajib `true` bareng `SESSION_COOKIE_SECURE=true`) | false |
| Auth | `AUTH_MAX_FAILURES`, `AUTH_WINDOW_SECONDS` | 10 / 300 |
| Retensi/Kuota | `PROJECT_RETENTION_DAYS`, `MAX_ACTIVE_PROJECTS_PER_USER`, `MAX_FILES_PER_PROJECT`, `MAX_FILE_UPLOAD_BYTES`, `MAX_TOTAL_UPLOAD_BYTES`, `MAX_PDF_PAGES`, `MAX_EXTRACTED_CHARS`, `MAX_CHUNKS_PER_DOCUMENT` | 30 / 100 / 20 / 16MB / 1GB / 200 / 2.000.000 / 5.000 |
| OASIS | `OASIS_ENABLED`, `OASIS_RUNTIME_DIR`, `OASIS_DATA_DIR`, `DEFAULT_SIMULATION_ENGINE` (`deterministic`\|`oasis`), `ZEP_API_KEY` | true / oasis |

Validasi startup penting: `OASIS_ENABLED=true` + bukan testing → wajib `LLM_API_KEY` dan `ZEP_API_KEY` terisi, kalau tidak `create_app()` melempar `ValueError` (fail-fast, bukan fallback diam-diam).

---

## 15. Testing & Evaluation

- **Backend** (`backend/tests/`, 16 file): `test_api.py`, `test_auth.py`, `test_document_metadata.py`, `test_documents.py`, `test_engine.py`, `test_evaluation.py`, `test_oasis_activity.py`, `test_oasis_direct.py`, `test_oasis_runtime.py`, `test_project_creation.py`, `test_project_lifecycle.py`, `test_provider_contracts.py`, `test_quick_demo.py`, `test_repository.py`, `test_scenario_runs.py`, `test_storage.py`, `test_storage_lifecycle.py`. Jalan: `pytest -vv` + `python -m compileall -q app`.
- **Evaluasi deterministik** (`app/evaluation.py`, network-free): fixture di `evaluations/fixtures/v1` (schema_version "1.0"), metrik `concept_recall`, `citation_validity`, `citation_coverage`; gagal bila skor apa pun < `EVALUATION_FAIL_THRESHOLD` (default 0.8). Jalankan: `make evaluation` atau `python -m app.evaluation --fail-threshold 0.8`.
- **Frontend**: `npm test` (vitest run), `npm run lint` (eslint), `npm run build` (tsc -b && vite build), `npm run test:e2e` (playwright), `npm run test:e2e:oasis` (`RUN_OASIS_E2E=true`, spesifik `oasis-workflow.spec.ts`).
- **Smoke test produksi**: `scripts/production-smoke.sh` (via `make smoke`) — register/login cookie flow, upload dokumen, 5 langkah workflow, sitasi laporan, interaksi laporan lewat proxy nginx produksi.
- **E2E OASIS sungguhan**: `scripts/oasis-e2e.sh` — start compose produksi penuh, Playwright Chromium 5 profil × 3 ronde, verifikasi provenance environment OASIS, penyelesaian Twitter&Reddit, event ternormalisasi, laporan, interaksi, aksi mentah tersimpan. Timeout per tahap `OASIS_STAGE_TIMEOUT_MS` (default 15 menit), `KEEP_STACK=true` untuk retain container.

---

## 16. CI/CD (`.github/workflows/`)

**`ci.yml`** (trigger: PR, push ke `main`, manual):
- Job `backend` (ubuntu + service Postgres 17): install `.[test]` → verifikasi Alembic single head → `alembic upgrade head` → `alembic current --check-heads` → `alembic check` → `pytest -vv` → `python -m app.evaluation --fail-threshold 0.8`.
- Job `frontend`: `npm ci` → `npm test` → `npm run lint` → `npm run build` → install Playwright Chromium → `npm run test:e2e`.
- Job `production-images`: build image `production` target untuk backend & frontend (validasi Dockerfile tanpa push).

**`deploy-backend.yml`** (trigger: push ke `main`, manual): SSH (appleboy/ssh-action) ke VM GCP (`secrets.GCP_HOST/GCP_USERNAME/GCP_SSH_PRIVATE_KEY`) → `cd /opt/pakar` → `git pull origin main` → `docker builder prune -af` → `docker compose -f compose.yaml build --pull` → `docker compose -f compose.yaml up -d` → cek status & disk.

Frontend punya jalur deploy independen ke **Vercel** (`vercel.json`) sebagai alternatif ke container nginx.

---

## 17. Prinsip Desain & Batasan Tanggung Jawab
- Evidence traceability sebagai syarat produk, bukan fitur tambahan — setiap sitasi divalidasi backend terhadap evidence tersimpan, ID sumber dari model tidak dipercaya mentah.
- Path internal storage tidak pernah diekspos lewat API proyek/evidence.
- Persona adalah pendekatan sintetis, bukan representasi individu nyata; keluaran simulasi adalah sinyal eksploratif, bukan prediksi opini publik.
- Produk tidak menggantikan konsultasi publik, tinjauan hukum, atau penilaian pakar domain — ia mempercepat identifikasi pertanyaan, risiko, dan prioritas konsultasi.

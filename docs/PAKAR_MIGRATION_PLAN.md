# Rencana migrasi workflow kebijakan ke PAKAR bisnis

Tanggal: 27 Oktober 2026. Status: rencana implementasi, belum mengubah aplikasi.
Sumber kebutuhan: `PAKAR_PRD_v1.0.docx`; pemetaan teknis berdasarkan pembacaan kode repository ini.

## 1. Arah produk dan keputusan awal

PAKAR adalah AI co-analyst untuk menemukan blind spot dalam keputusan bisnis. Target utama Business Analyst dan Strategic Planning, dengan demonstrasi pertama proposal ekspansi F&B Jakarta.

Perubahan inti adalah mengganti pekerjaan sistem: dari menghasilkan reaksi persona sosial menjadi mengekstrak asumsi, memeriksa bukti, menghitung dampak, menguji silang temuan, dan menyarankan tindakan validasi.

Alur target:

`Project → Upload → Claim Extraction → Human Review → Evidence Retrieval → Specialist Analysis → Cross-review → Findings & Report → Scenario Comparison`

Keputusan implementasi yang diusulkan:

- Pertahankan React, TypeScript, FastAPI, PostgreSQL, SQLAlchemy, Alembic, storage, dan worker yang sudah ada.
- Gunakan empat specialist: Market, Finance, Risk, Legal/Compliance; ditambah Orchestrator dan Report Agent. Enam peran ini tidak memerlukan enam layanan atau model berbeda.
- Jadikan evidence registry dan claim registry sebagai sumber utama. Graf claim–evidence–finding adalah tampilan turunan opsional, bukan prasyarat analisis.
- Keluarkan OASIS, Twitter/Reddit, persona sintetis, dan Zep dari jalur default PAKAR. Simpan sebagai modul legacy selama transisi.
- MVP memakai severity, confidence rationale, dan missingness. Feasibility score numerik menunggu rubrik yang tervalidasi.
- Perhitungan memakai fungsi Python bertipe dan `Decimal`, dengan kontrak unit/periode; eksekusi Python bebas dari LLM tidak diperlukan di MVP.
- MVP menangani dokumen publik, sintetis, atau non-rahasia sesuai PRD. Kebutuhan enterprise dan konektor data besar masuk tahap berikutnya.

## 2. Pemetaan kode yang sudah ada

| Bagian sekarang | Keputusan | Perubahan konkret |
| --- | --- | --- |
| `backend/app/auth.py`, middleware | Pakai kembali | Terapkan ownership ke semua resource bisnis; data classification dan aturan egress diperiksa server |
| `documents.py`, `storage.py` | Pakai dan perluas | Pertahankan chunk/offset/hash; tambah parsing tabel DOCX, deteksi scan/tabel gagal, status ekstraksi |
| `database.py`, `repository.py`, Alembic | Pakai infrastruktur | Tambah model bisnis dan repository terpisah; migrasi aditif |
| `service.py`, `worker.py`, tabel jobs | Pakai pola eksekusi | Pisahkan mekanisme lease/retry dari handler tahap kebijakan; tambah analysis job dan event bisnis |
| `providers.py`, `provider_errors.py` | Adaptasi | Reuse transport/error handling; tambah kontrak agent bisnis dan hasil bertipe |
| `provider_contracts.py`, `models.py` | Tambah kontrak baru | Claim, Evidence, Finding, Calculation, AgentRun, ScenarioPatch; jangan mengganti nama schema sosial saja |
| `oasis_direct*`, `oasis_runtime.py`, `oasis_engine_runtime/` | Legacy opsional | Tidak dibuat saat startup PAKAR; tidak diinstal dalam image default PAKAR |
| `frontend/src/api/client.ts`, `queries.ts` | Reuse pola | DTO dan query keys bisnis baru, tanpa membawa asumsi `simulation_id` ke seluruh domain |
| `ProjectWizard`, `ProjectsList`, `ProjectDetail` | Adaptasi | Industri, lokasi, target customer, decision question, klasifikasi data |
| `SimulationWorkflowPage`, `workflowSession`, demo data | Ganti alur | Halaman bisnis baru; jangan memperluas monolit workflow sosial |
| `SimulationMonitor`, SSE/reconnect | Reuse mekanisme | Tampilkan status agent, tool, temuan parsial, biaya, dan kegagalan |
| `CitationDrawer`, `Markdown`, `Reports`, `Provenance` | Adaptasi | Sumber eksternal, waktu observasi/retrieval, validasi, metode dan input hitungan |
| `ScenarioBuilder`, scenario revisions/run snapshots | Reuse konsep | Scenario patch dan snapshot immutable; tabel sosial tidak langsung diperlakukan sebagai schema bisnis |
| Evaluasi dan smoke test | Perluas/ganti fixture | Dataset bisnis, anotasi blind spot, benchmark dengan tools setara |

Temuan kode yang memengaruhi urutan kerja:

1. `create_project()` sekarang langsung mengantrekan graph build. PAKAR harus berhenti setelah ekstraksi dan memberi kesempatan review claim sebelum analisis.
2. `jobs`, `documents`, `document_chunks`, `citations`, dan `workflow_events` terikat ke `simulations`. Reuse memerlukan migrasi hubungan resource, bukan hanya label UI baru.
3. Citation type dibatasi constraint database dan union TypeScript. Evidence eksternal dan calculation perlu kontrak yang diperluas atau kontrak bisnis tersendiri.
4. `Settings.load()` default mengaktifkan OASIS dan memerlukan LLM/Zep key. Docker production juga selalu memasang dependensi runtime sosial. Keduanya harus dipisahkan.
5. Parser DOCX sekarang membaca paragraf, belum isi tabel. Ini penting untuk proposal bisnis berisi angka.
6. Provider deterministik saat ini membuat stakeholder/persona dari template. Itu tidak dapat menjadi bukti kebenaran analisis bisnis.
7. Evaluator saat ini menilai claim yang sudah ada di fixture, bukan menjalankan pipeline end-to-end. Perlu harness baru untuk membuktikan kualitas PAKAR.

## 3. Arsitektur target

```text
React workspace
  → FastAPI + session auth + project ownership
  → Business intake / claim review API
  → PostgreSQL job queue → worker
      → Analysis Orchestrator
          → Evidence retrieval + typed calculators melalui Tool Gateway
          → Market / Finance / Legal checks
          → Risk challenge + bounded peer review
          → Finding validator → Report synthesis
  → Registry + immutable run snapshots + audit events
  → SSE progress → Findings dashboard / Scenario Lab / Export
```

Orchestrator berupa state machine dengan dependency eksplisit. LLM boleh membantu merencanakan pemeriksaan, tetapi server mengatur tool permission, kuota, timeout, tahap yang sah, dan kapan proses berhenti. Jumlah agent aktif dan putaran review dibatasi, rekomendasi maksimum dua putaran.

Paket backend yang diusulkan:

```text
app/business/
  contracts.py, api.py, repository.py, service.py
  claims.py, evidence.py, findings.py, reports.py, scenarios.py
  orchestrator.py, agents/, prompts/
app/tools/
  gateway.py, calculators.py, sources/
app/jobs/
  runner.py, handlers.py
```

Nama file adalah usulan pemisahan tanggung jawab. Tidak perlu memecah seluruh kode legacy di muka; ekstrak hanya mekanisme yang benar-benar dipakai bersama.

## 4. Model data dan versioning

| Entitas | Data minimum dan aturan |
| --- | --- |
| Project | Tambah `product_kind`, industry, region code, target_customer, decision_question, data_classification; pertahankan owner/lifecycle |
| Document/Chunk | Project ownership, hash, extraction version, locator dan parse status; review menghasilkan revision baru |
| Claim/ClaimRevision | Kutipan asli, normalized claim, variable, nilai nullable, unit, mata uang, region, period, classification, source pointer, approval |
| AnalysisRun | Project, claim/document snapshot, config, stage/status, budget, prompt/model/tool version, waktu dan parent/baseline |
| EvidenceSnapshot | Origin, URL/dataset, published/observed/retrieved time, region code, unit, potongan sumber/hash, status dan alasan kecocokan |
| ClaimEvidenceLink | Relasi supports/contradicts/context serta penjelasan relevansi; adanya URL saja tidak cukup untuk verified |
| CalculationRun | Formula/version, typed inputs, claim/evidence references, unit conversions, output nullable, rounding dan missing inputs |
| AgentRun/ToolCall | Role, task, attempt, status, sumber yang digunakan, ringkasan alasan, usage, cost aktual/estimated dan latency |
| Finding | Severity, affected claim atau missing-assumption record, evidence/calculation IDs, status, rationale, confidence, next validation, suggested owner |
| ScenarioVersion | Baseline analysis ID, shock type, typed patch, region/duration, version, child analysis ID |
| Report | Analysis ID, finding IDs, revision, limitations, export metadata |

Pisahkan classification claim (`supplied_fact`, `assumption`, `calculation`, `opinion`, `forecast`), human review status, evidence status (`VERIFIED`, `PARTIAL`, `CONFLICTING`, `UNAVAILABLE`, `STALE`), dan finding validation status. Informasi yang diberikan pengguna belum otomatis terverifikasi secara eksternal.

Analysis mengacu ke snapshot yang dibekukan. Koreksi claim membuat revisi baru dan menandai analisis sebelumnya tidak mutakhir; hasil lama tetap dapat diaudit. Scenario membuat child analysis baru dan tidak mengubah baseline.

Untuk dokumen lama, tambahkan `project_id`, backfill lewat `simulations.project_id`, validasi hasil, lalu izinkan resource bisnis tanpa `simulation_id`. Constraint menjamin dokumen memiliki parent sah. Untuk queue, tambahkan `analysis_id` dengan constraint tepat satu target legacy/business; perluas runner agar claim job, heartbeat dan penyelesaian memagari kedua jenis target.

Gunakan `analysis_events` dan citation/link bisnis tersendiri untuk menghindari memaksa finding baru menjadi event sosial. Setiap mutasi menjalankan ownership dan expected revision check.

## 5. Tahapan implementasi dan kriteria selesai

### M0 — Fondasi migrasi dan kontrak

- Catat kontrak API/data, model snapshot, status tahap, dan semantik unknown/partial failure.
- Tambah identitas project bisnis dan feature flag; pertahankan akses data kebijakan lama.
- Pisahkan startup/image PAKAR dari OASIS; LLM tetap dibutuhkan untuk mode live, Zep tidak wajib.
- Siapkan fixture ekspansi F&B dengan anotasi claim dan angka yang diketahui.
- Verifikasi lisensi kode turunan/dependensi sebelum distribusi PAKAR.

Selesai ketika: kontrak resource disepakati secara teknis, migrasi legacy diuji di database salinan/fixture, startup PAKAR tidak membutuhkan Zep, dan rute produk baru dapat dipisahkan.

### M1 — Intake dan assumption registry

- Ubah intake sesuai FR-01; batas pilot 20 MB/file, konsisten di frontend, backend, proxy, serta batas total request.
- Pisahkan pembuatan project, upload, ekstraksi, dan start analysis.
- Perluas parser untuk tabel DOCX dan text-table PDF yang didukung; scan tanpa teks menjadi `needs_ocr`/unreadable. OCR otomatis di luar MVP.
- Ekstrak significant claims dengan schema tervalidasi, sumber span yang dapat ditemukan kembali, unit dan periode.
- Tambah claim review: edit, approve, reject, tambah asumsi manual dengan provenance user-supplied.
- Nilai finansial yang tidak ada tetap null; tidak diisi dari template provider.

Selesai ketika: tiga contoh dokumen menghasilkan daftar claim yang bisa dikoreksi dan ditelusuri; kegagalan parser terlihat; analisis menggunakan revision hasil review.

### M2 — Evidence retrieval dan kalkulator

- Buat Tool Gateway dengan input/output validation, izin per role, sumber/domain yang disetujui, quota, timeout, cache, dan logging teredaksi.
- Pilih indikator BPS untuk demo berdasarkan kode wilayah, periode, unit dan ketersediaan aktual. Verifikasi dokumentasi/akses API saat implementasi; jangan menganggap dataset tertentu tersedia.
- Tambah sumber resmi upah/regulasi yang relevan dan scoped official-source retrieval; BI hanya bila relevan dengan use case.
- Simpan snapshot provenance; data tidak cocok wilayah/periode, stale, conflicting, dan kegagalan akses menjadi status eksplisit.
- Pisahkan cache sumber publik dari dokumen privat; data classification menentukan payload yang boleh dikirim ke tool/model.
- Buat kalkulator contribution margin, gross margin, break-even units dan cost sensitivity. Validasi basis waktu, unit, pembagi nol, margin negatif, missing inputs dan pembulatan.

Selesai ketika: satu indikator dapat ditelusuri ke sumber, wilayah, periode dan unit; unavailable tidak berubah menjadi angka; hitungan dapat direproduksi dari input tersimpan. Jika akses live belum tersedia, demo berlabel snapshot; gerbang integrasi live tetap belum lulus.

### M3 — Orchestrator dan empat specialist

- Tambah handler job bisnis memakai lease, retry, fencing token dan idempotent persistence; retry tidak menggandakan finding atau tool result.
- Market: kesesuaian indikator/segmentasi dan klaim demand; jangan memakai upah minimum sebagai pengukuran langsung daya beli.
- Finance: panggil kalkulator, tafsirkan hasil dengan asumsi eksplisit; angka laporan berasal dari calculation output.
- Legal: identifikasi pertanyaan regulasi dan sumber yang perlu diperiksa reviewer.
- Risk: baca claim, evidence, calculation dan peer findings; cari kontradiksi, unsupported assumption dan prioritas validasi.
- Jalankan tugas independen secara paralel sesuai budget; tugas dengan dependency menunggu hasil yang diperlukan.
- Maksimum dua putaran cross-review; disagreement disimpan beserta sumbernya, tanpa voting yang menghapus ketidakpastian.
- Provider offline/fixture diberi label test/demo. Kegagalan LLM live menghasilkan failed/partial, bukan fallback template yang ditampilkan sebagai hasil terverifikasi.
- Simpan trace terstruktur berupa tool, sumber, keputusan validasi dan ringkasan alasan; tidak memerlukan penyimpanan penalaran internal model.

Selesai ketika: seluruh finding memenuhi schema dan referential integrity, satu specialist gagal tetap terlihat sebagai partial, budget/timeout menghentikan run secara terkontrol, dan konflik kesimpulan tetap muncul.

### M4 — Findings dashboard, laporan, export

- Bangun layar Assumption Review, Analysis Live dan Findings Dashboard memakai shell/auth/query/SSE yang ada.
- Filter severity/category/status; detail finding membuka claim, evidence, confidence rationale, hitungan dan next validation.
- Report Agent hanya membaca validated finding registry. Finding unresolved tetap boleh dilaporkan dengan label unresolved, bukan dianggap verified.
- Hasil report memuat delapan bagian PRD, termasuk contradictions, scenario impact, validation tasks dan limitations. Sebelum scenario dijalankan, bagian scenario menyatakan belum diuji.
- Tambah HTML download atau DOCX dengan citation/calculation appendix; PDF menyusul bila diperlukan.
- Ringkasan usage menampilkan token, tool calls, latency, model/version; biaya unknown jika harga provider belum dikonfigurasi.

Selesai ketika: finding utama punya jejak `claim → evidence/calculation → recommendation`; export sesuai snapshot dan dapat diunduh hanya pemilik project.

### M5 — Scenario Lab / Chaos Injection

- Dukung minimal satu template end-to-end untuk MVP: competitor price cut, dengan magnitude/region/duration dan asumsi respons eksplisit.
- Pisahkan competitor price dari own selling price. Potongan harga kompetitor 20% tidak otomatis menurunkan harga/volume bisnis pengguna 20%.
- Minta strategi respons yang dipilih: match price, tetap harga dengan dampak demand unknown, atau perubahan volume yang pengguna nyatakan sebagai asumsi.
- Scenario patch membuat versi baru; dependency map memilih kalkulator/evidence checks/agent checks yang terdampak.
- Jika dependency belum dapat dipastikan, rerun lebih luas dan catat alasannya; jangan membawa finding lama yang sudah tidak relevan sebagai hasil valid.
- Tampilkan before/after, delta hitungan, finding baru/berubah/tetap dan unsupported estimate.

Selesai ketika: baseline tidak berubah, semua delta dapat dihitung ulang, dan dampak yang tidak bisa dihitung tetap unknown.

Contoh fixture sintetis, bukan data pasar: harga sendiri Rp30.000/unit, biaya variabel Rp12.000/unit, fixed cost Rp36.000.000/bulan. Contribution margin Rp18.000/unit dan break-even 2.000 unit/bulan. Jika pengguna memilih respons match price -20%, harga menjadi Rp24.000, margin Rp12.000, break-even 3.000 unit/bulan (+50%). Tanpa asumsi match price, dampak terhadap own price dan volume belum diketahui.

### M6 — Evaluasi, migrasi akhir, dan demo

- Bangun 20–30 dokumen sintetis/berizin dengan blind spot berlabel independen; mulai fixture kecil sejak M1.
- Jalankan A: single LLM; B: single LLM + tools; C: multi-agent + tools dengan source snapshot, model dan anggaran yang sebanding.
- Ukur recall, precision, source-to-claim matching, calculation correctness, false certainty, utility reviewer, latency dan cost.
- Lakukan ablation evidence retrieval dan cross-review. Evaluator tidak hanya mengecek bahwa citation ID ada.
- Uji isolation, classification/egress, prompt injection, tool response invalid, quota, source outage, retry, claim revision conflict dan baseline immutability.
- Update quick demo, landing, navigation, README, PRODUCT, SUMMARY, API contracts, Compose, Docker dan smoke scripts agar tidak masih menjalankan bundle UMKM kebijakan.
- Terapkan canary/feature flag; verifikasi migrasi data dan backup sebelum mengalihkan default. Rollback aplikasi tidak menghapus data analisis baru.

Selesai ketika: checklist PRD terukur; gerbang kandidat recall ≥0,75, precision ≥0,80, grounding ≥0,90, calculation ≥0,98 dan nol kasus critical false certainty dicatat hasil aktualnya. Angka ini target provisional, bukan klaim performa yang sudah dicapai.

## 6. Kontrak API awal

Gunakan namespace bisnis `/api/v1` yang konsisten dengan workspace sekarang. Tambahan bersifat aditif; kontrak legacy `/api/simulations/*` tetap terpisah selama transisi.

| Endpoint | Perilaku |
| --- | --- |
| `POST /api/v1/projects` | Extend/create business intake dengan `product_kind`, tanpa auto graph job |
| `POST /api/v1/projects/{id}/documents` | Upload; kembalikan ingestion job ID dan status |
| `GET /api/v1/projects/{id}/claims` | Daftar claim, locator, status dan revision |
| `PATCH /api/v1/projects/{id}/claims/{claimId}` | Koreksi/approve dengan expected revision |
| `POST /api/v1/projects/{id}/analyses` | Bekukan input dan enqueue; idempotency key |
| `GET /api/v1/analyses/{id}` | Stage, status, summary, usage dan partial failures |
| `GET /api/v1/analyses/{id}/stream` | SSE dengan cursor dan reconnect |
| `GET /api/v1/analyses/{id}/findings` | Finding terstruktur dan filter |
| `GET /api/v1/analyses/{id}/evidence` | Provenance, calculation dan source status |
| `POST /api/v1/analyses/{id}/scenarios` | Buat scenario version dan child analysis |
| `GET /api/v1/analyses/{id}/comparison` | Diff terhadap baseline yang tersimpan |
| `GET /api/v1/analyses/{id}/export` | Output terotorisasi dengan revision |

Halaman target: Projects → Intake → Assumption Review → Analysis Live → Findings → Scenario Lab → Export. Graf agent/claim opsional; layar temuan tetap berguna tanpa visualisasi graf.

## 7. Batas MVP dan urutan pengerjaan

P0 mencakup claim review, evidence resmi terbatas, empat specialist, validasi hitungan, disagreement, laporan downloadable, satu scenario, trace/usage, dan batas akses/data. CSV/DuckDB sejuta baris, ERP/CRM, persona konsumen, graf animasi/Nerve Center, skor kelayakan dan PDF khusus tidak menjadi syarat jalur pertama.

Urutan dependensi: `M0 → M1 → M2 → M3 → M4 → M5 → M6`. Kalkulator dan adapter evidence di M2 bisa dikembangkan independen; UI dapat memakai kontrak fixture setelah M0. Pengujian domain dan fixture dimulai pada milestone terkait, bukan ditunda sampai M6.

Paket pekerjaan pertama yang disarankan: M0 dan M1 sampai alur **buat project bisnis → upload → claim berjejak sumber → koreksi dan approve** selesai. Ini memberi fondasi yang bisa direview sebelum biaya integrasi agent dan sumber eksternal bertambah.

Keputusan lanjutan yang belum menghalangi fondasi: provider/model dan region pemrosesan live, shortlist indikator BPS, anggaran per analysis, reviewer dataset, serta kebutuhan data lama setelah rollout. Gunakan konfigurasi dan antarmuka adapter agar pilihan ini tidak mengunci seluruh arsitektur.

Dokumen ini tidak menetapkan estimasi kalender: kapasitas tim, akses provider dan ketersediaan sumber belum diketahui. Milestone dinilai dari hasil dan kriteria selesai di atas.

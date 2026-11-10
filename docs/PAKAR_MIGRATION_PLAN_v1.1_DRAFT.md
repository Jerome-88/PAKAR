# PAKAR — rencana migrasi berdasarkan usulan PRD v1.1

Tanggal rencana: 27 Oktober 2026. Eksekusi disetujui pengguna dan implementasi MVP sedang berjalan. Status aktual serta batas verifikasi dicatat di [implementation status](PAKAR_IMPLEMENTATION_STATUS.md); tabel di bawah tetap merupakan kriteria penerimaan, bukan klaim seluruh gate sudah lulus.

Sumber utama: [usulan revisi v1.1](PAKAR_PRD_REVISION_v1.1.md), melengkapi `PAKAR_PRD_v1.0.docx`. Dokumen ini mengganti arah arsitektur dalam [rencana berbasis v1.0](PAKAR_MIGRATION_PLAN.md) jika usulan v1.1 dijadikan acuan. Rencana lama tetap disimpan sebagai riwayat, bukan instruksi implementasi yang dijalankan bersamaan.

## 1. Penilaian arah revisi

Revisi v1.1 mengembalikan simulasi stakeholder sebagai kemampuan inti. PAKAR memiliki dua lapisan yang saling melengkapi:

1. **Simulation personas** mengeksplorasi kemungkinan respons, kepentingan, konflik dan dampak berantai.
2. **Analytical agents** memeriksa asumsi, mencari evidence, menghitung metrik, dan menilai hipotesis hasil simulasi.

Keunggulan yang perlu dibuktikan adalah tambahan temuan berguna dari interaksi stakeholder dibanding analisis dokumen dan specialist saja. Jumlah persona, panjang percakapan atau intensitas konflik bukan ukuran keberhasilan produk.

Istilah “Multi-Agent Swarm Intelligence” dapat menjadi positioning, tetapi spesifikasi teknis tetap harus menjelaskan penjadwalan, perubahan state, dependency, validasi dan stopping criteria yang benar-benar diimplementasikan.

## 2. Keputusan rencana lama yang dibatalkan atau dipertahankan

| Keputusan v1.0 | Arah v1.1 |
| --- | --- |
| Persona generator diganti specialist | Pertahankan persona generator dan tambahkan specialist sebagai lapisan terpisah |
| OASIS keluar dari jalur utama | Pertahankan dan adaptasi OASIS pada jalur simulasi P0 |
| Graf dan timeline hanya opsional | Graf hubungan dasar dan timeline audit masuk P0; visualisasi lanjutan tetap P1 |
| Blind spot bertumpu pada dokumen/evidence | Tambah stakeholder, interaction-based dan scenario-based findings |
| Chaos terutama kalkulasi ulang | Tambah respons persona, perubahan state/hubungan dan evaluasi specialist |
| Evaluasi multi-agent versus single LLM | Tambah ablation tanpa persona serta evaluasi stakeholder discovery |
| Reuse auth, storage, worker, parsing | Tetap berlaku |
| Claim/evidence registry dan kalkulator deterministik | Tetap berlaku |
| Baseline immutable, scenario versioned | Tetap berlaku |
| Unknown eksplisit, biaya terukur, akses data dibatasi | Tetap berlaku |

Ketentuan v1.0 yang tidak diubah revisi tetap berlaku, termasuk upload berjejak sumber, koreksi claim, export, missing-data handling, privasi dan non-goals. Scoring kelayakan numerik tetap P1 sampai rubrik disepakati. “Business risk scoring” di REV-07 diterapkan sebagai severity beralasan pada P0.

## 3. Alur produk yang direvisi

```text
Business intake + dokumen
  → Ekstraksi context dan claim
  → Stakeholder discovery + evidence awal
  → Persona generation + relationship graph
  → Human review: claim, stakeholder, persona, konteks yang dibagikan
  → Freeze input dan konfigurasi run
  → Pemeriksaan specialist awal + simulasi interaksi stakeholder
  → Ekstraksi kandidat blind spot dari event/state
  → Validasi specialist + cross-review terbatas
  → Findings dan report dengan evidence, hipotesis, calculation trail
  → Chaos scenario versi baru → interaksi dan kalkulasi ulang → comparison
```

Evidence awal membantu membentuk konteks persona; evidence lanjutan dapat dicari untuk menguji hipotesis yang muncul. Jika run menemukan stakeholder baru setelah review, simpan sebagai kandidat untuk ditinjau atau versi berikutnya. Penambahan persona diam-diam di tengah run tidak menjadi default MVP.

## 4. Arsitektur dan pemetaan repository aktual

```text
React → FastAPI/Auth → Business workspace + registry
                         ↓
                 Workflow Orchestrator / worker
                   ├─ Analytical layer → Tool Gateway
                   │                    ├─ BPS / approved official sources
                   │                    └─ Typed deterministic calculators
                   └─ Simulation layer → Business simulation adapter
                                         → OASIS / existing runtime
                                         → persona state, memory, events
                         ↓
              Candidate findings → Validator → Report
                         ↓
              SSE / timeline / graph / scenario comparison
```

| Kode sekarang | Reuse dan perubahan |
| --- | --- |
| `app/auth.py`, middleware, `storage.py` | Pertahankan; perluas ownership dan data classification ke resource baru |
| `app/documents.py` | Pertahankan chunk/locator; tambah tabel DOCX dan kegagalan ekstraksi yang eksplisit |
| `app/service.py`, `worker.py`, `repository.py` | Pertahankan queue/lease/heartbeat/retry; pisahkan handler context/discovery/personas/simulation/validation/report |
| `app/providers.py`, `provider_contracts.py` | Reuse provider transport dan validation; tambah schema bisnis dan specialist output |
| `app/oasis_direct.py`, `oasis_direct_bridge.py` | Pertahankan bridge; tambah run isolation, profile revision, runtime identity, business event projection dan shock config |
| `oasis_engine_runtime/app/services/oasis_profile_generator.py` | Adaptasi profil sosial menjadi profil stakeholder bisnis; pertahankan serializer yang dibutuhkan runtime |
| `simulation_manager.py`, `simulation_config_generator.py` | Adaptasi permission/context per persona, relationship-based scheduling, budget dan action configuration |
| `simulation_runner.py`, scripts runtime | Pertahankan lifecycle; audit kemampuan business actions, memory, state transitions dan scheduled shock |
| `app/oasis_runtime.py` | Perluas normalisasi event: actor/target, interaction type, source event IDs, before/after state, provenance |
| Graph/Zep services | Reuse relationship/memory; pisahkan source facts dari simulated memory dan namespace tiap run |
| `report_agent.py` dan jalur report backend | Reuse mekanisme/progres; report final membaca registry tervalidasi dengan status epistemik eksplisit |
| `PersonaStudio`, `ScenarioBuilder`, `SimulationMonitor` | Reuse pola UI/control; domain bisnis, review persona, timeline dan scenario comparison |
| `SimulationWorkflowPage`, `WorkflowComponents` | Reuse komponen relevan; pecah workflow bisnis agar tidak menambah monolit halaman lama |
| `CitationDrawer`, provenance, SSE hooks | Perluas untuk source eksternal, interaction chain, state delta dan calculation |

Batas reuse yang sudah terlihat dari kode:

- `normalize_environment()` berorientasi profil Twitter/Reddit. `normalize_action()` saat ini membawa stance/concern/citation profil; itu belum membuktikan perubahan keputusan atau dukungan evidence terhadap isi aksi baru.
- Aksi runtime yang terlihat mencakup post, comment, follow, like dan sejenisnya. Negosiasi, penawaran harga, perubahan syarat pembayaran dan keputusan supplier membutuhkan kontrak bisnis tambahan. Jangan hanya mengganti label post menjadi transaksi bisnis.
- IPC yang diperiksa mendefinisikan interview, batch interview dan close environment. Perintah inject shock atau fork checkpoint belum tersedia pada kontrak itu.
- `start_simulation()` menggunakan folder runtime dan membersihkan log aksi saat memulai ulang. Scenario tidak boleh berbagi folder/memory yang dapat menimpa baseline.
- Persona saat ini terutama berasal dari graph entities. Stakeholder tersembunyi membutuhkan discovery eksplisit, alasan inklusi dan human review; tidak otomatis tersedia karena generator profil sudah ada.
- Queue dan resource dokumen/citation sekarang banyak terikat `simulation_id`. Tambahkan relasi business analysis/run secara aditif; jangan membuat specialist harus menyamar sebagai social persona.

## 5. Kontrak data yang perlu ditambah

| Entitas | Field dan aturan utama |
| --- | --- |
| BusinessContext | Industry, region, customer segment, business model, value proposition, decision question, constraints; sumber masing-masing field |
| ClaimRevision | Quote, normalized text, variable/value/unit/period, source pointer, classification, approval dan revision |
| StakeholderCandidate | Direct/indirect/hidden, inclusion rationale, discovery origin, source links, reviewer decision |
| PersonaRevision | Stakeholder ID, role, goals, motivations, constraints, knowledge scope, interests, relationship IDs, provenance per atribut, active/reviewed |
| Relationship | Source/target, type, proposed mechanism, evidence atau assumption references, revision |
| AnalysisRun | Frozen context/claim/persona/evidence snapshot, specialist config, simulation config, budgets, model/prompt/tool versions |
| SimulationRun | Analysis ID, external runtime ID, initial snapshot, event cursor, status, stop reason, seed, memory namespace, runtime artifact IDs |
| PersonaState | Simulation ID, persona revision, positions/decisions/resources yang didefinisikan, state version dan last event ID |
| InteractionEvent | Actor, target, action, payload, visibility/recipients, causal parent events, state-before/after references, round/time, validation status |
| EvidenceSnapshot | Official/public/internal source, URL/dataset, region/period/unit, retrieved time/hash, applicability dan evidence status |
| CalculationRun | Formula version, typed inputs, claim references, deterministic outputs, units, missingness dan rounding |
| Finding | Category, severity, discoverer, claim/missing-assumption/stakeholder references, event chain, evidence gaps, calculation refs, confidence rationale dan next validation |
| ScenarioVersion | Baseline ID, input snapshot, shock type/magnitude/region/duration/effective round, child run IDs dan comparison |

Persona dapat memiliki atribut campuran: peran didukung dokumen, tujuan dari pengguna, motivasi sintetis. Label provenance harus tersedia per atribut, dengan ringkasan di level persona. Label “data-backed” pada profil tidak berarti tindakan yang dihasilkan persona adalah fakta.

Pisahkan empat hal: origin temuan (`document`, `evidence`, `simulation`, `scenario`), evidence status, finding validation status, serta severity. Risiko high tetap dapat berstatus unvalidated; banyak persona yang setuju tidak menaikkan bukti empirisnya.

Finding emergen tidak wajib merujuk claim eksplisit dalam proposal. Ia harus bisa menunjuk missing assumption atau stakeholder/interaction chain yang melahirkannya. Ini merevisi aturan lama yang terlalu berpusat pada claim dokumen.

## 6. Batas antara hipotesis dan fakta

- Simulation event selalu berstatus simulated, termasuk ketika persona memakai data resmi sebagai konteks.
- Kutipan resmi harus cocok dengan klaim yang didukung: indikator biaya tidak memverifikasi bahwa supplier nyata akan membatalkan kontrak.
- Finding hasil simulasi dapat memiliki mekanisme yang masuk akal dan sebagian evidence pendukung sambil tetap berstatus hypothesis/needs validation.
- Persetujuan specialist, frekuensi kemunculan event, atau ingestion ke Zep tidak mengubah simulated event menjadi observed evidence.
- Memory simulasi dan knowledge graph diberi run namespace dan origin tag. Retrieval tidak boleh menggunakan narasi sintetis sebagai konfirmasi independen atas narasi itu sendiri.
- Angka dampak hanya ditampilkan sebagai hasil kalkulator dengan asumsi yang jelas. Pergeseran stance/persona bukan estimasi market share atau persentase demand nyata.
- Specialist hanya menerima ringkasan/event relevan. Persona menerima knowledge scope terbatas, bukan seluruh dokumen atau data internal.

## 7. Perilaku simulasi MVP yang perlu dibuktikan lebih awal

Sebelum membangun semua layar, buat technical spike satu alur bisnis:

`Shock biaya supplier → persona supplier mengubah usulan syarat → persona operator merespons → persona customer menanggapi perubahan penawaran → specialist memeriksa risiko margin dan asumsi demand`.

Spike harus menunjukkan penerimaan informasi, perubahan state yang eksplisit dan event causal links. Dialog yang hanya menyatakan perubahan tanpa state yang dicatat belum cukup.

Adapter aksi memvalidasi actor/target, visibility, tipe aksi, state version dan batas resource jika ada. Usulan negosiasi tidak langsung menjadi kontrak disepakati. Penolakan atau invalid action dicatat; server menerapkan transisi sah. Jangan memberi LLM hak menulis state arbitrer.

Jika OASIS tidak menyediakan aksi bisnis secara native, pertahankan runtime scheduling/memory yang berguna dan implementasikan business action adapter serta state reducer di sisi backend/runtime. Cakupan klaim produk dibatasi pada interaksi yang benar-benar diuji. Bila spike menunjukkan keterbatasan mendasar, catat gap terhadap REV-04 sebelum memperluas MVP.

Rekomendasi konfigurasi pilot awal, bukan batas desain atau jaminan kualitas: 6–10 persona, 4–6 ronde interaksi, maksimum dua putaran specialist cross-review, satu crisis template, dan budget keras per run. Jumlah persona configurable di bawah cap deployment. Batas ronde simulasi berbeda dari batas putaran cross-review.

Runtime online tetap memakai OASIS dan dependensinya. Mode fixture/deterministik dipertahankan untuk CI/demo berlabel dan tidak dipresentasikan sebagai keberhasilan simulasi live.

## 8. Chaos Injection dan comparison yang sah

Kontrak P0 yang diusulkan: baseline dan scenario merupakan run terpisah dari initial snapshot yang sama, dengan shock terjadwal pada ronde yang ditentukan. Scenario run melanjutkan interaksi setelah menerima shock; baseline tidak dimutasi.

Ini berbeda dari fork proses baseline yang sedang berjalan. Live fork/checkpoint menjadi kemampuan lanjutan kecuali secara eksplisit dibutuhkan untuk acceptance; kontrak IPC saat ini belum menjaminnya.

Simpan profile/graph/evidence/model versions, initial state, shock payload dan seed. Seed yang sama tidak menjamin output LLM identik; comparison perilaku adalah hasil dua simulasi kondisional, bukan estimasi kausal dunia nyata. Untuk evaluasi, gunakan pengulangan seed/run yang ditetapkan sebelumnya dan laporkan variasinya.

Scenario dependency mencakup relasi stakeholder, scope informasi, calculation inputs dan finding references. Bila tidak yakin dampaknya lokal, rerun ekosistem kecil secara penuh; jangan mengklaim unaffected finding tetap valid tanpa alasan. Output membedakan:

- Delta matematis yang dapat direproduksi.
- Perubahan state/relasi yang diamati dalam run sintetis.
- Hipotesis risiko baru dan evidence gaps.
- Bagian tidak berubah serta bagian yang belum dapat dipastikan.

Contoh: competitor price cut 20% hanya mengubah harga kompetitor. Own price/volume berubah bila ada asumsi respons eksplisit. Jika persona mengusulkan match price, itu candidate strategy; calculation ditandai conditional sampai strategi dipilih atau dijadikan skenario terpisah.

## 9. Roadmap revisi dan gerbang milestone

| Milestone | Hasil utama | Kriteria selesai |
| --- | --- | --- |
| R0 — Kontrak dan simulation spike | State machine, schema persona/event/finding, business adapter, capability audit OASIS | Minimal dua peran saling memengaruhi dengan perubahan state dan causal links; keterbatasan terdokumentasi |
| R1 — Intake/context/claim | Metadata bisnis, tabel dokumen, claim revision dan human review | Tiga dokumen contoh memiliki trace sumber; missing tetap unknown; parser failure terlihat |
| R2 — Stakeholder/persona review | Discovery langsung/tidak langsung/hidden, dedup, profil, knowledge scope, graf dasar | Kandidat hidden stakeholder relevan muncul pada fixture yang sengaja memiliki omission; pengguna bisa edit/tambah/nonaktifkan |
| R3 — Evidence dan specialist | Minimal satu official-source adapter, provenance, kalkulator, empat specialist, Tool Gateway | Source cocok region/period/unit; calculation repeatable; invalid tool output tidak verified |
| R4 — Ecosystem simulation | Approved persona snapshot, scheduling, memory/state, timeline, hard budgets | Event trace lengkap, state isolation antar-run, stopping reason dan partial failures terlihat |
| R5 — Emergent findings/report | Event-to-finding extraction, evidence review, disagreement, severity, downloadable report | Risiko dokumen dan interaksi dapat ditelusuri; hypothesis tidak berubah menjadi fact; report punya next validation |
| R6 — Chaos/comparison | Shock terjadwal, child run, response persona, deterministic deltas, comparison | Baseline immutable; minimal satu state response sesudah shock dan satu delta hitungan sah jika input mendukung |
| R7 — Benchmark/rollout | Dataset, baseline/ablation, latency/cost, safeguards, docs dan demo | Tiga dimensi evaluasi dilaporkan; checklist P0 lulus dengan batas yang eksplisit |

R1/R2 boleh dimulai setelah kontrak R0 stabil; hasil spike harus tersedia sebelum investasi besar pada simulation UX. R3 dan R4 dapat berjalan dengan kontrak bersama; R5 menggabungkan keduanya. Tes dan anotasi fixture dimulai pada milestone terkait.

## 10. UI dan API yang terdampak

Alur layar: Projects → Business Intake → Context & Assumption Review → Stakeholder/Persona Review → Analysis & Simulation Live → Findings → Scenario Lab → Report/Export.

P0 graf dasar membuka profil/relasi, sumber dan event penyebab. Timeline menunjukkan actor/target, tindakan dan state delta. P1 baru menambahkan animasi Nerve Center dan visualisasi relasi lanjutan. Dashboard tetap membedakan factual evidence, conditional calculation dan simulation hypotheses secara tekstual.

Resource bisnis menggunakan project sebagai parent; analysis memiliki specialist runs dan simulation runs. Tambahan API di atas rancangan v1.0:

| Endpoint usulan | Tujuan |
| --- | --- |
| `POST /api/v1/projects/{id}/stakeholder-discovery` | Enqueue discovery dari context/claim revision |
| `GET /api/v1/projects/{id}/stakeholders` | Kandidat, provenance dan review status |
| `POST /api/v1/projects/{id}/personas` | Tambah persona user-supplied |
| `PATCH /api/v1/projects/{id}/personas/{personaId}` | Review/edit/deactivate dengan expected revision |
| `POST /api/v1/projects/{id}/analyses` | Freeze approved inputs; mulai specialist + simulation workflow |
| `GET /api/v1/analyses/{id}/simulation/events` | Cursor event/state trace |
| `GET /api/v1/analyses/{id}/simulation/graph` | Relasi pada snapshot/round tertentu |
| `POST /api/v1/analyses/{id}/scenarios` | Buat child scenario dengan typed shock |
| `GET /api/v1/analyses/{id}/comparison` | Findings, state dan calculation diff |

Endpoint claim, evidence, findings, SSE, export dan authentication dari rencana v1.0 tetap diperlukan. Runtime IDs internal dipetakan ke business run dan tidak menjadi satu-satunya resource identifier publik.

## 11. Evaluasi untuk membuktikan manfaat simulasi

Pakai dokumen sintetis/berizin dengan referensi stakeholder dan risiko yang dianotasi manusia. Pisahkan development set dari held-out set; gunakan evaluator yang tidak hanya menyetujui output model.

Desain benchmark:

- A: single LLM dengan dokumen.
- B: single LLM dengan tools/evidence yang sama.
- C: analytical multi-agent tanpa simulation personas.
- D: PAKAR lengkap dengan simulation personas dan analytical agents.

Perbandingan utama nilai tambah simulasi adalah C versus D. Samakan dokumen, source snapshots, akses tools dan batas biaya keseluruhan sejauh memungkinkan; laporkan konsumsi aktual dan perbedaan konfigurasi. Jangan memberi D budget tak terbatas lalu mengatribusikan keunggulannya hanya pada arsitektur.

Ukuran stakeholder discovery: relevansi, cakupan terhadap referensi, candidate hidden stakeholder yang diterima reviewer, keragaman dan duplicate rate. Daftar referensi tidak dianggap mencakup seluruh stakeholder dunia nyata.

Ukuran blind spot: precision/recall risiko berlabel, tambahan temuan yang diterima reviewer, grounding sesuai isi sumber, unsupported factual assertions dan critical false certainty. Hipotesis yang diberi label benar tidak otomatis dihitung sebagai hallucination atau true finding; nilai relevansi dan evidence gap secara terpisah.

Ukuran simulasi: state transition validity, event-to-finding trace completeness, respons pada controlled shock, ketahanan terhadap perubahan urutan/seed, utility reviewer, latency/token/cost. Uji metamorphic terarah hanya pada aturan yang memang dijamin, misalnya own price tetap bila shock hanya mengubah competitor price dan tidak ada respons strategi; jangan mengharuskan reaksi perilaku LLM selalu monoton.

Target kualitas final mengikuti revisi: ditetapkan sebelum benchmark dan dilaporkan sebagai pengukuran MVP. Angka provisional v1.0 tetap dapat menjadi masukan, bukan gate final yang sudah disepakati. Acceptance hidden stakeholder diuji pada fixture yang memang memiliki stakeholder terlewat, bukan kewajiban mengarang hidden stakeholder di setiap proposal.

## 12. Hal yang perlu diperjelas dalam PRD usulan

1. Definisikan arti simulation interaction: percakapan hipotetis, keputusan terstruktur, atau perubahan resource bisnis. Rekomendasi P0: keputusan terstruktur terbatas dengan state delta, tanpa mengklaim simulator ekonomi lengkap.
2. Tegaskan semantik Chaos P0 sebagai separate-run scheduled shock; live checkpoint fork adalah requirement berbeda.
3. Definisikan confidence sebagai dukungan dan keterbatasan evidence, bukan probabilitas kejadian nyata dari konsensus persona.
4. Pisahkan penemuan stakeholder, pembentukan persona dan peran specialist pada data model serta metrik; jumlahnya tidak saling membatasi.
5. Tetapkan budget/cap dan stopping rules deployment tanpa mengunci persona ke empat atau menjanjikan skala tanpa batas.
6. Revisi aturan finding-to-claim pada v1.0 agar stakeholder dan interaction finding yang baru muncul dapat dilaporkan dengan provenance yang sah.
7. Tetapkan minimum graf/timeline P0 versus enhanced Nerve Center P1 supaya scope visual tidak ambigu.

PRD DOCX asli tetap menjadi sumber historis. Implementasi, hasil pengujian, dan release gates yang belum lulus dicatat terpisah di [implementation status](PAKAR_IMPLEMENTATION_STATUS.md).

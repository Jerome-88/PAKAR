# Hasil lanjutan PAKAR — 30 Oktober 2026

Status: implementasi dan pasangan live selesai. [Plan](PAKAR_FOLLOWUP_PLAN_2026-10-30.md).

## Penjadwalan specialist

Run sebelumnya memberi Risk hanya 1,337 detik setelah review Legal memerlukan
89,164 detik. Prompt turut bertambah dari peer findings yang terus menumpuk.

Analisis baru menyimpan `review_policy=paired-v2`, prompt version `pakar-1.2` dan
`review_concurrency` dalam snapshot. Nilai concurrency dapat 1 atau 2; default
baru **1** untuk transport development yang konservatif. Konteks tetap dibekukan
per gelombang Market/Finance lalu Legal/Risk. Hasil digabung dalam urutan role
tetap, bukan urutan selesai. Reviewer dalam gelombang sama tidak saling melihat
hasil baru; gelombang berikutnya melihat hasil tervalidasi sebelumnya.

Runtime mendapat sisa budget setelah cadangan review 40% (maksimal 120 detik).
Budget per request mempertimbangkan gelombang dan antrean transport, sehingga
role terakhir tidak hanya mendapat sisa dari satu panggilan awal yang lama.
Deadline total tetap 300 detik pada smoke test; model Nemo dan reducer tidak diganti.

Konteks menghapus duplikasi plumbing registry/observasi mentah, mempertahankan
kutipan/claim, ID, nilai/unit/status, causal parents dan state changes. Window
35 claim / 12 event / 12 peer tetap eksplisit. Schema hanya menawarkan ID record
yang benar-benar disuplai. Maksimum satu tambahan finding dan dua disagreements
per specialist, output 1.100 token. Perubahan ini tradeoff scope output, bukan
bukti kualitas analisis meningkat. Peer disagreements dan ketidakpastian dipertahankan.

Pada snapshot scenario lama, payload sebelum schema turun sekitar 18.471 menjadi
13.911 byte untuk Risk. Token reservation bersama memakai lock. Salah satu
request tidak dapat memakai sisa token yang sudah direservasi request lain.

Baseline lama tidak diubah. Scenario mewarisi policy/config baseline; snapshot
paired lama tanpa field concurrency tetap memakai perilaku dua request, sedangkan
snapshot sequential-v1 tetap melalui jalur lama.

## BPS: konflik berhasil diidentifikasi

Publikasi resmi berhasil diperoleh lewat endpoint publication BPS. Tabel 2.1,
halaman cetak 15 / PDF 31, menunjukkan **2.794.485 Rupiah** untuk DKI Jakarta 2024,
sedangkan observasi API yang dikurasi memberi **2.764.456 Rupiah**. Periode survei
dan definisi agregat masih perlu klarifikasi sebelum menyimpulkan salah satu keliru.

Evidence baru menjadi **CONFLICTING**, scalar `value=null`; nilai mentah API dan
nilai publikasi, URL, checksum dan lokasi tabel dipertahankan. Reason memuat kedua
angka; sumber publikasi dapat dibuka dari laporan. Tidak ada penggantian angka
diam-diam atau promosi claim bisnis ke VERIFIED. Snapshot lama tetap PARTIAL
sebagaimana evidence yang tersedia saat run lama.

Detail dan provenance: [rekonsiliasi BPS](evidence/bps-dki-2024-reconciliation.md).

## Pemulihan worker

Pengawas parent dimulai sebelum import SDK/runtime berat. Ketika worker induk
mati, proses anak ikut keluar, termasuk ketika SDK sinkron sedang menunggu.
Windows memakai handle proses asli; POSIX memeriksa reparenting. Ini menghentikan
proses lokal/dispatch berikutnya, bukan jaminan membatalkan billing upstream
untuk request yang sudah diterima provider.

Tes mengakhiri worker controller sungguhan dengan request aktif ke HTTP provider
lokal. Proses anak keluar dalam batas tiga detik; setelah lease dibuat expired,
job/analysis live menjadi failed, worker pengganti tidak mengambil ulang job,
dan token stale worker tidak boleh publish/renew. Hanya satu request tercatat.

Retensi/penghapusan tabel dan storage bisnis belum diimplementasikan melalui
lifecycle legacy. Gap dan urutan implementasi dicatat di
[business retention gaps](BUSINESS_RETENTION_GAPS.md). Tidak ada data nyata dihapus.

## Verifikasi dan observasi live

- Suite backend final: **217 passed, 2 skipped** dalam 186,38 detik. Setelah
  penandaan disagreement terkait temuan tertahan, suite terdampak aritmetika,
  API dan report diulang: **25 passed**. Dua skip berasal dari probe lokasi
  runtime legacy dan privilege symlink Windows; runtime business diuji terpisah.
- Integrasi empat reviewer memakai SDK asli dengan HTTP provider lokal lulus,
  termasuk deterministic merge, konflik evidence, token ledger, cancellation dan
  bounded concurrency. Ini tidak memakai inference berbayar.
- Browser fixture empat persona / dua ronde: **1 passed**, real API/PostgreSQL,
  laporan delapan bagian, source-event navigation, scenario, desktop/mobile.
  Diulang setelah restart backend final: **1 passed** (12,0 detik), tanpa LLM.
  Export live yang diregenerasi juga lolos delapan bagian, absennya artikel/tugas
  finding tertahan, peringatan pada disagreement terkait dan containment mobile.
  Screenshot akhir `published-{baseline,scenario}-{desktop,mobile}.png`.
  Kode frontend tidak berubah; 65 unit tests, ESLint dan build sebelumnya tetap
  berlaku. `git diff --check` lulus; tidak ada konfigurasi linter Python di proyek.
- Uji live dua request aktif: `analysis_5692d5d49b35410a946c`, **partial**, 106,372
  detik, 8 aksi diterima / 0 ditolak. Finance selesai; tiga review lain mendapat
  ExternalCallError cepat. Tidak ada scenario dari run tersebut. Jenis upstream
  error lama tidak tersimpan, sehingga penyebabnya tidak ditebak sebagai rate limit.
- Satu request diagnostik Market dengan schema yang sama kemudian selesai dalam
  5,097 detik. Finance yang berhasil diketahui memakai Parasail lewat API generation.
  Ini menunjukkan kompatibilitas request, bukan bukti bahwa transport selalu stabil.
- Failure diagnostics baru hanya menyimpan tipe worker, HTTP status dan kategori/
  keyword allowlist. Raw message, header, credential, URL dan prompt tidak diekspor.
- Verifikasi live satu request aktif selesai sebagai perubahan konfigurasi
  yang terkontrol, bukan retry otomatis. Semua run gagal/partial tetap disimpan.

### Pasangan live akhir

| Pengukuran | Baseline | Scenario harga turun 20% |
|---|---:|---:|
| Analysis ID | `analysis_c751c17a692640b39a6b` | `analysis_ab708c6916804bce82d3` |
| Status eksekusi | completed | completed |
| Waktu (detik) | 137,460 | 102,135 |
| Persona / ronde | 4 / 2 | 4 / 2 |
| Aksi diterima / ditolak | 8 / 0 | 8 / 0 |
| Specialist selesai | 4/4, termasuk Risk | 4/4, termasuk Risk |
| Token provider | 36.539 | 39.814 |
| Biaya provider (USD), 12/12 calls | 0,000939366 | 0,001023732 |
| Harga / biaya variabel (Rp/unit) | 30.000 / 15.000 | 24.000 / 15.000 |
| Margin kondisional (Rp/unit) | 15.000 | 9.000 |
| BEP kondisional (unit/bulan) | 2.400 | 4.000 |
| Profit / demand nyata | unknown | unknown |
| Findings mentah / dipublikasikan | 7 / 6 | 9 / 9 |

Kedua laporan memiliki delapan bagian. Perbandingan ini mengikuti input, syarat
supplier sintetis dan strategi match-price; bukan forecast penjualan nyata.
Pemeriksaan hash dan kesamaan registry sebelum/sesudah regenerasi publikasi lulus.
Laporan HTML/JSON, perbandingan dan screenshots berada di audit lokal subfolder
`serial/`. Browser desktop/mobile berhasil, tanpa overflow horizontal halaman.

### Klaim aritmetika yang ditahan

Baseline mentah berisi finding Market yang menyatakan Rp30.000 di bawah Rp12.000.
Pemeriksaan `explicit-money-comparison-v1` menahan finding tersebut dari daftar
temuan, ringkasan dan tugas validasi. Catatan disagreement yang merujuk ID/judul
finding itu diberi peringatan; teks asal dan author tetap dipertahankan. Seluruh
registry tersimpan tetap utuh untuk audit. Tidak ada inference tambahan untuk
meregenerasi publikasi.

Angka biaya Rp12.000 di teks model juga berbeda dari biaya hasil negosiasi
Rp15.000; guard ini hanya membuktikan perbandingan literalnya salah. Ia tidak
memverifikasi seluruh angka terhadap konteks. Format ambigu, negasi, kondisi,
mata uang dan basis waktu/unit berbeda dilewati agar tidak ditebak sebagai error.
Karena guard ditambahkan setelah run selesai, status completed menyatakan
eksekusi selesai, bukan setiap temuan benar. Run berikutnya menolak kandidat
finding dengan perbandingan nominal eksplisit yang salah sebelum admission.

## Budget

Plafon **USD 0,02 kumulatif** sejak preflight awal 30 Oktober, tidak direset.
Sebelum konfigurasi serial, key-usage delta yang teramati USD 0,002366713,
termasuk run sebelumnya, uji dua request aktif dan satu diagnostic request.
Pemeriksaan read-only **2026-10-30 08:31:25 UTC** setelah kedua run mencatat
delta kumulatif **USD 0,004329811** sejak preflight awal, di bawah plafon.
Sisa limit key teramati USD 0,194127078. Ini pengamatan saat pemeriksaan, bukan
jaminan final settlement untuk request terputus/failed yang biaya lengkapnya
tidak tersedia. Dua run serial sendiri melaporkan USD 0,001963098.
Reservasi sebelum live beserta headroom tetap USD 0,009. Model/price ceiling,
limit akun/key dan ketentuan no automatic paid retry tidak dinaikkan.

Audit lokal: `backend/data/runtime-audit/2026-10-30/followup/`, dengan konfigurasi
serial di subfolder `serial/`. Credential/cookie tidak disimpan bersama bukti.
Scan exact-byte credential pada 45 file audit tidak menemukan kecocokan.

## Berkas implementasi paket ini

- Baru: `backend/app/business/reviews.py`, `backend/app/business/finding_checks.py`,
  `backend/app/child_guard.py`; tes review/integrasi/recovery/failure diagnostics/
  finding checks; plan, hasil, rekonsiliasi BPS dan catatan retention gaps.
- Diperbarui: business `agents.py`, `contracts.py`, `structured.py`, `service.py`,
  `evidence.py`, `budget.py`, `call_worker.py`, `reporting.py`, `api.py`;
  `oasis_direct.py`, `oasis_direct_bridge.py`; isolasi credential di
  `tests/conftest.py`, tes business terkait dan dokumentasi backend/status.
- `.env` lokal hanya menambah metadata publikasi untuk kurasi BPS; secret tetap
  di luar Git. Kode frontend/avatar dan reducer simulasi tidak diubah paket ini.

## Batas klaim

Satu kasus live bukan benchmark independen. Draft tiga kasus belum ground truth;
human business evaluation, ablations, metode/periode BPS dan lifecycle deletion
masih release gates. Empat response specialist yang valid tidak membuktikan
kelayakan usaha, demand nyata atau keunggulan multi-agent.

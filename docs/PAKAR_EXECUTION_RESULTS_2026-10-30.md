# Hasil eksekusi PAKAR — 30 Oktober 2026

Status: paket eksekusi selesai; baseline live completed, scenario live partial.
Rencana: [execution plan](PAKAR_EXECUTION_PLAN_2026-10-30.md).

## Implementasi

- Satu deadline attempt membatasi evidence, interpreter/runtime OASIS dan
  specialist. Fase baru memakai sisa waktu, dengan cadangan finalisasi dua detik
  atau 10% untuk budget pendek.
- Request BPS/specialist memakai subprocess yang dapat dihentikan dan direap;
  startup ikut dihitung. Bridge OASIS tidak lagi mendapat tambahan 30 detik.
  Penulisan stdin tidak boleh menghalangi deadline. Cancellation/kehilangan lease
  menghentikan dispatch atau proses yang ditunggu.
- Runtime CAMEL mencatat panggilan sync/async: persona/role, fase, attempt,
  generation ID, model, durasi, prompt/completion/total token, dan biaya provider
  bila tersedia. Reservasi turut mencakup panggilan internal tambahan.
- Specialist mempertahankan reservasi saat gagal/timeout. Usage agregat memisahkan
  biaya lengkap, subtotal diketahui dan unknown. Audit frontend memakai agregat
  analisis, dengan fallback usage simulasi untuk laporan lama.
- Job live baru hanya satu attempt: kegagalan/worker mati tidak otomatis mengulang
  inference berbayar. Retry fixture dipertahankan.
- `PAKAR_OPENROUTER_MAX_PRICE` membatasi routing: prompt/completion dalam USD
  per sejuta token, request dalam USD per request. Sesi ini memakai 0,03 / 0,03 / 0,
  dengan fallback provider dimatikan. Model dan limit key pengguna tidak diubah.
- Suite tes default mengisolasi kredensial developer; adapter memakai key palsu
  dan provider lokal untuk pemeriksaan tanpa biaya inference.

## BPS DKI Jakarta

Katalog resmi mengidentifikasi domain `3100`, variabel `144`, periode `124`
berlabel **2024**: pengeluaran rata-rata per kapita per bulan menurut golongan
pengeluaran dan kelompok barang. Ini periode terbaru di seri API tersebut saat
diperiksa, bukan klaim bahwa seluruh data BPS terbaru hanya sampai 2024.

Seleksi eksplisit `vervar=9`, `turvar=163`, `turtahun=0`, berlabel total. Nilai
mentah API **2.764.456 Rupiah per kapita per bulan**, tanpa pengali tambahan.
Makanan 1.096.758 + bukan makanan 1.667.698 cocok dengan total API. Ini pemeriksaan
metadata/aritmetika internal, bukan konfirmasi statistik independen.

Evidence tetap **PARTIAL**, claim support **NOT_ASSESSED**. Data historis provinsi
bukan demand atau profit kedai. Pencocokan dengan publikasi/tabel pembanding belum
selesai: halaman publik mendapat 403 dan unduhan PDF melalui pembaca web timeout.
Sampel nasional lama juga masih memerlukan review skala. Tidak ada promosi otomatis
ke VERIFIED.

Adapter memeriksa dimensi, periode, satuan dan nilai finite. Cache mencakup
konfigurasi/seleksi/wilayah. Jakarta tanpa pemetaan eksplisit dan Bandung tetap
UNAVAILABLE, tanpa fallback nasional/DKI.

## Verifikasi offline

- Suite backend lengkap: **184 passed, 2 skipped**. Skip mencakup probe
  integration legacy yang mencari bundled runtime pada lokasi lain dan tes
  symlink Windows tanpa privilege. Business OASIS runtime yang terpasang tetap
  diuji secara nyata terhadap provider HTTP lokal.
- Setelah pengetatan akhir per-panggilan, suite structured/budget **17 passed**.
- Tes mencakup SDK sinkron macet, cancellation, runtime macet sebelum membaca
  stdin besar, reaping proses, deadline API tanpa retry live, metadata BPS tidak
  cocok, cache, dan coverage unknown cost.
- Runtime OASIS/CAMEL terpasang diuji terhadap provider HTTP lokal: empat
  offer/accept, empat panggilan/360 token, biaya unknown karena provider lokal
  memang tidak melaporkan billing.
- Frontend **65 passed**, build TypeScript/Vite dan ESLint lulus. Advisory bundle
  besar yang sudah ada tetap muncul.
- Browser FastAPI/PostgreSQL fixture **1 passed**, kini **empat persona × dua
  ronde**, DKI Jakarta, baseline/scenario, delapan bagian laporan, source navigation,
  ekspor HTML, identitas avatar dan akses mobile. Workflow ini nol inference LLM.
- Tiga kasus sintetis dan rubric disiapkan di [draft evaluasi](evaluation/README.md).
  Anotasi belum ground truth/review independen; benchmark pembanding belum berjalan.

## Biaya sesi

Plafon **USD 0,02**. Pemeriksaan awal key menunjukkan remaining USD 0,198456889.
Tes lama sempat mewarisi `.env`, menimbulkan usage delta USD 0,000161095 sebelum
dihentikan. Ini ikut dihitung dalam plafon; isolasi kredensial tes lalu ditambahkan.

Reservasi sebelum baseline: dua run dengan token-cap masing-masing 100.000,
harga maksimum 0,03 USD/sejuta token, plus 50% headroom = **USD 0,009**.
Unknown cost tidak dianggap nol. Kontrol token/harga ini bukan perubahan hard
spending limit akun atau key.

## Hasil live

Baseline `analysis_1c5e5c6f273d4080b9c2` **completed**, empat persona × dua ronde,
8 aksi diterima / 0 ditolak, empat specialist tanpa failure, 6 kandidat finding.
Durasi **280,173 detik**, di bawah batas 300 detik. Semua 12 panggilan melaporkan
token/biaya: **45.937 token**, biaya provider **USD 0,000870438**.

Input awal harga 30.000 / biaya variabel 12.000 / fixed cost 36.000.000.
Pada negosiasi sintetis, supplier menawarkan 15.000 dan operator menerima.
Biaya variabel menjadi 15.000: margin 15.000, break-even **2.400 unit/bulan**.
Perubahan dapat ditelusuri ke rantai offer/accept; berbeda dari fixture yang
menahan penawaran di 12.000. Demand/profit tetap unknown.

Scenario `analysis_41fb945dd53f45008365` **partial**. Delapan aksi diterima tanpa
penolakan; Market, Finance dan Legal/Compliance selesai. Risk Agent terhenti pada
sisa deadline. Dua record failure pada audit adalah satu panggilan Risk dan satu
catatan review untuk role yang sama, bukan dua specialist berbeda.

| Metrik | Baseline | Scenario |
| --- | --- | --- |
| Status | completed | partial |
| Persona / ronde | 4 / 2 | 4 / 2 |
| Aksi diterima / ditolak | 8 / 0 | 8 / 0, ditambah scheduled shock |
| Specialist live selesai | 4 / 4 | 3 / 4 |
| Durasi kerja | 280,173 detik | 298,011 detik |
| Batas waktu | 300 detik | 300 detik |
| Kandidat finding | 6 | 5 |
| Harga jual kondisional | Rp30.000 | Rp24.000 |
| Biaya variabel hasil negosiasi | Rp15.000 | Rp15.000 |
| Margin kontribusi | Rp15.000 | Rp9.000 |
| Break-even unit/bulan | 2.400 | 4.000 |
| Demand/profit | unknown | unknown |
| Token dilaporkan | 45.937 lengkap | subtotal 39.271; total unknown |
| Biaya provider | USD 0,000870438 lengkap | subtotal USD 0,000744042; total unknown |

Baseline result digest tidak berubah. Scheduled shock turun harga competitor 20%
di ronde 2, dengan strategi match-price yang dipilih eksplisit. Perbandingan ini
dua run kondisional, bukan estimasi kausal pasar. Semua findings tetap
NEEDS_VALIDATION, evidence BPS tetap PARTIAL, dan laporan masing-masing memuat
delapan bagian. Browser live desktop/mobile lulus dengan overflow halaman false.

Pembacaan key sesudah settlement singkat: usage delta sesi **USD 0,001775575**,
termasuk kejadian tes lama, dengan remaining limit key **USD 0,196681314**.
Ini observasi saat pemeriksaan, bukan jaminan billing lengkap untuk satu attempt
Risk yang terhenti. Nilai awal setelah run sempat lebih rendah karena settlement
belum tercermin; angka itu tidak dijadikan biaya final per panggilan.

Deadline global 300 detik ditegakkan pada kedua run. Proses live sempat memuat
versi guard per-panggilan yang memakai provider timeout; satu review berlangsung
89 detik. Source final memperketat batas proses specialist ke maksimum 60 detik,
termasuk startup, dan diuji lokal. Tidak ada paid repeat setelah pengetatan ini.

Persona smoke test ditambahkan manual dan ditinjau sebagai hipotesis sintetis;
ini tidak mengukur kualitas dynamic stakeholder discovery. Tidak ada klaim
superioritas kualitas atau kesiapan produksi.

Audit tersanitasi: `backend/data/runtime-audit/2026-10-30/`. Tidak ada key, cookie
atau password di bukti. Berkas utama: `live-baseline-report.html`,
`live-scenario-report.html`, proyeksi JSON, `live-comparison.json`,
`live-verification.json`, pemeriksaan BPS, hasil tes dan screenshot desktop/mobile.

## Batas lanjutan

Pencocokan publikasi BPS, evaluasi bisnis independen/ablation, semantik industri
lain, serta recovery/retensi/penghapusan lintas penyimpanan tetap release gates.
Perubahan ini belum menyatakan aplikasi siap produksi.

## Berkas utama yang berubah

Baru: `backend/app/business/budget.py`, `call_worker.py`, `usage.py`;
`backend/tests/test_business_budget.py`, `test_business_evidence.py`;
`docs/evaluation/README.md`, `business-cases.v0.json`, dan catatan hasil ini.

Diubah: business `agents.py`, `evidence.py`, `oasis_bridge.py`, `service.py`,
`repository.py`, `structured.py`; `backend/app/oasis_direct.py`; test `conftest.py`,
`test_business_structured.py`, `test_business_runtime.py`, `test_business_api.py`;
backend README, contoh env root/backend dan Compose; frontend API business,
binding usage pada BusinessAnalysisPage dan browser test business-report;
plan/status implementasi. Key tetap di konfigurasi lokal yang diabaikan Git.

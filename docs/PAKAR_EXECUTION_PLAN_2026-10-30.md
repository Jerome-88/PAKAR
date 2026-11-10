# Plan eksekusi PAKAR — Jumat, 30 Oktober 2026

Status: **dieksekusi, 30 Oktober 2026; baseline completed, scenario partial**. Dibuat 29 Oktober 2026, WIB.
Hasil aktual: [execution results](PAKAR_EXECUTION_RESULTS_2026-10-30.md).

## Target besok

Menutup satu alur demo bisnis yang dapat diperiksa: **dokumen sintetis → review
asumsi/persona → evidence BPS sesuai wilayah → baseline live → scenario → laporan
delapan bagian dengan sumber, perubahan state dan keterbatasan yang jelas**.

Prioritas: kecocokan data, kendali penggunaan API dan hasil yang dapat ditelusuri.
Keberhasilan demo tidak otomatis berarti siap produksi atau membuktikan bahwa
multi-agent lebih baik daripada satu LLM.

## Titik awal

- Intake, review claim/persona, OASIS/CAMEL, empat specialist, findings,
  scenario terpisah, laporan PRD dan ekspor HTML sudah tersedia.
- Smoke live sebelumnya: baseline dan scenario masing-masing dua persona,
  dua ronde; keduanya selesai. Belum menjadi pengujian lintas kasus/skala.
- Key BPS pernah berhasil diuji. Satu sampel Indonesia berstatus PARTIAL;
  pemetaan wilayah proyek dan pemeriksaan skala angkanya belum selesai.
- Deadline belum ketat: scenario sebelumnya sekitar 310 detik untuk konfigurasi
  300 detik. Billing runtime per panggilan belum lengkap.
- Avatar selesai; build/lint, 65 tes frontend dan workflow browser fixture lulus.
  Tes tampilan 120 node tidak sama dengan simulasi live 120 persona.

Referensi: [status implementasi](PAKAR_IMPLEMENTATION_STATUS.md),
[revisi PRD](PAKAR_PRD_REVISION_v1.1.md), [catatan avatar](persona-avatars.md).

## Urutan eksekusi

| Urutan | Pekerjaan | Hasil yang harus tersedia |
| --- | --- | --- |
| 1 | Preflight dan kasus demo | Layanan sehat, input sintetis tetap, rencana anggaran tercatat |
| 2 | Kurasi BPS sesuai wilayah | Observasi relevan dengan metadata, skala dan keterbatasan yang diperiksa |
| 3 | Deadline dan usage | Penghentian request/proses serta pencatatan penggunaan teruji sebelum live |
| 4 | Uji tanpa biaya LLM | Alur fixture, laporan, error handling dan navigasi lulus |
| 5 | Baseline/scenario live terbatas | Hasil, audit aksi, evidence dan perbandingan tersimpan |
| 6 | Paket demo dan status akhir | Bukti uji, laporan, daftar gap dan langkah evaluasi berikutnya |

### 1. Preflight dan tetapkan kasus demo

- Periksa database/migrasi, backend, worker, frontend dan runtime OASIS yang
  digunakan. Hindari menjalankan dua worker lokal tanpa sengaja.
- Periksa konfigurasi provider/model dan key tanpa menampilkan secret.
  Pertahankan model yang sudah kompatibel dengan structured output.
- Default kasus: **kedai kopi sintetis di DKI Jakarta**. Ini wilayah provinsi;
  jangan menyamakannya dengan kota administratif atau seluruh Indonesia.
  Perubahan wilayah harus eksplisit di konteks proyek.
- Siapkan angka biaya/harga dengan basis unit/periode yang jelas. Demand dan
  profit tetap unknown jika inputnya belum didukung. Pisahkan angka sintetis
  dari observasi BPS.
- Review operator, supplier, customer dan competitor: tujuan, provenance,
  duplikasi dan identitas sebelum membekukan input run.

Selesai bila konteks, input, persona, model dan anggaran demo sudah tercatat.

### 2. Kurasi BPS untuk konteks tersebut

Area: `backend/app/business/evidence.py`, konfigurasi indikator lokal dan tes
evidence dalam suite business yang ada.

- Cari domain, variabel, periode dan dimensi dari katalog resmi. Jangan menebak
  kode periode dari tahun. Batasi pencarian pada wilayah/indikator yang relevan.
- Target minimal satu indikator yang membantu memeriksa konteks bisnis.
  Pengeluaran per kapita dapat menjadi kandidat jika tersedia dan cocok;
  ketersediaannya belum dijamin oleh plan ini.
- Periksa definisi, label wilayah, nilai mentah, pengali/skala, satuan, periode
  observasi dan waktu publikasi. Cocokkan dengan tabel/publikasi resmi yang sama.
  Sampel nasional lama juga masih memerlukan pemeriksaan skala.
- Simpan sumber tanpa API key, waktu pengambilan, checksum dan batas relevansi.
  Jumlah penduduk atau pengeluaran tidak otomatis menjadi demand kedai.
- Uji cache, wilayah tidak terpetakan, data kosong/stale, timeout dan kegagalan
  provider. Jangan mengganti kegagalan dengan angka atau status VERIFIED.
- PARTIAL tetap benar jika kaitan indikator dengan claim belum cukup kuat.

Selesai bila satu observasi sesuai wilayah dapat ditelusuri dan skala angkanya
dijelaskan; claim yang belum didukung tetap memiliki evidence gap. Bila indikator
relevan tidak tersedia, catat UNAVAILABLE dan batas demo secara eksplisit.

### 3. Perbaiki deadline dan usage sebelum inference berbayar

Area: `backend/app/business/service.py`, `agents.py`, `oasis_bridge.py` dan
batas proses di `backend/app/oasis_direct.py`.

- Gunakan satu deadline berbasis waktu monoton untuk evidence, runtime persona,
  specialist dan finalisasi dalam satu attempt. Operasi berikutnya hanya mendapat
  sisa waktu, bukan jatah penuh yang baru.
- Hentikan dispatch ketika waktu/token habis. Tangani panggilan HTTP sinkron dan
  subprocess yang masih hidup; timeout coroutine saja belum menjamin berhenti.
- Cadangkan waktu penyimpanan hasil/status. Pisahkan budget kerja dari toleransi
  cleanup. Target tes provider lambat: cleanup maksimal lima detik setelah
  deadline, dengan kondisi pengukuran dicatat.
- Catat per panggilan: role/fase, model, attempt, durasi, token, status dan biaya
  provider bila tersedia. Pisahkan biaya terukur, estimasi dan unknown; unknown
  tidak boleh dianggap nol.
- Budget sesi mencakup semua attempt; hindari retry otomatis yang menggandakan
  belanja. Reservasi token mencakup schema, prompt dan batas output.
- Uji provider palsu/lokal: request lambat, JSON invalid, token habis dan cancel.
  Periksa tidak ada proses yatim atau event baru dari attempt yang kehilangan
  hak menulis. Hasil partial/failed harus menjelaskan sebab.

Selesai bila batas waktu/cleanup dan penggunaan API terbukti pada tes lokal,
tanpa membuat laporan seolah fase yang terhenti sudah selesai.

### 4. Verifikasi offline end-to-end

- Jalankan fixture pada input yang sama: review → baseline → scenario penurunan
  harga competitor 20%, dengan strategi respons yang dipilih eksplisit.
- Periksa offer/accept, actor/target, versi state dan referensi event.
- Pastikan scenario terpisah, avatar konsisten, baseline tidak berubah dan
  perubahan hitungan dapat direproduksi dari formula/input tersimpan.
- Periksa delapan bagian laporan, evidence gaps, label sintetis dan unknown.
  Uji adapter BPS secara terpisah; fixture engine tetap berlabel fixture dan
  tidak diam-diam berubah menjadi live.
- Jalankan tes backend terdampak. Setelah perubahan stabil, jalankan suite
  backend/frontend, build, lint dan workflow browser yang relevan.

Selesai bila regresi relevan lulus. Tahap ini tidak menggunakan biaya LLM.

### 5. Uji live secara bertahap dan hemat

**Usulan plafon pengujian besok: USD 0,02 total**, atau lebih rendah jika saldo
aktual tidak mencukupi. Saldo yang pernah disebut pengguna bukan saldo yang sudah
diverifikasi untuk besok. Tidak ada inference berbayar saat menulis plan ini.

- Periksa saldo dan harga model yang berlaku sebelum run. Jangan mengganti
  provider/model, melakukan top-up atau menaikkan plafon otomatis.
- Hitung estimasi maksimum konservatif dari jumlah panggilan dan token/output
  seluruh sesi; sisakan ruang untuk usage yang terlambat. Token cap sendiri
  bukan jaminan hard cap dolar dari provider.
- Jika biaya tidak dapat dibatasi dengan cukup pasti, selesaikan paket fixture
  dan tandai live tertunda. Jangan terus mencoba model/retry secara acak.
- Jika perlu preflight credential, cukup satu panggilan kecil yang ikut dihitung
  dalam plafon. Gunakan hasil preflight yang masih relevan agar tidak berulang.
- Target perluasan: **empat persona × dua ronde**, satu baseline lalu satu
  scenario dengan snapshot yang dibekukan. Scenario hanya dimulai setelah hasil
  baseline dan sisa budget diperiksa. Tidak langsung menjalankan 100 persona live.
- Rekam accepted/rejected actions, specialist yang lolos validator, durasi,
  cakupan usage/cost, stop reason, evidence dan kandidat finding.
- Periksa sebab perubahan state serta baseline tetap utuh. Catat partial/failed
  apa adanya; jangan menaikkan deadline atau mengulang hanya agar terlihat selesai.

Target demo penuh: baseline dan scenario selesai dengan sumber/limitations yang
jujur. Bila terhalang saldo, data, timeout atau kualitas output, catat bukti
penyebab dan langkah perbaikan, bukan klaim berhasil.

### 6. Rapikan hasil dan siapkan evaluasi

- Simpan bukti tersanitasi di `backend/data/runtime-audit/2026-10-30/`: ringkasan
  run, pemeriksaan BPS, usage, event/state comparison dan ekspor laporan.
  Jangan menyimpan key, cookie, kredensial atau URL berisi secret dalam bukti.
- Perbarui `docs/PAKAR_IMPLEMENTATION_STATUS.md` dengan hasil aktual, kondisi uji
  dan gap. Pisahkan hasil fixture dari hasil provider live.
- Siapkan draft tiga kasus sintetis dan rubric: relevansi/kelengkapan stakeholder,
  duplikasi, precision/recall blind spot, grounding, kegunaan, konsistensi scenario,
  latency dan biaya. Draft belum menjadi ground truth sampai direview evaluator
  bisnis independen.

## Tahap lanjutan setelah demo

1. **Evaluasi kualitas:** dataset direview manusia, beberapa pengulangan serta
   perbandingan single LLM, single LLM + tools, specialist tanpa persona dan
   PAKAR lengkap, dengan akses tool serta anggaran yang sebanding. Terpisah dari
   smoke test; tidak perlu menghabiskan budget besok untuk semua pembanding.
2. **Operasional:** uji worker mati/restart memakai provider lokal, lease dan
   idempotency, serta retensi/penghapusan lintas database, upload, runtime artifacts
   dan backup pada data uji terisolasi sebelum memakai dokumen perusahaan nyata.
3. **Cakupan bisnis:** validasi semantik aksi industri lain dan tambahan wilayah
   BPS. Temuan regulasi tetap membutuhkan review ahli.
4. PDF, advanced graph, live checkpoint fork, feasibility score dan ERP/CRM tetap
   pekerjaan terpisah; tidak menjadi target besok.

## Checklist penutupan hari

- [x] Kasus demo dan konteks wilayah ditetapkan.
- [x] Kurasi BPS serta pemeriksaan skala/aplikabilitas tercatat.
- [x] Deadline, cleanup dan usage diuji memakai provider lokal.
- [x] Regresi, build/lint dan workflow fixture lulus.
- [x] Baseline/scenario live diperiksa, atau alasan penundaan tercatat.
- [x] Tidak ada secret di bukti atau kenaikan budget otomatis.
- [x] Laporan HTML, ringkasan hasil dan status implementasi diperbarui.

Eksekusi tanggal ini sudah dicatat pada execution results: baseline completed dan
scenario partial. Pekerjaan lanjutan dimulai dari gap yang tersisa, dengan
preflight layanan/data/budget baru; tidak ada penjadwalan atau paid retry otomatis.

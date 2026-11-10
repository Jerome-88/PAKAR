# Alur otomatis PAKAR — 30 Oktober 2026

Permintaan pengguna: upload dokumen, isi keterangan, lalu langsung analisis
dengan persona sesuai konteks. Review manual tidak lagi menjadi gerbang wajib.

## Penyebab kegagalan dan perubahan

Stack endpoint discovery lama berakhir pada `BudgetExceeded`: request provider
melewati batas proses, tidak ditangani oleh route, lalu menjadi HTTP 500.
HTTP 401 `/auth/me` sebelum login adalah pemeriksaan sesi anonim; pesan React
DevTools adalah informasi development. Keduanya bukan penyebab discovery gagal.

Form utama kini hanya dokumen, nama analisis dan keterangan. Nama dapat terisi
dari filename. Industri, wilayah, target customer, mode dan ronde ada di
pengaturan tambahan. Informasi yang tidak disuplai tetap belum ditentukan.
Tombol Mulai analisis langsung membuka progres. Proyek dari alur lama juga punya
tombol Analisis otomatis agar dokumen yang sudah tersimpan bisa dipakai kembali.

Endpoint quick-analysis membuat durable job tanpa menunggu provider di request
browser. Worker menyiapkan claim dan persona, membekukan input melalui checkpoint
berpagar lease, lalu memakai engine simulasi dan specialist yang sama. Default
dua ronde, maksimal empat persona, batas token 100.000 dan waktu 300 detik.
Pembuatan persona memakai bagian dari budget yang sama, bukan tambahan tak tercatat.
Panggilan discovery maksimal 25 detik; timeout/kontrak invalid beralih ke kandidat
berbasis konteks dokumen, dengan generator dan keterbatasan yang eksplisit.
Tidak ada penggantian engine live menjadi fixture secara diam-diam.

Nama persona memakai label peran bisnis. Schema membatasi kandidat pada peran
yang terkait sumber ditambah operator/customer sebagai asumsi perspektif dasar.
Tujuan dari model tetap hipotesis. Seleksi pascarespons mempertahankan peran
kontekstual dan menambah perspektif dasar yang hilang, tanpa mengarang nama orang.
Manual discovery tetap tersedia, dengan error 504/502 yang aman untuk kegagalan
provider, bukan 500 tak tertangani.

Claim mentah proyek tidak ditandai sudah direview manusia. Snapshot menyimpan
`automatic_document_assumption` dan human_reviewed yang eksplisit; persona tetap
reviewed=false. Angka ganda/satuan tidak sesuai disimpan sebagai kutipan tetapi
tidak dipilih sembarang untuk kalkulasi. Input ambigu menghasilkan unknown.
Permintaan idempotent tidak menggandakan job walaupun persiapan memperbarui revisi
proyek. Stale worker tidak dapat membekukan/mengganti profil yang sudah tersimpan.

## Verifikasi lokal

- Full backend setelah alur otomatis awal: **230 passed, 2 skipped**.
- Setelah penyaringan nama/peran dari temuan live, suite quick-analysis/API/
  trial/structured diulang: **33 passed**. Pemeriksaan terakhir peran pendanaan
  dan quick-analysis: **9 passed**. Investor/pemodal hanya ditambahkan jika
  sumber menyebut investor/pendanaan, bukan ke setiap dokumen.
- Frontend: **65 passed**, ESLint dan build lulus. Warning bundle >500 kB
  masih ada; tidak menghalangi build.
- Browser: upload file dan keterangan → persona otomatis → laporan lulus;
  contoh editable → laporan lulus; graph/scenario/baseline immutability lulus.
  Regresi laporan delapan bagian juga lulus, memakai fixture tanpa inference.
  Suite alur otomatis akhir **3 passed** (17,6 detik); regresi laporan
  **1 passed** pada pass sebelumnya. Screenshot desktop/mobile diperiksa;
  mobile tidak overflow. Perubahan terakhir normalisasi profil backend diuji
  lokal, lalu backend dimuat ulang ke kode akhir tanpa inference ulang.

## Satu smoke live

Run `analysis_0c9715b2398a496f9715` memakai dokumen sintetis kedai kopi,
tanpa approval claim, pembuatan atau review persona manual. Discovery AI selesai
dalam fase persiapan; laporan delapan bagian tersedia dalam **127,515 detik**.
Status **partial**: 7 aksi diterima, 1 ditolak, 3/4 specialist selesai. Legal
mendapat HTTP 429 rate limit dari provider; dua baris audit gagal merujuk satu
specialist yang sama. Tidak ada retry berbayar otomatis. BEP kondisional 2.400
unit/bulan, profit unknown. Ini bukti alur berjalan, bukan validasi kelayakan.

Run ini memakai discovery v2 sebelum normalisasi nama/peran akhir. Ia menemukan
nama orang dan dua role partner yang tidak cukup didukung dokumen. Karena itu
konfigurasi akhir memakai schema/seleksi kontekstual v3 dan label peran bisnis.
Regresi terhadap payload bermasalah tersebut ditambahkan secara lokal; hasil
tersimpan run lama tidak diubah. Tidak ada run penuh berbayar tambahan untuk
mengejar status completed.

Coverage billing live 12/13 calls, subtotal provider USD 0,000785082; satu
request gagal tidak memiliki biaya lengkap. Pembacaan key langsung saat run
selesai masih dapat tertunda oleh settlement. Pembacaan read-only pada
**2026-10-30 09:21:12 UTC** mencatat delta sejak preflight awal **USD 0,005186023**
dan sisa limit key USD 0,193270866. Ini pengamatan saat pemeriksaan, bukan
jaminan settlement final. Scan credential pada sembilan file audit: nol kecocokan.
Plafon kumulatif USD 0,02 sejak preflight awal sesi tetap berlaku, tidak direset.
Audit tersanitasi dan HTML/JSON ada di ignored
`backend/data/runtime-audit/2026-10-30/automatic/`. Credential/cookie tidak disimpan.

## Berkas

- Backend: contracts, preparation, agents, structured schema, service, repository,
  API, reporting; tes quick-analysis baru.
- Frontend: BusinessPages, BusinessAnalysisPage, BusinessHomePage, BusinessReport,
  business API client; browser trial/workflow tests.
- Dokumentasi: PRODUCT, backend/frontend README, panduan trial dan catatan ini.

OASIS/reducer tidak diganti. Review sumber/persona manual tetap tersedia untuk
perbaikan input berikutnya. Rate limit provider, validasi manusia, konflik BPS
serta retensi/penghapusan tetap merupakan batas operasional yang terpisah.

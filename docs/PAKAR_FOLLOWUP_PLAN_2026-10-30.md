# Plan lanjutan PAKAR — 30 Oktober 2026

Status: implementasi dan pasangan live selesai; hasil dan batas klaim dicatat di bawah. Melanjutkan [hasil eksekusi sebelumnya](PAKAR_EXECUTION_RESULTS_2026-10-30.md).
Hasil aktual: [follow-up results](PAKAR_FOLLOWUP_RESULTS_2026-10-30.md).

## Tujuan

Memberi semua specialist kesempatan review dalam deadline yang sama, merekonsiliasi
evidence BPS dengan publikasi resmi, dan membuktikan perilaku saat worker berhenti
mendadak tanpa mengulang inference berbayar secara otomatis.

## Urutan dan kriteria selesai

1. **Perbaiki penjadwalan review.** Maksimal dua specialist berjalan bersamaan,
   dalam dua gelombang. Konteks peer dibekukan per gelombang; hasil digabung dalam
   urutan Market, Finance, Legal/Compliance, Risk, bukan urutan selesai. Konteks
   dipadatkan tanpa menghilangkan ID sumber, status ketidakpastian, nilai/unit dan
   parent event. Token reservation harus aman untuk concurrency. Sisakan waktu
   review dari budget runtime. Model, reducer, batas waktu 300 detik dan aturan
   validasi tidak diganti. Snapshot run baru menyimpan versi kebijakan review;
   baseline lama tetap immutable dan scenario mewarisi kebijakan baseline.
   Setelah tiga kegagalan transport pada uji dua request aktif, default transport
   untuk analisis baru dibatasi satu request. Dua gelombang dan peer scope tetap
   sama; mode dua request harus dipilih eksplisit. Penyebab pasti kegagalan lama
   belum terklasifikasi, jadi tidak dianggap sebagai bukti limit concurrency provider.
2. **Buktikan scheduler secara lokal.** Uji dua gelombang, hasil deterministik,
   peer disagreements, role/reference invalid, batas token, cancellation dan
   satu reviewer lambat. Tidak ada panggilan provider asli pada tes default.
3. **Rekonsiliasi BPS.** Ambil publikasi resmi melalui jalur resmi yang tersedia;
   bandingkan indikator, tahun, wilayah, satuan dan angka. Simpan checksum/lokasi
   tabel. Jika angka berbeda, catat konflik dan jangan memilih angka pengganti
   diam-diam. Kecocokan publikasi tidak otomatis memverifikasi claim bisnis.
4. **Uji worker mati/restart.** Pakai database uji dan provider lokal. Periksa
   lease expiration, fencing terhadap stale worker, status terminal dan larangan
   retry berbayar otomatis. Nilai apakah runtime/request anak ikut terhenti.
   Retensi/penghapusan business storage tetap harus diperiksa terpisah; jangan
   menganggap purge legacy sudah mencakup business tables/runtime artifacts.
5. **Regresi dan satu pasangan live bila budget memadai.** Gunakan kasus sintetis,
   empat persona × dua ronde, baseline baru dan scenario baru, deadline 300 detik.
   Jalankan sekali per konfigurasi, periksa coverage empat specialist, biaya,
   validasi aksi, baseline immutability, laporan delapan bagian dan partial/error
   yang jujur. Tidak ada retry untuk mengejar status completed.
6. **Catat hasil dan gap tersisa.** Perbarui status, laporan dan bukti tersanitasi.
   Benchmark independen tetap membutuhkan evaluator manusia; draft bukan ground truth.

Tambahan dari audit live: tahan perbandingan nominal eksplisit yang secara
aritmetika salah sebelum finding baru diterima. Untuk registry lama, terapkan
proyeksi baca pada API/laporan tanpa menulis ulang baseline. Catatan disagreement
yang merujuk finding tertahan tetap disimpan dengan peringatan, bukan dianggap
dukungan. Pemeriksaan sempit ini bukan fact checker semantik umum.

## Budget dan batas lingkup

Plafon tetap **USD 0,02 kumulatif sejak preflight sesi tanggal ini**, termasuk
pemakaian sebelumnya sekitar USD 0,001775575. Bukan plafon baru yang direset.
Periksa ulang saldo, routing price ceiling dan reservasi konservatif sebelum live.
Pertahankan Nemo; tidak ada top-up, kenaikan limit key atau penggantian model otomatis.
Jika biaya tidak dapat dibatasi, tutup pekerjaan dengan tes lokal dan catat live tertunda.

Tidak ada deployment publik, penghapusan data pengguna nyata, live fork, ERP/CRM,
PDF export, feasibility score atau klaim kesiapan produksi pada paket ini.

## Bukti yang diharapkan

- Tes scheduler, budget/cancellation dan recovery dengan provider lokal.
- Catatan rekonsiliasi BPS termasuk konflik atau akses yang masih terhalang.
- Laporan baseline/scenario baru jika live dijalankan, dengan versi review dan
  biaya/unknown coverage yang eksplisit.
- Daftar gap operasional dan evaluasi yang benar-benar masih terbuka.

# Hasil pengembangan swarm — 31 Oktober 2026

[Plan](PAKAR_SWARM_PLAN_2026-10-31.md) sudah diimplementasikan dan diuji lokal.
Alur pengguna tetap upload dokumen → keterangan → mulai analisis. Analisis quick
baru default mode swarm, empat customer, maksimal delapan persona dan tiga ronde.
Mode berpasangan tetap tersedia di pengaturan tambahan; analisis manual lama dan
snapshot tanpa mode baru tetap memakai reducer/perilaku lama.

## Perilaku baru

- Customer mempunyai lensa nilai/harga, kualitas/kejelasan, keandalan layanan,
  dan kemudahan penggunaan. Lensa tambahan tersedia bila jumlah diubah. Ini
  hipotesis kebutuhan, bukan demografi, segmentasi terukur atau proporsi pasar.
  Stakeholder lainnya mengikuti konteks dokumen. ID dibekukan sebelum simulasi,
  disimpan di snapshot/profil dan dipakai lagi oleh scenario serta avatar lokal.
- Persona dapat membuka post dan membalas pesan di thread yang sama. Thread
  publik dapat dibaca peserta lain; thread privat terbatas pada dua partisipan.
  Server menolak referensi tak terlihat, cross-thread reply dan perluasan akses
  privat. Prompt peserta tidak membawa dump memori/keuangan privat milik pengirim
  pesan publik. Ini pengamanan struktur/akses; bukan jaminan model tidak pernah
  menulis ulang informasi sensitif dalam teks bebas.
- Sikap mendukung/menolak/bersyarat/belum memutuskan, alasan dan riwayat disimpan
  terpisah dari nilai finansial. Perubahan sikap yang sudah dinyatakan membutuhkan
  alasan dan referensi terlihat dari pihak lain. Referensi itu adalah pengaruh
  yang dinyatakan peserta, bukan pembuktian sebab akibat di pasar nyata.
- Diskusi/opini tidak dapat mengubah harga, biaya atau volume. Penawaran,
  penerimaan dan strategi match-price tetap melalui reducer bisnis yang sama.
- Scheduler memberi giliran terbatas, mendahulukan pembukaan topik oleh operator
  lalu customer. Pesan baru yang relevan dapat dibaca pada giliran berikutnya.
  Tidak ada penyamaan sikap secara otomatis atau penghentian berdasarkan suara
  mayoritas. Ronde penuh abstain dapat berhenti lebih awal, sambil menghormati
  awal/akhir shock terjadwal. Batas event/token/waktu tetap menghasilkan partial,
  bukan diganti menjadi status diskusi selesai normal.
- Empat specialist menerima pesan, sikap dan referensi thread dalam konteks
  terbatas yang eksplisit. Laporan delapan bagian menyertakan jejak diskusi,
  alasan perubahan, perbedaan posisi, source links dan tugas validasi. HTML export
  membawa thread, akses, balasan dan riwayat sikap dengan teks yang di-escape.
- Tab **Diskusi swarm** menampilkan pembicara, role, avatar, balasan, akses thread
  dan posisi terakhir. Navigasi balasan menuju pesan yang dirujuk; event di luar
  thread dapat ditelusuri lewat timeline. Progres menampilkan diskusi saat run
  berjalan, lalu laporan tersedia setelah selesai. Perpindahan ke scenario baru
  membuka tab sesuai run baru, tanpa mewarisi pilihan tab run sebelumnya.

## OASIS dan lingkup swarm

OASIS/CAMEL terpasang tetap menjalankan tiap persona. Adapter bisnis memakai
INTERVIEW untuk menghasilkan aksi terstruktur, lalu menyimpan/merutekan thread
dan state melalui validator server. Ini diskusi multipersona dengan giliran
terjadwal, bukan feed Reddit native, jaringan rekomendasi sosial, atau seluruh
agent berjalan paralel tanpa batas. Tidak ada penggantian mesin OASIS/MiroFish.

Satu giliran memuat pesan dan sikap sekaligus; tidak ada call tambahan khusus
untuk menilai sikap. Jumlah peserta/ronde yang lebih besar tetap meningkatkan
panggilan model. Batas token 100.000 dan waktu 300 detik tidak dinaikkan. Run live
dapat berhenti partial jika budget atau provider membatasi. Tidak ada paid retry
otomatis; plafon sesi lama tidak direset.

## Bukti lokal

Fixture baru melalui API/PostgreSQL menghasilkan:

| Pengukuran | Hasil |
|---|---:|
| Persona / customer | 7 / 4 |
| Ronde / thread | 3 / 1 |
| Pesan publik | 16 |
| Balasan customer ke customer | 11 |
| Perubahan sikap setelah posisi awal | 1 |
| Posisi akhir | bersyarat, menolak, belum memutuskan |
| Aksi diterima / ditolak | 21 / 0 |
| Bagian laporan | 8 |
| BEP kondisional baseline | 2.000 unit/bulan |
| Profit | unknown |
| Inference calls | 0 |

Waktu worker fixture 0,877 detik **bukan latensi AI live**. Angka dan percakapan
fixture terprogram untuk menguji kontrak; tidak mengukur mutu analisis atau
perilaku model. Scenario match-price −20% diuji menghasilkan BEP kondisional
3.000, memakai persona yang sama dan tanpa mengubah baseline.

Artefak lokal tersanitasi:
`backend/data/runtime-audit/2026-10-31/swarm/` berisi input, hasil, laporan JSON,
`demo-report.html` dan verification. Tidak ada credential/cookie disimpan; scan
exact-byte credential pada lima file: nol kecocokan. Tidak ada panggilan provider
berbayar atau pemeriksaan saldo yang diperlukan untuk paket ini.

## Verifikasi

- Full backend sebelum guard/finishing akhir: **243 passed, 2 skipped**.
  Skip adalah probe runtime legacy di lokasi alternatif dan privilege symlink
  Windows. Runtime bisnis terpasang tetap diuji.
- OASIS/CAMEL + OpenAI SDK sungguhan dengan HTTP provider lokal lulus untuk
  pairwise dan swarm: thread, customer reply, schema scoped state/ID dan usage.
  Suite akhir swarm/API/runtime: **15 passed**. Setelah finishing fixture dan
  laporan, suite swarm/API/quick/report: **23 passed**.
- Frontend final: **68 passed** dalam 65,07 detik dengan satu worker. Pass ketika
  build/test berjalan bersama mengalami timeout di avatar/graph/legacy. Satu tes
  legacy lintas lima langkah juga melampaui budget total 5 detik pada pass serial,
  lalu lulus sendiri dalam 4,31 detik. Tes itu memang menunggu beberapa fallback
  poll 1,5 detik; timeout khusus seluruh kasus dinaikkan ke 15 detik tanpa mengubah
  assertion atau timeout individual. Full suite kemudian lulus; kode workflow
  legacy tidak diubah paket ini.
- Build dan ESLint lulus; warning bundle >500 kB yang sudah ada tetap tercatat.
- Browser: empat regresi report/trial/workflow lulus; test swarm baru akhirnya
  lulus (20,7 detik) setelah perbaikan tab antar-run. Mencakup upload, empat
  customer, balasan peer, fokus navigasi, riwayat sikap, mobile containment,
  HTML export, scenario, identitas tetap dan baseline immutable.
- Screenshot desktop/mobile diperiksa dalam satu pass dan finishing terbatas.
  Mechanical scan menandai ukuran 13px pada CSS baru; diganti ke ramp 14px.

## Berkas paket ini

Baru: `backend/app/business/swarm.py`, tests swarm dan swarm API;
`frontend/src/pages/Business/SwarmDiscussion.tsx`, CSS dan unit test;
`frontend/tests/e2e/business-swarm.spec.ts`; plan dan hasil ini.

Diubah: backend business contracts, preparation, structured, service, agents,
reviews, reporting, oasis_bridge; tes runtime dan quick-analysis. Frontend
business API client, BusinessPages, BusinessAnalysisPage, BusinessReport;
dokumentasi workflow/panduan, dan budget waktu satu tes integrasi legacy.
Tidak ada migrasi/destruksi data, perubahan key,
penggantian model atau publikasi/deployment eksternal.

## Batas yang tersisa

Paket ini belum diuji dengan inference berbayar pada model live. Mutu argumen,
kegunaan bisnis, biaya/latensi live serta perilaku saat rate limit membutuhkan
pengamatan berikutnya dengan budget eksplisit. Tidak ada klaim representasi
customer, akurasi prediksi, keunggulan multi-agent, atau kesiapan produksi.
Skala ratusan agent, retensi/purge bisnis, konflik BPS dan evaluasi independen
tetap di luar paket ini.

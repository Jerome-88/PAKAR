# Pemisahan pengetahuan stakeholder — 1 November 2026

Run bisnis baru memakai `public-brief-v1`, prompt `pakar-1.8`. Pengguna mengisi
**Brief untuk stakeholder** secara terpisah dari dokumen, keterangan keputusan,
dan versi ide. Run AI tanpa brief minimal 20 karakter ditolak sebelum enqueue.
Membuka ruang ide, mengunggah dokumen dan menyimpan ide tidak membutuhkan brief.

## Dua ruang

| Ruang | Konteks |
| --- | --- |
| Stakeholder | Brief yang sengaja dibagikan, POV sintetis milik persona, peserta berlabel generik dan pesan yang diizinkan terlihat |
| Analisis internal | Dokumen/riset, ide lengkap, input bisnis, kalkulator, brief yang benar-benar dibagikan dan jejak interaksi |

Customer, pesaing, pemasok, mitra, investor dan peninjau klaim tidak menerima
kutipan riset, statistik internal, HPP, margin, target penjualan atau strategi
dari input internal. Fasilitator produk (`operator`) dalam ruang stakeholder
juga menggunakan konteks publik saja. Empat specialist berada di ruang internal
dan tidak memposting isi review secara otomatis ke diskusi stakeholder.

Ini batas konteks antarperan simulasi, bukan sistem login customer eksternal.
Pemilik proyek tetap dapat memeriksa data lengkap. Provider AI untuk review
internal tetap memproses data internal yang diizinkan pengguna.

## Penegakan

`information.py` membangun ulang input model dari field yang diizinkan.
Pembatasan berlaku pada profil/system message OASIS, compact dialogue, protokol
swarm lain dan jalur berpasangan. Nama, tujuan, pengetahuan, constraint dan
interest kandidat yang dibuat dari dokumen tidak langsung diteruskan. Profil
eksternal memakai peran dan lensa sintetis yang ditentukan server; kandidat
aslinya disimpan di snapshot internal untuk pemeriksaan.

Snapshot persona yang ditampilkan pada run memakai profil yang benar-benar
digunakan. ID persona tetap sama sehingga avatar dan referensi interaksi stabil.
Tidak ada inferensi demografi atau pengalaman mencoba produk baru.

Schema juga membuang nominal dan referensi event privat yang tidak dibagikan.
Ruang stakeholder publik menolak transaksi finansial dan pesan privat; interaksi
di sini adalah kritik konsep. Reducer/kalkulator lama dipertahankan. Negosiasi
komersial dengan data rahasia memerlukan alur privat tersendiri; belum menjadi
fitur ruang publik ini. Fixture tetap dilabeli respons terprogram tanpa AI.

Brief sendiri merupakan data yang sengaja diizinkan untuk stakeholder. Sistem
tidak menjanjikan DLP otomatis atas teks yang pengguna masukkan ke field itu,
atau bahwa model tidak pernah mengarang informasi. Dokumen dan pesan tetap
untrusted data. Pemisahan input dapat diuji; mutu semantik respons perlu dinilai
tersendiri.

## Percakapan

Mulai ronde kedua, giliran dasar customer yang tidak sedang menjawab pertanyaan
langsung dapat diarahkan ke pesan customer lain yang belum ditanggapinya.
Identitas penerima, nomor pesan dan causal parent berasal dari server.
Konteks balasan menyertakan ucapan lawan bicara dan tugas menanggapi alasan
tersebut dari prioritas sendiri. Balasan pada pernyataan diberi intent klarifikasi;
balasan pada pertanyaan diberi intent jawaban.

Semua peserta tetap mendapat giliran dasar. Batas follow-up, token, event,
deadline dan cancellation tetap berlaku. Tidak ada ledakan panggilan semua
pasangan, jawaban buatan server dalam run AI, atau aturan yang memaksakan
persetujuan/perubahan posisi. Perbaikan penjadwalan dan prompt belum merupakan
bukti bahwa debat model live telah menjadi mendalam.

Specialist mendapat tugas domain yang lebih jelas: Market menyandingkan
respons dengan riset; Finance memakai input dan kalkulator; Legal mengidentifikasi
pertanyaan klaim/sumber regulasi; Risk menelusuri risiko dan asumsi. Mereka dapat
mengetahui data internal yang tidak pernah diberikan kepada stakeholder.

## Alur pengguna

1. Unggah dokumen dan isi keterangan internal seperti biasa.
2. Masukkan konsep yang boleh dilihat stakeholder pada field brief yang terpisah.
3. Jalankan analisis. Brief disimpan dalam snapshot run dan dapat diperiksa pada
   detail hasil melalui **Informasi yang dibagikan ke stakeholder**.
4. Pada ruang ide, brief disimpan terpisah per versi selama halaman terbuka;
   mengganti versi tidak menyalin brief versi lain. Draft brief belum tersimpan
   permanen sampai run dibuat.

Brief tidak diisi otomatis dari dokumen atau teks ide. Contoh untuk disesuaikan
pengguna sebelum menjalankan Pepsodent:

> Konsep pasta gigi: satu tube menawarkan dua rasa untuk pagi–siang dan malam.
> Formula diusulkan berubah warna setelah sekitar dua menit menyikat. Perubahan
> warna diusulkan sebagai petunjuk visual; hubungannya dengan kebersihan gigi
> belum diuji. Harga dan mekanisme pemilihan rasa belum ditentukan.

Ini contoh deskripsi konsep, bukan hasil riset, spesifikasi formula yang
terverifikasi atau perubahan otomatis terhadap ide tersimpan.

Permintaan yang gagal secara ambigu mempertahankan body, brief dan
`Idempotency-Key`. Input terkunci dan hanya retry permintaan yang sama yang
tersedia; jalur intake, otomatis, manual dan ruang ide mengikuti aturan ini.
Penolakan definitif yang dikenali membolehkan pengguna memeriksa konteks lalu
memulai permintaan baru secara eksplisit. Tidak ada paid retry otomatis.

## Riwayat dan scenario

Hasil Pepsodent sebelumnya tidak ditulis ulang. UI menandai run live lama yang
belum memakai pemisahan brief. Review internal atas hasil lama tetap tersedia.
Scenario AI dari baseline lama ditolak: buat baseline baru dengan brief terlebih
dahulu. Scenario baseline baru mewarisi brief; deskripsi shock dan harga internal
tidak dipublikasikan otomatis. Untuk menguji informasi produk yang berubah kepada
stakeholder, pengguna perlu menyetujui brief yang diperbarui pada run baru.

## Verifikasi dan berkas

Pengujian menggunakan provider HTTP lokal dan fixture berlabel; pekerjaan ini
tidak melakukan inference berbayar. Tes memeriksa request SDK/OASIS yang sebenarnya,
termasuk system message, profil, body dan schema. Penanda data rahasia sintetis
pada riset, nama, goal, pengetahuan, ide, pertanyaan keputusan dan angka bisnis
tidak boleh muncul pada request stakeholder. Review internal tetap dapat membaca
sumber asli. Ada tes giliran antarcustomer, larangan transaksi publik, nonce,
brief per versi dan penolakan run AI tanpa brief.

Hasil tes dan screenshot berada pada
`backend/data/runtime-audit/2026-11-01/information-policy/` dan
`frontend/test-results/`. Run browser menggunakan akun QA dan data sintetis.

- Full backend: **297 passed, 2 skipped**.
- Regresi terakhir input/schema dan OASIS SDK terhadap provider lokal: **15 passed**.
- Frontend: **89 passed**; TypeScript/Vite dan ESLint lulus. Warning bundle besar
  yang sudah ada tetap muncul.
- Lima alur browser utama dan tiga alur recovery disclosure lulus, semuanya
  fixture tanpa inference berbayar. Body/nonce retry dibandingkan secara langsung.
- Detector UI sekali: tanpa temuan. Review akhir UI mencatat satu perbaikan
  material pada retry intake/proyek. Perbaikan dinilai **resolved** berdasarkan
  bukti browser desktop/mobile dan source; disposition akhir **ship**, tanpa
  regresi material.

Baru: backend `business/information.py`, tes `test_business_information.py`;
frontend `StakeholderBriefField.tsx`/CSS, `useBusinessLaunch.ts`/tes dan browser
`business-disclosure-retry.spec.ts`.

Diubah: business contracts, service, dialogue protocol, discussion, OASIS bridge,
recovery, review dan fixture-lens lookup; tes integrasi terkait; frontend API,
intake/project, ruang ide dan detail analisis beserta tes alurnya. Tidak ada
migrasi, perubahan library OASIS/CAMEL, API key atau model utama.

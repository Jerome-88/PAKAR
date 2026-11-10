# Coba input → proses → output PAKAR

Buka [contoh proposal](http://127.0.0.1:5173/business/new?example=1).
Login atau daftar lewat aplikasi jika diminta. Backend lokal memakai port 5001.

## Percobaan pertama

1. Buka [analisis baru](http://127.0.0.1:5173/business/new), lalu upload PDF
   berisi teks, DOCX, TXT atau Markdown. Nama analisis terisi dari nama file.
   Anda juga bisa memilih contoh proposal sintetis yang dapat diedit.
2. Isi **Keterangan dan pertanyaan**: rencana bisnis dan keputusan yang ingin
   diperiksa. Industri, wilayah dan target customer opsional di
   **Pengaturan tambahan**. Wilayah yang diisi dipakai untuk mencocokkan BPS;
   jika tidak diketahui, sistem tidak menebak wilayah resmi.
3. Konfirmasi penggunaan dokumen, lalu klik **Mulai analisis**. Anda langsung
   masuk halaman progres. Persona dibuat otomatis dari konteks dokumen, lalu
   interaksi dan pemeriksaan specialist berjalan. Tidak perlu menyetujui claim
   atau membuat persona satu per satu.
4. Baca **Laporan akhir**, lalu periksa tab interaksi, evidence dan audit.
   Buka **Persona yang dibuat** untuk melihat profil yang dipakai. Sumber dan
   pengaturan tetap dapat diperiksa lewat halaman proyek.
5. Untuk menguji kondisi berbeda, buka **Scenario Lab** setelah baseline selesai.
   Penurunan harga competitor tidak otomatis mengubah harga sendiri; pilih
   strategi menyamai harga competitor jika itu yang hendak diuji.

Default memakai **AI live**, mode **Diskusi swarm**, tiga ronde, empat perspektif customer dan maksimal delapan persona. Pembuatan
persona AI dibatasi waktunya; jika gagal, kandidat kontekstual dari dokumen
menjadi fallback yang ditandai dalam provenance dan keterbatasan laporan.
Fallback ini tidak mengganti engine analisis AI menjadi fixture secara diam-diam.

Untuk mencoba alur tanpa biaya model: pilih contoh sintetis, buka
**Pengaturan tambahan ? Mode analisis ? Demo tanpa AI**. Persona tetap dibuat
secara otomatis dari konteks, tetapi respons simulasi terprogram. Mode ini bukan
pengujian kualitas AI. Tidak ada discovery live terpisah pada jalur otomatis.

Jika proyek sudah terlanjur dibuat pada alur lama, buka proyeknya dan klik
**Analisis otomatis**. Tidak perlu mengunggah dokumen lagi. Tombol discovery
manual masih tersedia di pengaturan lama; kegagalan provider ditampilkan sebagai
error terkontrol, bukan traceback 500.

## Membaca diskusi swarm

Saat analisis berjalan, diskusi dapat muncul pada halaman progres. Setelah selesai,
buka tab **Diskusi swarm** untuk membaca thread dan balasan customer ke customer.
Klik **Membalas ...** untuk menuju pesan asal. Buka **Alasan dan pengaruh pada
sikap**, lalu **Posisi sintetis terakhir** untuk memeriksa riwayat perubahan.
Thread privat diberi label akses; tampilan pemilik proyek merupakan audit run.

Empat customer memakai lensa kebutuhan yang berbeda; ini bukan empat segmen
pasar terukur. Sikap boleh tetap menolak atau belum memutuskan. Kesepakatan tidak
memverifikasi pasar. Empat specialist memeriksa diskusi dan sumber tersebut.
Laporan dan HTML export juga memuat jejak pesan serta sikap.

Jumlah perspektif customer, ronde dan pilihan **Interaksi berpasangan** tersedia
di pengaturan tambahan. Semakin banyak giliran, semakin banyak panggilan model;
batas budget dapat membuat hasil live berstatus partial. Untuk melihat alur
langsung tanpa kredit, gunakan **Demo tanpa AI** dengan contoh sintetis.

## Input dan angka yang bisa diperiksa

Ekspektasi berikut berlaku untuk fixture tiga ronde dengan input asli, operator
dan supplier aktif, serta tanpa perubahan nilai manual. Angka ini pemeriksaan
rumus kondisional, bukan proyeksi atau kriteria penilaian kualitas LLM.

| Contoh | Harga/unit | Biaya variabel/unit | Biaya tetap/bulan | BEP baseline | Scenario yang diuji | BEP scenario |
|---|---:|---:|---:|---:|---|---:|
| Kedai kopi | Rp30.000 | Rp12.000 | Rp36.000.000 | 2.000 unit | Harga competitor −20%, strategi match-price | 3.000 unit |
| Produsen roti | Rp10.000 | Rp6.000 | Rp12.000.000 | 3.000 unit | Biaya supplier +50%, penawaran diterima | 12.000 unit |
| Jasa perawatan | Rp150.000 | Rp90.000 | Rp18.000.000 | 300 unit | Asumsi perubahan regulasi, tanpa input biaya baru | 300 unit |

Semua contoh sengaja tidak mempunyai volume penjualan. **Profit harus tetap
belum diketahui.** BEP = pembulatan ke atas biaya tetap / (harga − biaya variabel).
Pada run live, penawaran supplier atau keputusan harga yang diterima dapat
mengubah input perhitungan. Ikuti calculation trail, bukan angka ekspektasi
fixture semata. Run live sebelumnya, misalnya, menerima biaya Rp15.000 dan
menghasilkan BEP 2.400 → 4.000, bukan 2.000 → 3.000.

Bahan tambahan untuk upload sendiri:

- [Kedai kopi](examples/01-coffee-dki-v0.txt)
- [Produsen roti](examples/02-supplier-bandung-v0.txt)
- [Jasa perawatan](examples/03-services-dki-v0.txt)
- [Harga belum ada](examples/04-harga-belum-ada.txt): margin, BEP dan profit
  harus belum diketahui; jangan isi harga dengan tebakan.
- [Dua harga aktif](examples/05-dua-harga-aktif.txt): menyetujui kedua harga
  akan memblokir analisis. Tolak salah satu claim lalu coba lagi.

## Output yang perlu dibaca

Laporan terdiri dari delapan bagian: Executive Summary, Assumption Register,
Top Blind Spots, Evidence Table, Contradictions, Scenario Impact, Recommended
Validation Tasks, dan Limitations. Lampiran menjelaskan persona, event, relasi,
input/formula perhitungan dan provenance. Unduhan HTML memakai isi laporan yang
sama dan tidak memanggil model lagi.

Mulai dari temuan prioritas. Buka kutipan sumber dan event yang dirujuk, lalu
lihat apa yang masih kurang serta siapa yang disarankan melakukan validasi.
Kesepakatan persona tidak mengubah hipotesis menjadi fakta. Evidence BPS DKI
yang angkanya berbeda tetap berstatus CONFLICTING; Bandung yang belum dikurasi
tidak diam-diam memakai indikator DKI/nasional.

## Cara kerja

Dokumen → ekstraksi claim → review input → review persona → snapshot input
dibekukan → interaksi stakeholder → validasi aksi dan perubahan state oleh
server → pemeriksaan Market, Finance, Legal/Compliance dan Risk → temuan serta
laporan bersumber. Scenario membuat run terpisah dari snapshot baseline.

AI mengusulkan respons dan penilaian. Server memeriksa referensi/aksi dan
menghitung angka dengan rumus. Pemeriksaan nominal eksplisit yang salah dapat
menahan finding, tetapi tidak memeriksa seluruh makna dan fakta bisnis.

## Nilai sendiri hasilnya

Untuk setiap temuan, beri **berguna / perlu koreksi / tidak berguna** dan catat:

- Apakah relevan dengan pertanyaan keputusan dan spesifik terhadap proposal?
- Apakah kutipan, event dan angka mendukung kalimatnya?
- Apakah dampak input yang berubah dijelaskan tanpa mengarang demand?
- Apakah temuan ini menambah informasi, atau mengulang temuan lain?
- Apakah langkah validasinya konkret dan bisa dilakukan pemilik bisnis?

Audit awal menemukan temuan demand yang berulang serta campuran Bahasa Indonesia
dan Inggris pada run live. Banyaknya finding tidak berarti banyak insight unik.
Penilaian kegunaan bisnis tetap membutuhkan pembaca; tes otomatis tidak
menggantikan penilaian tersebut.

## Setelah diskusi timeout

Refresh run yang gagal. Jika event tersimpan valid, detail menampilkan laporan
parsial hasil pemulihan. Diskusi dan run asli tetap tersimpan; pemulihan tidak
memanggil AI lagi. Jika review specialist belum pernah dimulai, tombol
**Jalankan empat specialist AI** membuat review terpisah dengan biaya provider.
Percakapan tidak diulang. Setelah dibuat, gunakan **Buka review specialist**;
refresh atau klik ulang tidak membeli job yang sama dua kali.

Run lanjutan memiliki tautan diskusi asal dan tabel hasil empat specialist.
**HTTP 429** berarti provider membatasi request, bukan analisis lengkap.
Respons yang ditolak validator dan batas review ditampilkan terpisah bila
catatannya tersedia. Tidak ada retry AI otomatis. Unduhan HTML mengikuti hasil
parsial yang sama; periksa Limitations sebelum mengambil keputusan.

## Demo AI yang sudah tersimpan

Hasil live lengkap tersedia pada run
`analysis_be0b0b4f0ccf44889954`, di akun pemilik proyek. Buka hasil tersimpan
untuk memperlihatkan dua ronde, lima stakeholder, sepuluh interaksi valid dan
empat reviewer yang selesai. Dua reviewer ditandai sebagai hasil sah yang
dipakai kembali dari run sumber; dua lainnya dijalankan pada continuation.

Untuk presentasi offline, ekstrak
`backend/data/demo/PAKAR-demo-AI-2026-10-31.zip`, lalu buka `report.html`.
Membaca hasil ini tidak memakai API key atau kredit. Panduan urutan presentasi
ada di `README-DEMO.md` dalam paket. Angka BPS konflik dan profit yang belum
diketahui tetap ditampilkan sebagai keterbatasan.

Jika sebagian specialist gagal pada run lain, **Lanjutkan specialist yang belum
selesai** adalah aksi AI berbayar yang eksplisit. Review yang sudah lolos
validator dipakai kembali; diskusi tidak diulang. Hasil lanjutannya disimpan
terpisah dan tidak menjalankan retry secara otomatis saat dibuka.

## Memeriksa diskusi reaktif

Quick analysis baru memakai agenda `reactive-v2`. Buka tab **Diskusi** atau
tambahkan `?tab=swarm` pada URL hasil. Setiap pesan menampilkan pengirim,
penerima dan jenis tanggapan; tautan balasan/pemicu membawa fokus ke pesan asal.
Persona dapat bertanya dan membalas persona lain, termasuk sesama customer.
Giliran tambahan dibatasi sehingga percakapan tidak berjalan tanpa batas.

Periksa peringatan pesan mirip dan pertanyaan tanpa balasan. Jumlah pasangan
dua arah hanya menghitung referensi pesan; baca isinya untuk menilai apakah
jawaban relevan dan menambah alasan. Demo lama yang selesai secara teknis
masih mempunyai banyak pengulangan. Perkembangan dan keterbatasan live terbaru
ada di [hasil swarm reaktif](PAKAR_REACTIVE_SWARM_RESULTS_2026-10-31.md).

Hasil Qwen terbaru pada akun pemilik:
`http://localhost:5173/business/analyses/analysis_aaee63ab18d447ba9594?tab=swarm`.
Paket `backend/data/demo/PAKAR-demo-Qwen-2026-10-31.zip` dapat dibuka offline;
baca `README-DEMO.txt` lalu `report.html`. Ada delapan pesan dan empat specialist
selesai, tetapi status **parsial** tetap berlaku: ronde berhenti pada budget dan
tiga pesan mirip. Catatan manual juga menandai satuan harian/bulanan yang salah
pada ucapan operator. Kalkulator tetap 2.000 unit/bulan. Jangan memakai ucapan
itu sebagai fakta. Uji ini memakai Qwen sementara; `.env` utama tetap Nemo.

## Chat dan revisi ide

Untuk berdiskusi sebelum simulasi, pilih **Buka ruang ide dahulu** setelah upload data. Di tab **Chat & ide**, simpan ide lewat teks/dokumen, pilih fasilitator/specialist, lalu kirim pertanyaan. **Jadikan revisi ide** membuka editor; hanya **Simpan versi ide** yang menyimpan versi baru. **Analisis ide versi N** memakai versi terpilih dalam run terpisah dan berbayar pada mode live. Hasil lama memiliki tautan **Diskusikan hasil ini di ruang ide**.

[Kasus Pepsodent yang disiapkan dan bukti pengujian](PAKAR_PROJECT_CHAT_2026-10-31.md) mencatat dua turn Qwen sungguhan serta keterbatasan sumber/jawaban. Membuka chat lama tidak membeli panggilan model baru.

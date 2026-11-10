# Ruang ide dan chat proyek — 31 Oktober 2026

Satu chat tersimpan per proyek. User memilih fasilitator, Market, Finance,
Legal/Compliance atau Risk; satu pesan memanggil satu agent. Jawaban menampilkan
nama responder, status, kutipan dan tipe sumber. Referensi yang tidak disertakan
dalam konteks ditolak server. Ketepatan makna tetap membutuhkan pemeriksaan.

Dokumen diberi purpose `evidence` atau `idea`. Data/temuan menjadi sumber proyek;
dokumen ide hanya masuk konteks ide yang memilihnya. Maksimum 12 ide per proyek,
50 versi immutable per ide dan 200 chat turns per proyek pilot. User dapat
memuat riwayat lebih lama dengan pagination. Ide/penjelasan adalah asumsi,
bukan bukti pasar atau formula yang telah diverifikasi.

**Jadikan revisi ide** dan **Periksa sebelum menyimpan revisi** membuka editor.
Hanya **Simpan versi ide** yang membuat versi baru. Analisis memakai versi yang
dipilih sebagai snapshot, lalu membuat run terpisah. Versi/run lama tidak ditimpa.
Input finansial tetap melalui parser satuan dan kalkulator asli; nilai ganda
tetap unknown. Chat tidak otomatis memulai swarm atau menyimpan usulan AI.

**Diskusikan hasil ini di ruang ide** membawa rujukan analisis ke chat. Hasil
yang masih berjalan dipoll tanpa inference; pengiriman dengan rujukan itu
menunggu hasil tersedia. Sumber meliputi kutipan dokumen, usulan, temuan sintetis
dan perhitungan server bersyarat; tipe sumber tetap terlihat.

## Persistence dan biaya

Migration additive `0016_business_conversation` menambah tabel ide, versi dan
turn. Queue mendapat target chat dan tetap mewajibkan tepat satu target job.
Chat memakai worker/heartbeat/lease fencing dan subprocess provider yang ada,
satu attempt tanpa paid retry otomatis. Pesan/key disimpan sebelum inference;
refresh hanya membaca. Satu turn aktif per proyek. Owner check berlaku untuk
semua sumber, ide, riwayat dan analisis yang dirujuk.

Konteks dibatasi pencocokan teks lokal, jendela sumber dan riwayat. Belum ada
semantic retrieval atau OCR. Satu turn dibatasi 1.100 output token, default
admission 24.000 token, maksimum API 30.000, dan deadline. Model menerima hanya
potongan yang tercatat pada snapshot. Snapshot tidak berubah saat input proyek
direvisi. Worker tanpa lease tidak dapat menerbitkan jawaban. Pembatalan membuang
jawaban terlambat, mempertahankan usage diketahui dan menyatakan billing unknown
bila tidak diketahui; panggilan yang sudah dikirim tidak dianggap gratis.

Analisis yang definitif ditolak `409 revision_conflict` dapat memuat konteks
terbaru lalu memakai identity baru. Kegagalan transport ambigu mempertahankan
body/key agar retry tidak membeli run kedua.

## Kasus pengguna yang siap dibuka

Pada akun pemilik:
`http://localhost:5173/business/projects/business_75c6d7e057ea4b99b9b0?tab=chat`.

PDF `Dokumen.pdf` tersimpan dengan 396 kandidat claim. Fragmentasi/duplikasi PDF
berarti jumlah tersebut bukan jumlah fakta unik. Grafik halaman 7 dilengkapi
**Dokumen-halaman-7-transkripsi-grafik.txt**, dilabeli transkripsi visual dari
dokumen pengguna, bukan riset baru. Angka survei tetap representatif untuk studi
kasus. Tidak ada klaim bahwa grafik lain telah di-OCR.

IDEA 2 asli tersimpan sebagai versi pertama. Dua pesan bertanda **Uji integrasi
chat** dan jawaban Market Agent sungguhan sudah tersimpan. Pesan kedua memberi
hipotesis dua ruang/nozzle untuk menguji follow-up; penjelasan itu belum diterapkan
ke ide. User dapat memeriksa dan menyimpannya sendiri.

Proyek baru: unggah data, isi tujuan, pilih **Buka ruang ide dahulu**. Tambahkan
ide lewat teks/dokumen, kirim klarifikasi, lalu pilih **Analisis ide versi N**
hanya saat ingin membeli run swarm baru.

## Verifikasi

- Backend full: **281 passed, 2 skipped**; regresi chat terakhir: **10 passed**.
- Frontend full: **85 passed**. Tujuh regresi chat menguji save eksplisit,
  selected-version run, disclosure, completion announcement dan nonce recovery.
- TypeScript/Vite build dan ESLint lulus; warning bundle besar tetap ada.
- Browser chat + reactive + swarm: **3 passed**. Respons dalam screenshot chat
  adalah fixture terprogram; tidak menggunakan provider berbayar.
- Detector sekali pada komponen/CSS baru: tanpa temuan. Finish review terakhir
  **ship**, ketiga temuan awal resolved:

| Temuan UI | Hasil akhir |
| --- | --- |
| Pengumuman jawaban selesai | Resolved: polite live status menyebut responder |
| Alasan analisis nonaktif | Resolved: editor, active run dan runtime dijelaskan |
| Pemulihan permintaan stale | Resolved: identity baru hanya setelah penolakan definitif |

Live Qwen/Nebius: **dua turn completed**, 3.037 + 3.302 token, biaya provider
**USD 0.00080110**. Turn kedua menerima satu history turn. Tidak ada simulasi
baru; versi ide tetap satu. Ini bukti integrasi, bukan evaluasi mutu umum.
Jawaban pertama memparafrasekan willingness-to-pay 41% sebagai kepercayaan;
interpretasi itu perlu diperiksa. Klaim regulasi pada jawaban kedua belum
diverifikasi eksternal. Keterbatasan semantik tidak disembunyikan oleh keberhasilan
validasi kontrak/referensi.

Total Qwen termasuk tugas sebelumnya **USD 0.00779600**, di bawah tambahan USD
0.01. Cumulative session **USD 0.027027381**, di bawah plafon USD 0.03; limit key
tersisa **USD 0.171429508** saat dicek. `.env` utama tetap Nemo/Parasail; Qwen
dipakai pada proses uji saja. Jawaban berikutnya dari aplikasi memakai model utama.

Audit live ada di ignored `backend/data/demo/project-chat-pepsodent-2026-10-31/`;
XML/log tes di `backend/data/runtime-audit/`. Kredensial tidak dimasukkan ke artefak.

## Berkas dan batas

Baru: backend business `conversation.py`, `conversation_repository.py`,
`conversation_contracts.py`, `idea_inputs.py`; migration 0016; test chat;
frontend `ProjectConversation.tsx`, CSS, unit/browser test; surface brief dan dokumen ini.
Diubah: business API/tables/contracts/service/dialogue protocol/OASIS bridge/review
context; shared queue/worker dispatch/lease recovery dan readiness test. Frontend
API, intake/project dan analysis page; PRODUCT/README/panduan.

Reducer simulasi, memory/reasoning library OASIS/CAMEL, key/model utama dan hasil
lama dipertahankan. Belum tersedia: chat langsung ke persona swarm individual,
semantic retrieval, OCR otomatis, skor 6P tervalidasi dan pembuktian formula/klinis.
Debat swarm lama yang repetitif tetap tidak dipromosikan sebagai hasil berkualitas.

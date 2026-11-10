# Diskusi swarm reaktif — 31 Oktober 2026

## Perubahan yang dapat diperiksa

Quick analysis baru memakai `reactive-v2`: semua peserta mendapat giliran dasar,
penerima pertanyaan/sanggahan diprioritaskan, dan giliran tambahan dibatasi per
ronde. Pertanyaan mempunyai penerima spesifik; respons yang ditugaskan harus
membalas pesan pemicunya. Snapshot lama tetap menggunakan kebijakan yang dibekukan.

OASIS/CAMEL tetap menjalankan stakeholder dan memorinya. Constructor/template
publik OASIS dipakai untuk memberi tugas bisnis sesuai peran, tanpa mengganti
engine atau mengubah library. Reducer finansial, akses privat, causal references,
lease, cancellation dan larangan retry berbayar otomatis tetap berlaku.

Protokol ringkas memisahkan isi ucapan dari metadata server. Pada respons yang
ditugaskan, AI menulis `content`, `stance`, `stance_reason`; server mengikat
identitas, revision, thread, visibility dan parent ke pesan pemicu yang terlihat.
Label answer menunjukkan slot respons, bukan jaminan kecukupan makna jawaban.

Versi `pakar-1.6` menambahkan `choice_dialogue` untuk quick run baru. AI memilih
satu opsi interaksi yang terikat ke nomor peserta/pesan dalam konteksnya.
Pilihan sanggahan tidak dapat kehilangan referensi pesan atau berubah penerima.
Ucapan, pilihan interaksi dan sikap tetap berasal dari model; tidak ada ucapan
buatan server atau aturan yang memaksakan persetujuan/konflik. Pilihan finansial
tetap diperiksa reducer asli. Protokol lama tetap tersedia lewat snapshot config.

UI/laporan menampilkan penerima, intent, navigasi balasan dan pemicu, pasangan
yang saling membalas, balasan antarcustomer, pesan mirip dan pertanyaan tanpa
balasan penerima. Semua ini indikator struktur; pembaca tetap perlu menilai
relevansi, kebenaran, kecukupan jawaban dan kegunaan bisnis. `?tab=swarm` membuka
diskusi secara langsung. Hasil parsial dengan diskusi tersimpan tetapi tanpa
panggilan reviewer menawarkan aksi review berbayar yang eksplisit.

Reservasi token sekarang memakai identitas giliran unik termasuk follow-up
dalam ronde yang sama. Usage lengkap menyelesaikan reservasi dengan token aktual;
usage tidak lengkap tetap konservatif. Runtime memerlukan trace baru per giliran,
sehingga kegagalan provider tidak dapat memakai ulang respons giliran sebelumnya.
Reviewer mengurangi jendela event/peer secara eksplisit sebelum admission jika
budget sempit; record penuh tetap tersimpan pada audit dan laporan.

## Hasil live yang belum memenuhi sasaran

Empat percobaan Nemo disimpan terpisah; hasil lama tidak ditimpa:

| Run | Pesan valid / ditolak | Pasangan dua arah | Pesan mirip | Biaya provider USD |
| --- | --- | --- | --- | --- |
| `analysis_8c554ae1f2964169bc8f` | 12 / 0 | 2 | 3 | 0.00227319 |
| `analysis_95d1f44a8a014f9d9681` | 9 / 0 | 2 | 2 | 0.00159357 |
| `analysis_e81ffa6cfe56457b81b8` | 14 / 0 | 3 | 7 | 0.00170538 |
| `analysis_8c7c1d76d6dc49b4ab9b` | 10 / 4 | 2 | 5 | 0.00088239 |

Mekanisme respons berjalan, tetapi pembacaan manual masih menemukan pengulangan,
peran yang tertukar, dan pertanyaan generik. Angka dua arah tidak membuktikan
debat yang baik. Keempat hasil parsial ini tidak dipromosikan sebagai demo debat.

Uji Qwen pertama, `analysis_fc2bce3d8ffd43ebabd1`, memakai Nebius dan menghasilkan
5 pesan valid / 3 ditolak dalam 57,083 detik, biaya provider USD 0.00235920.
Tiga customer response ditolak karena intent membutuhkan parent yang tidak
dipilih model. Budget token menghentikan ronde dan empat reviewer belum
dispatch. Bahasa dan relevansi bisnis lebih baik, tetapi pesan masih berulang
dan sebagian mencapai batas panjang di tengah kalimat. Temuan ini melandasi
pilihan interaksi terikat dan instruksi ucapan pendek, bukan klaim selesai.

Model Qwen yang diuji adalah `qwen/qwen3-30b-a3b-instruct-2507`, dirutekan ke
Nebius dengan fallback mati dan batas harga input/output USD 0.10/0.30 per juta
token pada proses uji saja. Lihat [halaman resmi model](https://openrouter.ai/qwen/qwen3-30b-a3b-instruct-2507).
Konfigurasi model utama di `.env` tidak diganti oleh eksperimen ini.

## Hasil Qwen yang tersimpan untuk pemeriksaan

Protokol pilihan pada `analysis_aa5ab95c49d04e94b2ae` menghasilkan delapan pesan
valid, nol ditolak, tiga pasangan saling membalas dan dua balasan antarcustomer
dalam 40,972 detik. Tiga pesan hampir sama. Pembacaan manual menemukan operator
tidak menjawab kendala supplier dan salah menyebut BEP 2.000 unit sebagai angka
harian; kalkulator tetap benar pada 2.000 unit/bulan. Ronde berhenti karena budget.

Review dilanjutkan terpisah tanpa mengulang percakapan. Satu respons Market awal
ditolak validator. Review berikutnya diterima; Finance dan Legal diterima pada
kelanjutan berikutnya, lalu Risk pada kelanjutan terakhir. Batas admission token
yang konservatif membuat seluruh reviewer tidak muat dalam satu run kecil.
Packing serial sekarang menunggu settlement usage sebelum menyiapkan request
berikutnya; peer dalam satu wave tetap dibekukan.

Hasil terakhir: `analysis_aaee63ab18d447ba9594`, lima stakeholder, dua customer,
delapan pesan asli, empat review specialist diterima dan delapan bagian laporan.
Market/Finance/Legal diwarisi dari sumber, Risk baru. Status tetap **partial**
karena diskusi terhenti dan kualitasnya terbatas. Lolos validator berarti kontrak,
referensi dan pemeriksaan yang tersedia diterima; bukan penilaian makna menyeluruh.
Review Finance melebar ke kualitas produk, sedangkan review Legal melebar ke
harga/daya beli. Interpretasi daya beli itu belum dibuktikan indikator BPS.

Buka hasil pada akun pemilik proyek:
`http://localhost:5173/business/analyses/analysis_aaee63ab18d447ba9594?tab=swarm`.
Paket offline `backend/data/demo/PAKAR-demo-Qwen-2026-10-31.zip` berisi HTML,
JSON, event, verification, ringkasan biaya gabungan dan catatan pemeriksaan manual.
Raw hasil semua percobaan dan sumber tetap sama; hash sumber timeout lama juga
diverifikasi. Membuka paket atau run tersimpan tidak menghabiskan kredit.

Seluruh uji Qwen termasuk discovery, respons yang ditolak dan review lanjutan:
**22 panggilan, 55.545 token, USD 0.00699490** berdasarkan biaya provider per
generation ID unik. Pada **21:03:46 WIB**, cumulative key usage sejak preflight
awal USD **0.026226281**; limit key tersisa USD **0.172230608**. Keduanya sudah
settle dan cocok dengan biaya panggilan. Tambahan Qwen di bawah USD 0.01 dan
total sesi di bawah USD 0.03. Tidak ada panggilan berbayar tambahan yang dijadwalkan.

Paket ini memperlihatkan input/output dan diskusi antarpersona, tetapi **belum
memenuhi sasaran debat mendalam atau rekomendasi bisnis tervalidasi**. Membutuhkan
evaluasi isi dan penyesuaian model/prompt lebih lanjut; tidak ada janji bahwa
bertambahnya jumlah agent otomatis memperbaiki hasil.

## Bukti lokal

Full backend setelah protokol pilihan: **270 passed, 2 skipped**. Sesudah
perbaikan settlement packing serial, regresi review/integration/continuation:
**17 passed**. Suite discussion/review/quick/swarm API: **33 passed**; runtime
OASIS/CAMEL asli terhadap provider HTTP lokal: **6 passed**, meliputi pairwise,
swarm, reactive, compact dan pilihan interaksi, tanpa biaya inference.
Frontend full terakhir: **78 passed**; targeted UI sebelumnya: **9 passed**.
Build dan ESLint lulus; warning bundle besar tetap ada. Browser regression
reactive + swarm: 2 passed, memakai fixture berlabel tanpa biaya inference.
Paket HTML Qwen final dibuka di Chromium pada viewport mobile: nol request
jaringan, tanpa overflow, dan peringatan pengulangan terlihat. Backend terbaru
direstart setelah tidak ada job aktif; `/health` dan `/ready` lulus pada port 5001.

Impeccable finish reviewer: **ship**, tanpa material fix. Bukti fixture UI
menetapkan presentasi/navigasi, bukan kualitas percakapan AI live.

## Berkas implementasi

Baru: `backend/app/business/discussion.py`, `dialogue_protocol.py`,
`backend/tests/test_business_discussion.py`,
`frontend/tests/e2e/business-reactive.spec.ts`, serta plan/hasil reaktif ini.

Diubah pada paket reaktif: backend business `contracts.py`, `oasis_bridge.py`,
`structured.py`, `swarm.py`, `recovery.py`, `service.py`, `reviews.py`,
`reporting.py`; tests runtime/reviews/swarm API/partial recovery. Frontend
`api/business.ts`, `SwarmDiscussion.tsx` dan CSS/test, `BusinessAnalysisPage.tsx`,
`BusinessReport.tsx`, `SpecialistContinuation.tsx` dan test. Dokumentasi:
backend README, implementation status, trial guide dan surface brief Impeccable.
Tidak ada migrasi atau perubahan key/model pada `.env` utama.

## Lokasi dan batas

Raw JSON, event, HTML dan verification berada pada folder lokal yang diabaikan
Git di `backend/data/demo/`; audit/test XML di `backend/data/runtime-audit/`.
Demo lama `analysis_be0b0b4f0ccf44889954` dan ZIP-nya tetap tersedia. Run lama
selesai secara teknis, tetapi 7/10 pesan hampir sama, sehingga bukan bukti debat
swarm berkualitas. Membaca atau mengunduh hasil tersimpan tidak memanggil model.

Konflik sumber BPS, volume/profit yang belum diketahui, evaluasi manusia,
retensi/purge dan pengujian skala ratusan peserta tetap belum terselesaikan.

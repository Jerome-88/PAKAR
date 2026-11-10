# Contoh Pepsodent dengan AI sungguhan — 1 November 2026

Buka pada akun pemilik:
<http://localhost:5173/business/analyses/analysis_07c300937f2749f48279?tab=swarm>.
Run ini menyimpan **31 pesan dari 10 stakeholder**, empat review specialist AI,
dan delapan bagian laporan. Model pesan dan review final adalah
[Qwen3 235B Instruct](https://openrouter.ai/qwen/qwen3-235b-a22b-2507)
melalui DeepInfra. Membaca hasil tidak memanggil model.

## Input dan alur

Input berasal dari `Dokumen.pdf`, transkripsi visual grafik halaman 7 yang sudah
dilabeli, serta IDEA 2 versi pertama. Ide dan file asli tidak diubah.
`Skenario-diskusi-Pepsodent-asumsi.txt` ditambahkan sebagai **asumsi simulasi
yang disusun asisten**, bukan temuan PDF atau spesifikasi baru dari pengguna.
File itu menjelaskan peran hipotetis pemasok, kompetitor, regulator dan mitra.
Hipotesis dua nozzle dari chat uji tidak diterapkan ke versi ide.

Sepuluh stakeholder terdiri dari pengelola, pemasok, kompetitor, peninjau
regulasi, mitra distribusi dan lima lensa customer. Ditambah empat specialist,
ada 14 peran pada alur ini. Discovery LLM tidak selesai/valid; profil memakai
fallback kontekstual yang ditandai secara eksplisit. **Ucapan diskusi dan keempat
review specialist berasal dari panggilan AI sungguhan**, bukan fixture.

| Tahap | Run | Hasil |
| --- | --- | --- |
| Qwen 30B/Nebius | `analysis_bbdb1cc33dd948a2873b` | Dihentikan: repetitif dan salah membaca arti 52% |
| Qwen 235B/GMICloud | `analysis_dd618c13c3544fe3a34c` | Gagal karena provider tidak memiliki kapasitas; tidak ada diskusi |
| Qwen 235B/DeepInfra | `analysis_33bcd797598d4a27a07d` | 31 pesan; dibatalkan pengaman biaya sebelum laporan |
| Review eksplisit | `analysis_07c300937f2749f48279` | Memakai ulang 31 pesan, empat reviewer selesai, laporan **partial** |

Run awal tetap dibatalkan. Pemulihan memvalidasi ulang urutan, referensi,
akses dan delta state setiap event. Hash hasil mentah dan hash event disimpan
pada lineage; tidak ada giliran stakeholder, discovery atau BPS baru ketika
mereview. Evidence eksternal yang tidak tersimpan akibat pembatalan tidak
dipulihkan. Hasil mentah dan event sumber tidak ditimpa.

## Contoh hasil dan batas mutu

- Customer kemudahan penggunaan mempertanyakan pemilihan rasa pagi/malam.
- Customer keandalan meminta kepastian stok; mitra meminta kejelasan trial pack
  dan dukungan edukasi sebelum mengusulkan distribusi.
- Klaim bahwa perubahan warna menunjukkan kebersihan dipertanyakan karena
  bukti korelasi klinis belum tersedia pada input.
- Harga, HPP, biaya tetap dan volume belum tersedia; kalkulator mempertahankan
  profit dan break-even sebagai **unknown**, bukan menciptakan angka.

Ada 26 balasan, 12 pasangan saling membalas dan empat balasan antarcustomer.
Dua pesan ditandai hampir sama; tiga pertanyaan belum mendapat jawaban penerima.
Seluruh posisi akhir **undecided**, bukan persetujuan peluncuran.
Indikator struktur tersebut tidak mengukur kebenaran atau kedalaman argumen.

Pembacaan manual masih menemukan pengulangan, jawaban operator yang kembali
menanyakan bukti, Finance AI yang melebar ke isu klinis, dan ucapan customer
yang menyebut alternatif merek sebagai sudah terbukti tanpa sumber. Legal AI
menyebut ketentuan BPOM tanpa sumber resmi dalam konteks. Itu **belum
terverifikasi**. Lolos kontrak/referensi tidak membuktikan klaim tersebut.
Demo ini memperlihatkan alur nyata; belum merupakan debat mendalam atau
rekomendasi bisnis yang telah divalidasi. Laporan menandai semua finding AI
sebagai `NEEDS_VALIDATION`.

## Biaya yang sudah settle

Pengguna mengizinkan tambahan pemakaian asal saldo tidak habis. Batas kerja
akhir diumumkan sebesar **USD 0.04** untuk seluruh percobaan hari ini.
Pengaman pertama menghentikan diskusi di bawah batas awal USD 0.03; review
dilanjutkan dengan batas yang dinaikkan tanpa mengulang diskusi.

| Pemakaian | USD |
| --- | ---: |
| Percobaan Qwen 30B | 0.00799380 |
| Percobaan kapasitas GMICloud, delta key teramati | 0.00000000 |
| Diskusi Qwen 235B, delta key teramati | 0.01857456 |
| Empat review Qwen 235B, biaya provider | 0.00413154 |
| **Total delta key teramati** | **0.03069990** |
| **Sisa limit key** | **0.140729608** |

Usage key naik dari 0.028570492 ke 0.059270392 setelah settlement. Usage individual
untuk panggilan yang terputus dapat tetap unknown; delta key tidak mengubahnya
menjadi usage per-call yang diketahui. Konfigurasi utama `.env` tetap Nemo;
Qwen hanya dipilih pada proses run ini. Tidak ada retry inference otomatis.

## Perbaikan dan verifikasi

Prompt diskusi baru menerima kutipan terbatas dengan urutan sumber, judul,
penyebut angka, lensa peran dan ucapan terbarunya. Angka preferensi dibedakan
dari hasil uji produk. Sumber dideduplikasi; maksimum 20 kutipan/2.400 karakter,
1.200 karakter per dokumen, dan 320 karakter per kutipan dengan penanda potongan.
Klaim unit economics privat tetap disaring. Dokumen/pesan tetap untrusted data.

Quick run baru menggunakan `document_grounding=true` dan versi prompt `pakar-1.7`.
Snapshot lama tanpa flag mempertahankan request compact lama. Run live di atas
dibuat saat pengujian sebelum flag versi tersebut dibakukan; metadata aslinya
masih `pakar-1.6` dan tidak ditulis ulang. Paket menyimpan catatan ini untuk
membedakan eksperimen dengan default akhir.

Batas API token dapat dinaikkan secara eksplisit hingga 300.000 untuk cohort
lebih besar; default quick tetap 100.000, maksimum persona quick tetap 12.
Ini batas token, bukan batas dolar. Pengaman biaya pada percobaan ini berada
di runner audit; bukan fitur pembatas saldo global dalam aplikasi.

Endpoint specialist-review menerima `recover_cancelled=true` secara eksplisit.
Tanpa flag, run yang dibatalkan tetap tidak dapat dilanjutkan. Pemulihan ditolak
jika jejak validasi menunjukkan review mungkin sudah dimulai, agar tidak membeli
ulang review yang billing-nya tidak diketahui. Owner check, nonce, deduplikasi
sumber, lease dan satu attempt tetap berlaku.

- Full backend sebelum pemulihan/flag terakhir: **285 passed, 2 skipped**.
- Regresi akhir recovery, continuation, discussion, quick dan chat: **43 passed**.
- OASIS terpasang terhadap provider HTTP lokal: pengujian grounded choice lulus;
  memeriksa sumber/identitas dan penyaringan quote biaya tanpa inference berbayar.
- `git diff --check` lulus. Frontend tidak diubah pada pekerjaan ini.
- HTML hasil aktual dibuka di Chromium tanpa error JavaScript atau request
  eksternal. Desktop tidak overflow; HTML ekspor masih overflow pada viewport
  mobile 390px. Ini batas presentasi ekspor, bukan kegagalan inference.

Berkas aplikasi berubah: backend business `agents.py`, `contracts.py`,
`dialogue_protocol.py`, `oasis_bridge.py`, `repository.py`, `service.py`;
tests `test_business_discussion.py`, `test_business_partial_recovery.py`,
`test_business_runtime.py`. Tidak ada perubahan library OASIS/CAMEL atau migrasi.

Artefak lokal berada di `backend/data/demo/pepsodent-review-2026-11-01/`;
paket offline `backend/data/demo/PAKAR-Pepsodent-AI-2026-11-01.zip` memuat HTML,
JSON, diskusi sumber, verifikasi dan catatan ini. Log/XML berada di
`backend/data/runtime-audit/2026-11-01/`. Kredensial tidak disertakan dalam paket.

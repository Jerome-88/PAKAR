# Demo AI tersimpan — 31 Oktober 2026

## Hasil yang dapat dipresentasikan

Run akhir **analysis_be0b0b4f0ccf44889954** berstatus **completed** dan tersimpan
pada akun/proyek sumber. Buka hasil ini untuk demo berikutnya, tanpa membuat
analisis baru:

http://localhost:5173/business/analyses/analysis_be0b0b4f0ccf44889954

| Pemeriksaan | Hasil aktual |
| --- | --- |
| Model dan provider | mistralai/mistral-nemo melalui Parasail |
| Stakeholder | 5, termasuk 2 perspektif customer |
| Ronde | 2 |
| Interaksi tervalidasi | 10 diterima, 0 ditolak |
| Balasan customer ke pesan customer lain | 1, diperiksa melalui penulis `reply_to` |
| Specialist | Market, Finance, Legal/Compliance, Risk selesai dan lolos pemeriksaan |
| Finding / bagian laporan | 8 kandidat finding / 8 bagian PRD |
| Evidence BPS | CONFLICTING; angka tidak dipromosikan menjadi data tervalidasi |
| Profit | belum diketahui; volume tidak tersedia |

Diskusi dan Market/Finance berasal dari run **analysis_d4b91997958e4ff68769**.
Run akhir meneruskan hanya Legal/Risk dengan dua panggilan baru. Hasil
Market/Finance, diskusi, profil dan ID persona dipakai kembali secara eksplisit.
Status completed menyatakan alur komputasi selesai, bukan keberhasilan bisnis
atau kebenaran hipotesis pasar.

## Berkas demo offline

Folder lokal (diabaikan Git karena berisi hasil/input bisnis):
`backend/data/demo/live-2026-10-31-final/`.

- `report.html`: laporan mandiri yang dapat dibuka offline.
- `README-DEMO.md`: urutan presentasi dan penjelasan provenance.
- `report.json`, `analysis.json`, `events.json`: hasil terstruktur dan jejak.
- `verification.json`, `replay-verification.json`, `offline-verification.json`,
  `credit-verification.json`: bukti kelengkapan, pembacaan ulang dan biaya.
- `checksums.json`: SHA-256 berkas; screenshot desktop/mobile ikut disimpan.

Paket salinan: `backend/data/demo/PAKAR-demo-AI-2026-10-31.zip`.
Isi ZIP dan checksumnya diperiksa. Scan exact-byte credential pada berkas paket:
**0 kecocokan**. Tidak ada cookie atau API key disimpan dalam paket.

Laporan HTML dibuka dengan browser dalam mode offline: delapan section tersedia,
**0 request jaringan**. Tiga kali pembacaan analisis/report/export melalui service
tidak membuat job baru dan tidak mengubah hasil tersimpan.

## Perbaikan yang diperlukan oleh tes live

1. Tambah pilihan eksplisit `PAKAR_OPENROUTER_PROVIDER_ORDER` dan catat provider
   aktual pada call ledger. Konfigurasi lokal dipilih `['Parasail']` setelah probe
   structured output berhasil, dengan model dan cap harga tetap. Fallback tetap
   dimatikan. Ini memakai [provider routing resmi OpenRouter](https://openrouter.ai/docs/guides/routing/provider-selection).
   Keberhasilan rute ini tidak membuktikan semua 429 lama disebabkan provider yang
   sama, atau menjamin provider selalu tersedia.
2. Setelah runtime mengembalikan semua usage lengkap, alokasi review memakai
   total token aktual. Reservasi admission lama tetap dicatat terpisah sebagai
   `dispatched_reservation_upper_bound`. Usage tidak lengkap tetap konservatif;
   hard-killed runtime tetap mereservasi seluruh alokasi fase. Pada percobaan
   pertama, 51.351 token masih direservasi setelah 30.133 token aktual dilaporkan,
   sehingga reviewer terakhir tidak mendapat admission.
3. Tambah template referensi balasan dari pesan yang terlihat: target, thread,
   visibility, reply ID dan causal parent konsisten. Tidak ada konten, opini atau
   sikap yang ditentukan template; model tetap menulis responsnya. Validator
   tidak dilonggarkan. Satu balasan tanpa causal parent pada percobaan pertama
   tetap tersimpan sebagai aksi ditolak.
4. Tambah `retry_failed=true` pada operasi specialist-review yang dipanggil
   eksplisit. Review yang selesai dan lolos validator diwariskan; hanya role
   tersisa yang dipanggil. Findings/disagreements yang sah dan provenance sumber
   ikut dipertahankan. Biaya baru hanya menghitung panggilan lanjutan. Pengiriman
   ganda tetap memakai job yang sama. Tidak ada retry inference otomatis.
5. Simpan `Retry-After` numerik yang dibatasi jika provider mengirimkannya;
   exception mentah, header credential dan isi request tetap tidak diekspor.

## Percobaan yang dipertahankan

| Run | Hasil |
| --- | --- |
| analysis_98a2353e7fb242b9b87d | 2 ronde selesai, 1 aksi ditolak; 3 specialist selesai, Risk tidak mendapat admission token |
| analysis_d4b91997958e4ff68769 | 10/10 aksi valid; Market/Finance selesai, Legal HTTP 429, Risk tidak mendapat admission setelah reservasi panggilan yang usage-nya tidak diketahui |
| analysis_be0b0b4f0ccf44889954 | diskusi dan review sah dipakai kembali; Legal/Risk selesai; hasil akhir completed |

Percobaan parsial serta raw result awal **analysis_c52e1c736c9c4356a0b7** tidak
ditimpa. Source lineage akhir berisi 16 panggilan model, 15 dengan cost terlapor;
subtotal terlapornya USD 0,00212448. Ini terpisah dari percobaan pertama dan
probe rute; cost panggilan gagal tidak dianggap nol.

## Biaya

Model dan batas rute tetap: prompt/completion maksimal USD 0,03 per juta token,
request USD 0; tidak ada top-up atau kenaikan limit key.

Pemeriksaan **16:37:36 WIB, 31 Oktober 2026**:

- Selisih usage key sepanjang permintaan ini: **USD 0,00378228**.
- Sisa limit key: **USD 0,187867758**.
- Penggunaan kumulatif sejak preflight awal sesi: **USD 0,010589131**, di bawah
  plafon USD 0,02 yang tidak direset.

Angka ini observasi waktu pemeriksaan. Ledger per-call tetap menyatakan unknown
jika provider tidak mengirim usage/cost, meski saldo key sudah diperiksa.

## Verifikasi

Final full backend: **254 passed, 2 skipped**. Runtime/usage/template guards
diuji dengan SDK OASIS/CAMEL terpasang dan HTTP provider lokal, terpisah dari
percobaan live. Suite routing 32 pass; runtime/schema/recovery 19 pass;
usage/reply 28 pass; explicit retry/diagnostics 9 pass. Guard mencakup isolasi
owner, freeze input, pemakaian ulang accepted reviews, tidak ada tagihan ulang
role yang selesai, idempotency, validator rejection dan konservasi unknown usage.

Final guard setelah full suite: **13 passed**, termasuk deadline pada resume
yang hanya menandai role tertunda sebagai gagal, tanpa mengubah status review
warisan yang sudah sah. Full suite tidak diulang setelah penyesuaian guard ini.

Full frontend: **76 passed**. Build produksi dan ESLint lulus; warning ukuran
bundle lama tetap ada. `git diff --check` lulus.

Browser UI: **1 passed**, paid endpoints dimock, mencakup failed-only continuation,
empat status selesai dan dua label review warisan. Offline HTML nyata diuji
terpisah tanpa jaringan. Finish review UI: **ship**, tidak ada material fixes.

## Batas yang tetap berlaku

Evidence BPS masih memiliki konflik, volume/profit belum diketahui, dan kegunaan
kandidat finding masih membutuhkan penilaian manusia. Satu demo tersimpan yang
selesai bukan benchmark akurasi, representasi customer nyata, uji skala atau
jaminan run live berikutnya akan bebas rate limit.

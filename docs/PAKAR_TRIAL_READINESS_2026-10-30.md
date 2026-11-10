# Kesiapan percobaan input/output — 30 Oktober 2026

Catatan historis: alur review manual pada paket ini kemudian disederhanakan atas
permintaan pengguna. Default terkini adalah upload → keterangan → analisis dengan
persona otomatis. Gunakan [panduan terkini](PAKAR_TRIAL_GUIDE.md) dan
[hasil alur otomatis](PAKAR_AUTOMATIC_FLOW_2026-10-30.md).

Lingkup prioritas: buat contoh transparan dan dapat diedit, lalu periksa hasil
input/output melalui beberapa kasus sebelum pengguna mencoba. Tidak ada inference
berbayar baru, penghapusan data nyata, perubahan reducer ataupun benchmark LLM.

## Yang dikerjakan

- Halaman input memakai tiga contoh sintetis dengan konteks dan wilayah tepat.
  Isi proposal dapat dibaca, diubah, dan diunduh; teks yang diedit menjadi sumber
  yang diunggah. Tidak ada hasil analisis yang sudah diisi di template.
- Penjelasan singkat membedakan ekstraksi, review, fixture dan OASIS live.
  Discovery live juga dinyatakan memakai model; memilih fixture kemudian tidak
  membuat panggilan discovery sebelumnya menjadi gratis.
- Lima kasus melewati API/PostgreSQL: tiga industri, harga hilang, dan harga
  aktif bertentangan. Rujukan sumber, unknown profit, delapan bagian laporan,
  perbandingan scenario dan immutability baseline diperiksa.
- [Panduan percobaan](PAKAR_TRIAL_GUIDE.md) mencakup alur hemat tanpa inference,
  contoh TXT, hasil hitungan yang bisa diperiksa, cara kerja dan pertanyaan review.

## Hasil pemeriksaan kasus

| Kasus | Hasil yang diperiksa |
|---|---|
| Kopi | Fixture BEP 2.000 → 3.000 pada match-price −20% |
| Roti | Fixture BEP 3.000 → 12.000 pada biaya supplier +50% yang diterima |
| Jasa | Fixture BEP 300 tetap 300 pada shock regulasi tanpa input biaya baru |
| Harga belum ada | Margin, BEP dan profit tetap null di perhitungan/laporan |
| Dua harga aktif | HTTP 422; run tidak dibuat sampai konflik input diselesaikan |

Kelima pemeriksaan kasus lulus. Nilai rujukan adalah ekspektasi aritmetika
kondisional, bukan ground truth untuk stakeholder, relevansi risiko, atau kualitas
respons model. Rubrik/corpus independen masih draft.

## Penilaian awal output live yang sudah tersedia

Tidak ada run live baru di paket ini. Laporan serial sebelumnya dibaca kembali:
temuan supplier memiliki rantai penawaran/penerimaan; hitungan 2.400 → 4.000
sesuai input hasil negosiasi; demand/profit tetap unknown; konflik BPS tetap
terlihat; satu finding dengan perbandingan nominal salah sudah ditahan.

Keterbatasan yang masih terlihat: pengulangan tema demand/BEP di beberapa finding,
campuran bahasa, serta kandidat risiko yang masih umum. Jumlah finding tidak
dipakai sebagai ukuran keberhasilan. Catatan ini review internal terhadap artefak
yang sama, bukan evaluasi bisnis independen atau bukti keunggulan multi-agent.

## Verifikasi

- Backend suite terdampak: **30 passed**, mencakup lima kasus baru, simulasi,
  pemeriksaan finding dan laporan. Backend source tidak diubah paket ini.
- Frontend: **65 passed**, ESLint dan production build lulus. Build masih
  memperingatkan bundle utama lebih dari 500 kB; pemecahan bundle di luar lingkup.
- Browser regresi report: **1 passed**. Browser input/edit/upload/report final:
  **1 passed** (8,9 detik). Proposal diedit dari biaya Rp12.000 menjadi Rp15.000;
  API menerima sumber yang sama dan laporan fixture menghasilkan BEP 2.400,
  profit null, delapan bagian, serta provenance fixture. Tidak ada discovery live.
  Percobaan awal tes memakai locator label select yang tidak cocok; diperbaiki
  menjadi combobox berdasarkan accessible name, tanpa perubahan logika aplikasi.
  Screenshot input desktop/mobile diperiksa; halaman mobile tidak overflow.
- Impeccable mechanical scan pada halaman berubah: tidak ada temuan.

## Berkas

Diubah: `frontend/src/pages/Business/BusinessPages.tsx`.
Baru: `businessExamples.json` di folder yang sama,
`backend/tests/test_business_trial_cases.py`,
`frontend/tests/e2e/business-trial.spec.ts`, lima TXT di `docs/examples/`,
serta panduan dan catatan kesiapan ini. Mesin simulasi dan konfigurasi API tetap.

Retensi/penghapusan data bisnis, klarifikasi metode/periode BPS dan evaluasi
independen tetap terbuka. Paket ini mempersiapkan percobaan lokal dengan data
sintetis; tidak menyatakan siap menerima dokumen rahasia atau siap produksi.

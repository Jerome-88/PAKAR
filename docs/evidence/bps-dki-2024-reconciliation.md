# Rekonsiliasi pengeluaran DKI Jakarta 2024

Status: **CONFLICTING — definisi/periode survei perlu klarifikasi**. Diperiksa
30 Oktober 2026; bukan keputusan bahwa salah satu sumber pasti keliru.

| Aspek | Seri WebAPI | Publikasi pembanding |
| --- | --- | --- |
| Wilayah | DKI Jakarta, domain 3100 | DKI Jakarta, total provinsi |
| Indikator | Variabel 144, total golongan pengeluaran dan kelompok barang | Rata-rata pengeluaran per kapita sebulan |
| Tahun | Period code 124 berlabel 2024 | 2024; sumber Susenas Maret |
| Satuan | Rupiah | Rupiah |
| Nilai | 2.764.456 | 2.794.485 |

Selisih nilai API terhadap publikasi: **−30.029 Rupiah**. Metadata API yang dibaca
belum cukup menjelaskan apakah periode survei/definisi agregasinya identik.
Karena itu kedua nilai disimpan dan scalar `value` ditahan (`null`) ketika
evidence memiliki status CONFLICTING. Tidak ada penggantian angka diam-diam dan
tidak ada promosi menjadi VERIFIED.

Publikasi resmi:
[Pola Konsumsi Penduduk Provinsi DKI Jakarta 2024](https://jakarta.bps.go.id/id/publication/2025/05/28/25d0e82d1e8200b26f04d2d5/pola-konsumsi-penduduk-provinsi-dki-jakarta-2024.html),
BPS Provinsi DKI Jakarta, rilis 28 Mei 2025, nomor publikasi 31000.25022,
katalog 3201010.31. **Tabel 2.1, halaman cetak 15 / halaman PDF 31** memuat
baris provinsi dan kolom 2024. Pemeriksaan memakai teks dan render halaman yang
sama, bukan cuplikan mesin pencari saja.

PDF diperoleh dari URL unduh yang dikembalikan endpoint publication resmi melalui
key pengguna. Key tidak dikirim ke mesin pencari atau disimpan bersama bukti.
SHA-256 PDF: `ef56c9bd9306f255c8069ee3912c50ff3ba69638c0e36330d40814a99b03ff17`.
Metadata pembanding tanpa kredensial ada di [JSON kurasi](bps-dki-2024-comparison.json).
PDF/render dan respons API berada di audit lokal yang diabaikan Git.

Sumber API yang direkam memakai domain 3100 / var 144 / th 124, dengan
`vervar=9`, `turvar=163`, `turtahun=0`, kunci observasi `91441631240`.
Nilai makanan 1.096.758 ditambah bukan makanan 1.667.698 cocok dengan total API,
tetapi konsistensi penjumlahan internal tidak menyelesaikan konflik publikasi.

Baseline/scenario lama mempertahankan snapshot PARTIAL yang tersedia saat run.
Konfigurasi pembanding berlaku untuk analisis baru. Kesamaan angka di masa depan
hanya menjadi numeric match; applicability pada claim usaha tetap harus dinilai.
Tidak ada angka di sini yang dianggap sebagai demand, volume penjualan, profit,
atau jaminan kelayakan bisnis.

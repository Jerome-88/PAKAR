# Rencana diskusi swarm reaktif

Tujuan: percakapan berkembang ketika peserta ditanya atau ditantang, dengan
kepentingan persona yang eksplisit dan pemeriksaan pengulangan. Tidak memaksakan
konflik, persetujuan atau perubahan sikap. Demo lama tetap immutable.

1. Tambah kebijakan `reactive-v2` untuk quick run baru; snapshot lama tetap
   memakai round-robin. Agenda memberi semua peserta kesempatan dasar, lalu
   memprioritaskan penerima pertanyaan/tanggapan dalam batas follow-up per ronde.
2. Tambah intent percakapan dan validasi penerima/causal reply, tetap memakai
   reducer finansial dan OASIS/CAMEL yang ada. Simpan alasan dispatch dan pemicu.
3. Kirim kepentingan/constraints/knowledge persona sendiri serta tugas diskusi
   konkret dalam prompt. Pertahankan batas akses privat dan ketidakpastian data.
4. Ukur struktur dialog dua arah, balasan antarcustomer, kemiripan pesan dan
   pertanyaan tanpa balasan penerima. Ini indikator pemeriksaan, bukan penilaian
   kebenaran semantik atau skor kelayakan bisnis. Laporan/UI menampilkan batasnya.
5. Uji starvation, batas follow-up, privat, causal replay, legacy, deadline/token,
   SDK lokal dan UI. Perbaiki reservasi berjalan hanya bila usage diketahui.
6. Jalankan satu diskusi AI baru dengan batas biaya sesi yang sama; simpan hasil
   dan kualitas yang teramati secara jujur. Bila reviewer perlu dilanjutkan,
   pakai accepted-review reuse yang sudah ada, tanpa mengulang diskusi.

Plafon awal USD 0,02 kumulatif sejak preflight awal. Setelah empat percobaan
Nemo, pengguna secara eksplisit menyetujui tambahan maksimal USD 0,01 untuk
uji Qwen: plafon baru USD 0,03 kumulatif. Saldo key bukan izin untuk menghabiskan
seluruh kredit. Setiap dispatch baru memeriksa usage key yang sudah settle,
batas harga provider, batas token dan headroom. Tidak ada inference otomatis
saat membuka demo. Hasil dan keterbatasan dicatat di
[hasil swarm reaktif](PAKAR_REACTIVE_SWARM_RESULTS_2026-10-31.md).

# Gap retensi dan penghapusan data bisnis

Diperiksa 30 Oktober 2026. Ini rencana operasional, bukan klaim purge bisnis
sudah tersedia atau otorisasi untuk menghapus data pengguna nyata.

## Kondisi saat ini

- Business projects/claims/personas/analyses/events memiliki tabel tersendiri.
  Lifecycle dan purge legacy tidak otomatis mencakup tabel tersebut.
- `business_projects` belum memiliki status archive/pending-delete/deadline purge.
  Business API belum menyediakan alur lifecycle penghapusan yang setara legacy.
- Upload memakai namespace `business/{project_id}/...`. Runtime OASIS memiliki
  namespace per attempt yang terpisah, termasuk artifacts ketika run terhenti.
- Parent guard menghentikan proses anak saat worker mati; ini tidak menghapus
  file, database runtime atau backup.
- Pemulihan lease live bersifat terminal tanpa paid retry otomatis. Tes lokal
  membuktikan orphan SDK berhenti, stale worker tidak boleh publish/renew lease,
  dan worker pengganti tidak mengambil ulang job yang exhausted.

## Paket implementasi berikutnya

1. Tambahkan lifecycle bisnis dengan revisi/ownership checks dan masa pending-delete
   yang eksplisit. Archive/deletion harus menolak atau menangani job aktif sebelum
   berpindah status; cancellation tidak boleh langsung dianggap proses sudah mati.
2. Simpan manifest runtime/artifact sejak namespace dibuat, termasuk attempt yang
   gagal sebelum menghasilkan `result.json`. Jangan hanya mencari file dari hasil
   run yang completed.
3. Buat purge idempotent bertahap: file/storage dan runtime artifacts, lalu record
   terkait. Kegagalan storage tidak boleh dilaporkan sebagai purge sukses. Baseline
   dan scenario serta foreign keys harus ditangani konsisten.
4. Sebelum operasi file rekursif, resolve absolute path dan pastikan setiap target
   tetap di root penyimpanan/namespace proyek yang dituju. Tolak symlink/path
   traversal atau lokasi yang bukan milik proyek tersebut.
5. Verifikasi di database/storage uji terisolasi: ownership lintas akun, active-job
   conflict, pembatalan pending-delete, partial purge, retry, stale lease,
   restart di tengah purge dan artifacts yang tidak punya hasil akhir.
6. Tetapkan serta uji kebijakan backup/restore, audit minimal yang dipertahankan
   dan penghapusan salinan ekspor. Kebijakan provider inference eksternal harus
   diperiksa terpisah; purge lokal tidak membuktikan data pada provider dihapus.

Dokumen perusahaan sungguhan tetap berada di luar klaim kesiapan paket demo ini.
Tidak ada penghapusan rekursif, migrasi lifecycle baru atau perubahan ownership
data nyata dilakukan pada pemeriksaan ini.

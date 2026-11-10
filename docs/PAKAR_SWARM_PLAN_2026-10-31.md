# Rencana swarm PAKAR — 31 Oktober 2026

Status: implementasi lokal selesai. Bukti dan batas klaim di
[hasil pengembangan](PAKAR_SWARM_RESULTS_2026-10-31.md). Tidak ada inference berbayar
pada paket ini.

Tujuan: upload dokumen + keterangan langsung menghasilkan diskusi stakeholder
yang dapat dibaca dan ditelusuri, kemudian diperiksa empat specialist. Ini
simulasi perspektif sintetis, bukan survei pasar atau voting kelayakan.

## Paket yang dieksekusi

1. **Kontrak dan kompatibilitas.** Tambah mode swarm berversi. Analisis quick
   baru default empat customer, hingga delapan persona dan tiga ronde. Snapshot
   lama/manual mempertahankan interaksi berpasangan. Scenario mewarisi input,
   profil, ID dan aturan baseline.
2. **Kelompok persona.** Perluas customer dari profil kontekstual menjadi beberapa
   perspektif kebutuhan/keberatan yang jelas berstatus hipotesis. Tidak mengarang
   demografi atau ukuran segmen. Bekukan identitas sebelum simulasi; avatar tetap
   mengikuti ID. Peran lain tetap memerlukan dukungan konteks dokumen.
3. **Diskusi dan sikap.** Tambah post, reply dan abstain; thread publik/privat,
   rujukan balasan dan validasi akses. Simpan sikap serta alasan dan event yang
   memengaruhinya. Perubahan sikap bukan perubahan angka finansial. Negosiasi dan
   kalkulasi tetap melalui reducer bisnis yang ada.
4. **Runtime dan scheduler.** Gunakan OASIS/CAMEL yang terpasang, dengan adapter
   bisnis thread/state yang divalidasi server. Giliran dibatasi; konteks menyertakan
   pesan yang terlihat dan balasan yang relevan. Berhenti pada batas ronde,
   waktu/token/event atau satu ronde penuh abstain tanpa shock terjadwal tersisa.
   Tidak menghentikan diskusi hanya karena mayoritas sepakat. Tidak menambah
   panggilan model khusus untuk penilaian sikap.
5. **Pemeriksaan dan laporan.** Specialist menerima pesan, rantai sumber dan
   perubahan sikap dalam konteks terbatas yang eksplisit. Laporan delapan bagian
   mempertahankan perbedaan pendapat dan menambah jejak diskusi/posisi sintetis.
6. **Tampilan.** Tambah tab diskusi dengan thread, balasan, identitas/role, label
   akses dan riwayat sikap. Pertahankan form ringkas serta tampilan/graph lama.
7. **Verifikasi.** Tes penolakan cross-thread/akses privat, referensi palsu,
   perubahan sikap, tidak ada perubahan finansial dari opini, budget/cancellation,
   snapshot lama dan scenario. Uji runtime SDK terpasang memakai provider lokal;
   browser upload → swarm fixture → report/scenario. Catat hasil dan batas klaim.

## Kriteria selesai

- Lebih dari satu customer dapat saling membalas dalam thread yang sama.
- Pesan privat tidak masuk prompt peserta di luar thread.
- Sikap boleh tetap berbeda; setiap perubahan memiliki alasan/rujukan.
- UI dan laporan menampilkan diskusi aktual serta identitas konsisten.
- API lama/snapshot baseline lama tidak berubah diam-diam.
- Default tests dan verifikasi paket ini tidak memakai kredit LLM. Tidak ada
  reset plafon USD 0,02 sesi sebelumnya atau automatic paid retry.

Di luar paket: skala ratusan persona, klaim representasi populasi, benchmark
independen, penyelesaian konflik statistik BPS, dan lifecycle purge bisnis.

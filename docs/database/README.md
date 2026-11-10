# ERD PAKAR / RekaKebijakan

Diagram diturunkan dari definisi SQLAlchemy di `backend/app/database.py` dan
`backend/app/business/tables.py` pada 9 November 2026. Tidak ada koneksi ke
database aktif; diagram menggambarkan schema pada kode workspace.

| Diagram | Gambar PNG | SVG yang bisa diperbesar | Sumber Mermaid |
| --- | --- | --- | --- |
| Sederhana: 9 tabel bisnis, kolom dan relasi inti | [PNG](erd-simple.png) | [SVG](erd-simple.svg) | [Mermaid](erd-simple.mmd) |
| Ringkasan semua tabel, menampilkan kolom kunci | [PNG](erd-overview.png) | [SVG](erd-overview.svg) | [Mermaid](erd-overview.mmd) |
| Detail bisnis PAKAR dan infrastruktur bersama | [PNG](erd-business.png) | [SVG](erd-business.svg) | [Mermaid](erd-business.mmd) |
| Seluruh tabel dan seluruh kolom | [PNG](erd-full.png) | [SVG](erd-full.svg) | [Mermaid](erd-full.mmd) |

## Cara membaca

- Versi sederhana berfokus pada pengguna, proyek, dokumen, klaim, persona,
  analisis, ide, revisi ide, dan percakapan. Hanya kolom penting dan delapan
  relasi utama yang ditampilkan. FK langsung dari klaim/revisi ide ke proyek,
  serta relasi `business_analyses.baseline_id`, disembunyikan untuk mengurangi
  kepadatan. Detail lengkap tetap tersedia pada diagram lain.
- Nama besar pada versi sederhana adalah label bahasa Indonesia; nama tabel
  aslinya tercantum tepat di bawahnya. `(JSON)` berarti isi tersimpan dalam
  kolom JSONB; struktur di dalamnya tidak dirinci.
- PK: primary key. Beberapa kolom bertanda PK pada tabel yang sama membentuk
  primary key gabungan, misalnya `business_events(analysis_id, sequence)`.
- FK: foreign key yang benar-benar dideklarasikan pada schema.
- UQ: kolom dengan unique constraint atau unique index satu kolom. Unique index
  gabungan dan check constraint tidak dirinci pada gambar.
- `?`: kolom nullable. Kolom tanpa tanda ini wajib terisi.
- Garis menghubungkan primary/referenced key induk dengan FK anak. Dua garis
  pada ujung relasi berarti satu; lingkaran berarti nol/opsional; kaki tiga
  berarti banyak. FK yang juga unik membatasi jumlah anak menjadi nol atau satu.
- Hijau: bisnis PAKAR. Biru: akses dan infrastruktur. Cokelat: simulasi kebijakan.
- `JSONB` adalah kolom dokumen JSON; field di dalamnya tidak dirinci sebagai kolom.

## Batas cakupan dan hal yang perlu diperhatikan

- `simulations.project_id` bertipe string wajib, tetapi belum memiliki
  `ForeignKey("projects.id")` pada kode. Karena itu tidak digambar sebagai relasi
  yang ditegakkan database. Tidak ada schema aplikasi yang diubah oleh ekspor ini.
- ID runtime eksternal, ID resource polimorfik, dan referensi di dalam JSONB tidak
  otomatis digambar sebagai FK.
- Diagram bisnis hanya memuat relasi dengan kedua tabel berada di cakupannya.
  FK `jobs.simulation_id` dan `jobs.run_id` terlihat sebagai kolom; garisnya
  tersedia pada diagram lengkap.
- `jobs` memiliki check constraint tepat satu target di antara `simulation_id`,
  `analysis_id`, dan `business_chat_turn_id`; nullability masing-masing kolom
  tidak berarti ketiganya boleh kosong bersamaan.
- Tabel `provider_spend_accounts` / `provider_spend_reservations` belum memiliki
  FK ke pengguna atau analisis; diagram mempertahankan kondisi kode tersebut.

## Memperbarui diagram

Jalankan dari root repository dengan Python yang memiliki SQLAlchemy:

```powershell
python scripts/export-erd.py
```

Perintah ini memperbarui `.dot`, `.mmd`, dan `manifest.json`. Render gambar dari
DOT dengan Graphviz (binary `dot` harus tersedia):

```powershell
dot -Tsvg docs/database/erd-simple.dot -o docs/database/erd-simple.svg
dot -Tpng docs/database/erd-simple.dot -o docs/database/erd-simple.png
dot -Tsvg docs/database/erd-overview.dot -o docs/database/erd-overview.svg
dot -Tpng docs/database/erd-overview.dot -o docs/database/erd-overview.png
dot -Tsvg docs/database/erd-business.dot -o docs/database/erd-business.svg
dot -Tpng docs/database/erd-business.dot -o docs/database/erd-business.png
dot -Tsvg docs/database/erd-full.dot -o docs/database/erd-full.svg
dot -Tpng docs/database/erd-full.dot -o docs/database/erd-full.png
```

SVG disarankan untuk presentasi/cetak dan pemeriksaan detail karena tetap tajam
saat diperbesar. Mermaid dan DOT dapat diedit atau dirender ulang.

# Menjalankan PAKAR pada satu VPS

Panduan per 7 November 2026. Target: VPS Ubuntu 24.04 LTS x86_64 yang bersih, satu domain/subdomain, Docker Compose, dan model AI melalui API. Ini konfigurasi pilot/demo; belum merupakan hasil load test atau audit production menyeluruh.

Paket ini berdiri sendiri. Gunakan `deploy/compose.vps.yaml`, bukan digabung dengan `compose.yaml` atau `compose.full.yaml` yang membuka port development.

```text
Internet -> domain HTTPS -> Caddy :443 -> nginx frontend
                                      -> /backend/ -> FastAPI
                                                     -> PostgreSQL
                                                     -> worker -> OASIS/CAMEL -> LLM API
                                                              -> BPS bila dikonfigurasi
```

Hanya Caddy menerbitkan port 80/443. Database, API, worker dan frontend nginx tidak menerbitkan port host. PAKAR kini membuka workspace bersama tanpa login (`AUTH_REQUIRED=false`); origin/host tetap mengikuti domain dan worker berjalan terpisah. Data database, upload dan sertifikat memakai volume persisten.

## 1. Persiapan

- VPS dengan akses SSH/sudo. Untuk pilot kecil, 2 vCPU/4 GB RAM dapat menjadi titik awal; 4 vCPU/8 GB memberi ruang lebih untuk build dependency runtime. Ini perkiraan perencanaan, bukan kapasitas yang telah dibenchmark. Sediakan SSD sekitar 50–60 GB dan pantau disk saat build.
- Tidak diperlukan GPU server karena inference dikirim ke provider API.
- Domain/subdomain yang DNS-nya bisa diatur, misalnya `pakar.domainanda.com`.
- Source code terbaru, kunci LLM valid dan saldo yang mencukupi batas run + cadangan kredit.
- BPS key dan katalog indikator jika retrieval BPS akan dipakai. Key saja belum cukup.

Semua perintah server di bawah dijalankan pada Bash Ubuntu, bukan PowerShell Windows.

## 2. Pastikan source terbaru tersedia

Workspace pengembangan saat panduan dibuat memiliki banyak perubahan lokal. `git clone` hanya mengambil perubahan yang sudah di-commit/push. Review dan masukkan perubahan aplikasi serta folder `deploy/` ke branch deployment terlebih dahulu. Jangan commit `.env`, API key, `.venv`, upload atau backup database.

Contoh pada VPS, setelah branch yang dipilih sudah berisi perubahan terbaru:

```bash
sudo apt update
sudo apt install -y git ca-certificates curl
sudo mkdir -p /opt/pakar
sudo chown "$USER":"$(id -gn)" /opt/pakar
git clone https://github.com/Jerome-88/PAKAR.git /opt/pakar
cd /opt/pakar
```

Jika folder sudah berisi checkout, gunakan checkout/pull branch yang benar; jangan clone menimpa folder. Repository private memerlukan akses GitHub/deploy key pada server.

## 3. Install Docker Engine dan Compose

Ikuti repository apt resmi Docker. Pada server bersih:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
```

Sumber: https://docs.docker.com/engine/install/ubuntu/

## 4. Arahkan domain dan buka akses jaringan

Tambahkan A record untuk hostname pilihan menuju IPv4 publik VPS. Contoh: record `pakar` pada domain `domainanda.com` menuju IP VPS. Buat AAAA hanya bila IPv6 server memang dikonfigurasi dan dapat dijangkau. Untuk setup pertama, gunakan DNS langsung agar penerbitan sertifikat tidak tercampur konfigurasi proxy lain.

Izinkan TCP 80/443 dan port SSH yang dipakai pada firewall provider maupun server. Jika SSH menggunakan port default 22, contoh UFW:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

Jika SSH memakai port lain, izinkan port itu sebelum mengaktifkan UFW. Port 80/443 harus belum dipakai web server lain; konfigurasi ini mengasumsikan VPS bersih. Tidak perlu membuka 5432, 5001 atau 5173 ke internet.

## 5. Isi environment VPS

```bash
cd /opt/pakar
cp deploy/vps.env.example deploy/.env
chmod 600 deploy/.env
openssl rand -hex 32
nano deploy/.env
```

Ganti setidaknya:

- `PAKAR_DOMAIN`: hostname saja, misalnya `pakar.domainanda.com`.
- `POSTGRES_PASSWORD`: password hex yang baru digenerate; jangan pakai placeholder. Hex menghindari masalah encoding URL database.
- `LLM_API_KEY`: kunci provider yang sesuai dengan `LLM_BASE_URL`. Untuk Groq,
  gunakan `https://api.groq.com/openai/v1`, model `openai/gpt-oss-20b`, dan isi
  `FREE_AI_KEY` sebagai alternatif. Jangan kirim key ke frontend atau chat.
- `LLM_MODEL`: model yang ingin dipakai; template mengikuti konfigurasi Qwen demo.
- `PAKAR_OPENROUTER_PROVIDER_ORDER` dan `PAKAR_OPENROUTER_MAX_PRICE`: template mempertahankan kebijakan route/cap demo. Itu plafon kebijakan, bukan jaminan harga/ketersediaan saat deployment. Route yang tidak memenuhi akan gagal tanpa fallback.
- `BPS_API_KEY` dan `PAKAR_BPS_INDICATORS`: salin katalog indikator yang memang sudah diperiksa jika BPS dipakai. `[]` membuat sumber BPS unavailable, bukan data perkiraan.

Template mempertahankan cap run USD 0,01 dan cadangan kredit USD 0,10. Saldo harus cukup untuk keduanya. Peningkatan batas dilakukan sengaja setelah menilai kebutuhan, bukan otomatis agar run bisa lolos.

`deploy/.env` adalah file Compose untuk VPS. Jangan langsung menyalin seluruh `backend/.env` lokal: alamat database, port dan path Windows tidak cocok di container. Konfigurasi bersama API/worker sudah diatur di Compose. Nilai rahasia tetap disimpan di server; jangan mengunggah keluaran `docker compose config` yang menampilkan environment penuh. Untuk validasi gunakan `config --quiet`.

## 6. Pilih: instalasi baru atau membawa demo lama

**Instalasi baru:** lanjut ke langkah 7. Akun, proyek dan analisis akan mulai kosong.

**Membawa demo Pepsodent:** source code saja tidak membawa akun, chat atau hasil analisis. Restore database PostgreSQL serta storage upload yang cocok. Tidak perlu menjalankan AI ulang hanya untuk menampilkan hasil lama.

Gunakan database tujuan yang masih kosong. Restore berikut tidak dimaksudkan untuk menimpa database VPS yang sudah berisi data. Selesaikan/batalkan run dan chat aktif serta hentikan worker sumber sebelum backup; job antrean yang ikut dicopy dapat dijalankan worker tujuan.

Pada laptop Windows, contoh dump dari container lokal yang dipakai pengembangan:

```powershell
docker exec pakar-migration-postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl --file=/tmp/pakar.dump'
docker cp pakar-migration-postgres:/tmp/pakar.dump ./pakar.dump
```

Cara ini menghindari redirect binary dump melalui PowerShell. Transfer `pakar.dump` dan folder upload aktual dari storage lokal melalui SCP/SFTP ke `deploy/migration/` di VPS. Pada setup lokal biasa, storage ada di `backend/data/uploads`; periksa konfigurasi sumber sebelum menyalin. Tidak perlu mengunggah seluruh `backend/data` yang berisi audit dan artefak development.

Setelah source dan environment siap, pada VPS:

```bash
sudo sh deploy/pakar.sh build backend frontend
sudo sh deploy/pakar.sh up -d database
sudo sh deploy/pakar.sh ps
```

Tunggu database healthy. Sebelum migrasi/aplikasi dimulai, restore dump:

```bash
sudo sh deploy/pakar.sh cp deploy/migration/pakar.dump database:/tmp/pakar.dump
sudo sh deploy/pakar.sh exec -T database sh -c 'pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/pakar.dump'
sudo sh deploy/pakar.sh up -d backend
```

`up backend` menjalankan migrasi yang diperlukan sebelum API. Setelah backend sehat dan folder `deploy/migration/uploads` berisi salinan storage:

```bash
sudo sh deploy/pakar.sh cp deploy/migration/uploads/. backend:/app/data/uploads/
sudo sh deploy/pakar.sh exec -T --user root backend chown -R 10001:10001 /app/data/uploads
```

Jaga struktur storage key, misalnya `uploads/business/...`, tetap sama. Kemudian lanjut `up -d` pada langkah 7. Buka workspace langsung dan periksa hasil/chat/sumber; kepemilikan lama tetap tersimpan tetapi tidak menghalangi akses bersama. Tampilan hasil tersimpan tidak memerlukan pemulihan seluruh runtime simulation database lama; kemampuan melanjutkan runtime lama lintas mesin harus diuji terpisah.

## 7. Build dan jalankan

```bash
sudo sh deploy/pakar.sh config --quiet
sudo sh deploy/pakar.sh build backend frontend
sudo sh deploy/pakar.sh up -d
sudo sh deploy/pakar.sh ps
sudo sh deploy/pakar.sh logs --tail=100 migrate backend worker frontend edge
```

Build pertama memasang runtime OASIS/CAMEL dan dapat memerlukan waktu/disk lebih banyak daripada build frontend. Tidak perlu menginstal Node, Python API atau runtime OASIS secara manual pada host ketika memakai image ini.

Service `migrate` seharusnya selesai dengan exit code 0; itu one-shot yang normal. Service lain harus berjalan dan healthcheck API/frontend/database lulus. Caddy mengurus sertifikat dan pengalihan HTTP ke HTTPS setelah DNS dan akses 80/443 siap.

## 8. Periksa dari internet

Ganti hostname contoh:

```bash
curl -I https://pakar.domainanda.com/
curl --fail https://pakar.domainanda.com/backend/ready
```

Kemudian buka browser:

1. Halaman HTTPS dapat diakses tanpa peringatan sertifikat.
2. Workspace langsung terbuka tanpa register/login, termasuk setelah reload.
3. Proyek hasil restore, graf, Executive Summary dan chat lama dapat dibaca.
4. Upload dokumen kecil dan penyimpanan ide berhasil.
5. Kirim satu chat AI secara eksplisit bila memang akan menguji provider; langkah ini memakai kredit. Jangan langsung menjalankan swarm besar untuk mengecek koneksi.
6. Bila perlu, lakukan satu analisis kecil dengan budget yang disetujui dan periksa log worker, sumber serta usage.

Pada mode bersama, `/backend/api/auth/me` mengembalikan identitas workspace dengan HTTP 200 tanpa cookie; endpoint ini dipertahankan untuk bootstrap UI, bukan gerbang login. Bila masih menerima 401, periksa apakah backend sudah memakai versi baru dan `AUTH_REQUIRED=false`. Origin domain tetap perlu cocok agar request tulis tidak ditolak. `/backend/ready` adalah pemeriksaan kesiapan, bukan bukti provider AI/BPS pasti tersedia.

## 9. Operasional setelah online

Jalankan `sudo sh deploy/pakar.sh logs --tail=100 worker backend` untuk diagnosis antrean/AI. Pantau `df -h`, `sudo docker system df` dan `sudo docker stats --no-stream`. Jangan menghapus volume untuk mengatasi disk penuh tanpa backup.

Deployment ini memakai ruang kerja bersama tanpa auth. Setiap orang yang dapat membuka URL dapat membaca/mengedit proyek dan mengirim permintaan AI memakai key bersama, dalam batas guard yang berlaku. Ini bukan billing per pengguna atau ruang data privat antar-pengunjung.

Backup database dari Bash VPS, misalnya ke direktori privat di luar repo:

```bash
sudo mkdir -p /srv/pakar-backups
sudo chmod 700 /srv/pakar-backups
sudo sh deploy/pakar.sh exec -T database sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl --file=/tmp/pakar-backup.dump'
sudo sh deploy/pakar.sh cp database:/tmp/pakar-backup.dump /srv/pakar-backups/pakar-backup.dump
```

Salin juga volume upload/artefak `backend_data` dengan konsistensi yang sesuai, simpan salinan off-server, serta uji restore. Nama berkas contoh di atas menimpa backup contoh sebelumnya; untuk jadwal rutin gunakan nama bertanggal dan retensi yang ditetapkan. Database saja tidak menggantikan backup berkas asli.

Update setelah perubahan source telah direview, tersedia di branch dan backup dibuat. Contoh ini memakai maintenance singkat agar aplikasi lama tidak berjalan saat skema berubah:

```bash
git pull --ff-only
sudo sh deploy/pakar.sh build backend frontend
sudo sh deploy/pakar.sh stop edge frontend worker backend
sudo sh deploy/pakar.sh run --rm migrate
sudo sh deploy/pakar.sh up -d
sudo sh deploy/pakar.sh ps
```

Migrasi one-shot yang sudah completed tidak boleh diasumsikan otomatis dijalankan ulang pada setiap update. Perintah `run --rm migrate` di atas menjalankan migrasi secara eksplisit; jika gagal, periksa log sebelum menyalakan aplikasi lagi. Rencanakan kompatibilitas schema/rollback.

Untuk menghentikan sementara, `sudo sh deploy/pakar.sh stop`. Hindari `down -v` karena menghapus volume database/upload/sertifikat. Jangan mengganti nama volume pada environment setelah data terisi. Mengubah `POSTGRES_PASSWORD` pada file environment juga tidak otomatis mengubah password role dalam database yang sudah ada.

Workflow `.github/workflows/deploy-backend.yml` yang lama memakai Compose lain dan hanya backend. Jangan arahkan konfigurasi workflow lama ke VPS ini tanpa menyesuaikan jalur, file environment dan layanan frontend/edge.

## 10. Validasi paket dan batas bukti

Konfigurasi Compose telah diperiksa tanpa menyalakan stack: enam service, hanya port 80/443 dipublikasikan, cookie Secure, worker terpisah, environment AI/guard API-worker sama. Backend `.dockerignore` juga mengecualikan environment/venv runtime bersarang agar tidak ikut masuk build context.

Pemeriksaan parser nginx (`nginx -t`) dan Caddy (`caddy validate`) dalam container validasi keduanya lolos. Shell helper juga diperiksa sintaksnya. Belum ada deployment ke VPS, penerbitan sertifikat domain, restore data ke server tujuan atau full image build PAKAR yang dilakukan oleh panduan ini. Tidak ada panggilan LLM berbayar.

Referensi resmi:

- Docker Ubuntu: https://docs.docker.com/engine/install/ubuntu/
- Compose production: https://docs.docker.com/compose/how-tos/production/
- Published ports: https://docs.docker.com/engine/network/port-publishing/
- Caddy HTTPS: https://caddyserver.com/docs/automatic-https
- PostgreSQL dump/restore: https://www.postgresql.org/docs/17/backup-dump.html

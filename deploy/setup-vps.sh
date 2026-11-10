#!/bin/sh
# ==============================================================================
# PAKAR - Initial VPS Host Setup Script for Ubuntu 24.04 LTS (x86_64)
# Configures 4 GB swap, kernel swappiness, UFW firewall, and Docker Engine.
# Run as root or with sudo: sudo sh deploy/setup-vps.sh
# ==============================================================================

set -eu

if [ "$(id -u)" -ne 0 ]; then
  printf '%s\n' "This script must be run as root or with sudo." >&2
  exit 1
fi

printf '\n==> [1/5] Updating system packages...\n'
apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  gnupg \
  git \
  ufw \
  fail2ban \
  tar

printf '\n==> [2/5] Configuring 4 GB Swap space (Critical for 2 GB RAM VPS)...\n'
if [ ! -f /swapfile ]; then
  fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  if ! grep -q '/swapfile' /etc/fstab; then
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
  fi
  printf '4 GB Swap file created and activated.\n'
else
  printf 'Swap file already exists at /swapfile.\n'
fi

# Set optimal swappiness for low-RAM server
sysctl vm.swappiness=10
echo 'vm.swappiness=10' > /etc/sysctl.d/99-pakar-swap.conf

printf '\n==> [3/5] Installing Official Docker Engine & Compose plugin...\n'
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.asc ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
fi

UBUNTU_CODENAME=$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
ARCH=$(dpkg --print-architecture)

cat <<EOF > /etc/apt/sources.list.d/docker.sources
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME}
Components: stable
Architectures: ${ARCH}
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt-get update -y
apt-get install -y --no-install-recommends \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin

systemctl enable --now docker
docker version >/dev/null 2>&1 && printf 'Docker installed successfully.\n'
docker compose version >/dev/null 2>&1 && printf 'Docker Compose plugin installed successfully.\n'

printf '\n==> [4/5] Configuring UFW Firewall...\n'
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status verbose

printf '\n==> [5/5] Ensuring project and backup directories exist...\n'
mkdir -p /opt/pakar
mkdir -p /srv/pakar-backups
chmod 700 /srv/pakar-backups

REAL_USER=${SUDO_USER:-$USER}
if [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
  chown "$REAL_USER":"$(id -gn "$REAL_USER")" /opt/pakar
  usermod -aG docker "$REAL_USER" || true
  printf 'Added %s to docker group. (Log out and back in to apply group membership).\n' "$REAL_USER"
fi

printf '\n==================================================================\n'
printf ' VPS host setup completed successfully!\n'
printf ' Next steps:\n'
printf '  1. cd /opt/pakar\n'
printf '  2. cp deploy/vps.env.example deploy/.env\n'
printf '  3. Fill out deploy/.env (domain, postgres password, API keys)\n'
printf '  4. Run: sudo sh deploy/pakar.sh up -d database\n'
printf '  5. Run: sudo sh deploy/pakar.sh run --rm migrate\n'
printf '  6. Run: sudo sh deploy/pakar.sh up -d\n'
printf '==================================================================\n'


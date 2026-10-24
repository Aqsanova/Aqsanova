#!/usr/bin/env bash
# Ubuntu VPS bootstrap for Node.js apps (external MySQL only)
# Review SSH_PORT and NODE_MAJOR before running.
set -Eeuo pipefail

SSH_PORT="${SSH_PORT:-22}"
NODE_MAJOR="${NODE_MAJOR:-24}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root: sudo bash install.sh"
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This script supports Ubuntu/Debian systems using apt."
  exit 1
fi

echo "==> Updating package lists and upgrading installed packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get -y upgrade

echo "==> Installing common tools, Nginx, firewall, and external-MySQL client..."
apt-get install -y \
  ca-certificates curl gnupg git unzip zip rsync \
  build-essential python3 make g++ \
  nginx ufw \
  default-mysql-client

echo "==> Installing Node.js ${NODE_MAJOR}.x LTS and npm..."
install -d -m 0755 /etc/apt/keyrings
curl -fsSL "https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key" \
  | gpg --dearmor --yes -o /etc/apt/keyrings/nodesource.gpg
chmod 0644 /etc/apt/keyrings/nodesource.gpg
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
  > /etc/apt/sources.list.d/nodesource.list
apt-get update
apt-get install -y nodejs

echo "==> Installing PM2 globally..."
npm install --global pm2

echo "==> Installing Certbot for Let's Encrypt with Nginx..."
apt-get install -y certbot python3-certbot-nginx

echo "==> Configuring UFW rules..."
# IMPORTANT: If SSH uses a custom port, set SSH_PORT before running this script.
ufw allow "${SSH_PORT}/tcp"
ufw allow 80/tcp
ufw allow 443/tcp
if ufw status | grep -q "Status: active"; then
  echo "UFW is already active; rules added."
else
  echo "Enabling UFW after allowing SSH port ${SSH_PORT}, HTTP, and HTTPS..."
  ufw --force enable
fi

echo "==> Enabling Nginx..."
systemctl enable --now nginx

echo "==> Configuring PM2 to start on reboot..."
pm2 startup systemd -u root --hp /root >/tmp/pm2-startup-command.txt 2>&1 || true
cat /tmp/pm2-startup-command.txt
echo
echo "Note: Run 'pm2 save' after starting your apps to save the process list."

echo
echo "==> Installation complete."
echo "Node:    $(node --version)"
echo "npm:     $(npm --version)"
echo "PM2:     $(pm2 --version)"
echo "MySQL:   $(mysql --version)"
echo "Nginx:   $(nginx -v 2>&1)"
echo
echo "Next steps:"
echo "  1. Point your domain's DNS A record to this VPS IP."
echo "  2. Configure an Nginx server block for your domain and app port."
echo "  3. Obtain SSL with: sudo certbot --nginx -d example.com -d www.example.com"
echo "  4. In each app directory, install its own dependencies (e.g. npm ci)."
echo "  5. For an app using MySQL, add the driver to that project: npm install mysql2"
echo "  6. Start the app with PM2, then run: pm2 save"
echo
echo "Security: configure your external MySQL server to allow this VPS IP only,"
echo "use a dedicated database user with least privilege, and keep credentials out of Git."

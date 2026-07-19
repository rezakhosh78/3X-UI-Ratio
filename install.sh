#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_VERSION="0.1.10"
APP_DIR="/opt/3xui-ratio"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGED_SOURCE=""

if [[ "$(readlink -f "$SOURCE_DIR")" == "$(readlink -f "$APP_DIR" 2>/dev/null || echo "$APP_DIR")" ]]; then
  STAGED_SOURCE=$(mktemp -d)
  cp -a "$SOURCE_DIR"/. "$STAGED_SOURCE"/
  SOURCE_DIR="$STAGED_SOURCE"
  trap '[[ -n "$STAGED_SOURCE" ]] && rm -rf "$STAGED_SOURCE"' EXIT
fi

red='\033[0;31m'; green='\033[0;32m'; yellow='\033[1;33m'; cyan='\033[0;36m'; reset='\033[0m'
info(){ echo -e "${cyan}[3X-UI Ratio]${reset} $*"; }
ok(){ echo -e "${green}[OK]${reset} $*"; }
warn(){ echo -e "${yellow}[!]${reset} $*"; }
die(){ echo -e "${red}[ERROR]${reset} $*" >&2; exit 1; }

[[ ${EUID:-$(id -u)} -eq 0 ]] || die "Run the installer as root: sudo bash install.sh"
command -v apt-get >/dev/null || die "This installer supports Ubuntu and Debian systems."

install_docker(){
  if command -v docker >/dev/null && docker compose version >/dev/null 2>&1; then
    return
  fi
  info "Installing Docker and Docker Compose..."
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl openssl docker.io
  if ! apt-get install -y docker-compose-v2; then
    apt-get install -y docker-compose-plugin || die "Docker Compose installation failed."
  fi
  systemctl enable --now docker
}

install_docker

if [[ -d "$APP_DIR" ]]; then
  warn "$APP_DIR already exists."
  read -r -p "Reinstall or upgrade this installation? [y/N]: " reinstall
  [[ "${reinstall:-N}" =~ ^[Yy]$ ]] || exit 0
  if [[ -f "$APP_DIR/docker-compose.yml" ]]; then
    docker compose --project-directory "$APP_DIR" -f "$APP_DIR/docker-compose.yml" down || true
  fi
  cp -a "$APP_DIR/data" "/tmp/3xui-ratio-data-backup-$$" 2>/dev/null || true
fi

read -r -p "Web panel port [8088]: " ratio_port
ratio_port=${ratio_port:-8088}
[[ "$ratio_port" =~ ^[0-9]+$ ]] && ((ratio_port >= 1 && ratio_port <= 65535)) || die "Invalid port."

read -r -p "Administrator username [admin]: " admin_user
admin_user=${admin_user:-admin}
[[ "$admin_user" =~ ^[A-Za-z0-9_.@-]+$ ]] || die "Username may contain only letters, numbers, dots, underscores, @, and hyphens."

while true; do
  read -r -s -p "Administrator password (minimum 8 characters): " admin_password
  echo
  [[ ${#admin_password} -ge 8 ]] && break
  warn "The password is too short."
done

read -r -p "Update package URL (optional, press Enter to skip): " update_url
read -r -p "Use secure cookies over HTTPS only? [y/N]: " secure_cookie
cookie_secure=false
[[ "${secure_cookie:-N}" =~ ^[Yy]$ ]] && cookie_secure=true

info "Copying application files..."
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"
cp -a "$SOURCE_DIR"/. "$APP_DIR"/
rm -f "$APP_DIR/.env"
mkdir -p "$APP_DIR/data" "$APP_DIR/backups"

if [[ -d "/tmp/3xui-ratio-data-backup-$$" ]]; then
  cp -a "/tmp/3xui-ratio-data-backup-$$"/. "$APP_DIR/data"/ || true
  rm -rf "/tmp/3xui-ratio-data-backup-$$"
fi

session_secret=$(openssl rand -hex 48)
encryption_key=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n')
admin_password_b64=$(printf '%s' "$admin_password" | base64 -w0)

cat > "$APP_DIR/.env" <<ENV
RATIO_BIND=0.0.0.0
RATIO_PORT=$ratio_port
ADMIN_USERNAME=$admin_user
ADMIN_PASSWORD_B64=$admin_password_b64
SESSION_SECRET=$session_secret
ENCRYPTION_KEY=$encryption_key
DATABASE_URL=sqlite:////data/ratio.db
COOKIE_SECURE=$cookie_secure
TRUSTED_HOSTS=*
SYNC_DEFAULT_INTERVAL=60
UPDATE_URL=$update_url
ENV

chmod 600 "$APP_DIR/.env"
chown -R 10001:10001 "$APP_DIR/data"
chmod 750 "$APP_DIR/data"
chmod +x "$APP_DIR/scripts/3xui-ratio" "$APP_DIR/install.sh"
cp "$APP_DIR/scripts/3xui-ratio" /usr/local/bin/3xui-ratio
chmod 755 /usr/local/bin/3xui-ratio

info "Building and starting the container..."
docker compose --project-directory "$APP_DIR" -f "$APP_DIR/docker-compose.yml" build
docker compose --project-directory "$APP_DIR" -f "$APP_DIR/docker-compose.yml" up -d

server_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
ok "3X-UI Ratio was installed successfully."
echo "Panel URL: http://${server_ip:-SERVER-IP}:$ratio_port"
echo "Administrator: $admin_user"
echo "Terminal manager: sudo 3xui-ratio"
warn "For public access, place the panel behind HTTPS and then set COOKIE_SECURE=true."

#!/usr/bin/env bash
set -Eeuo pipefail

REPO="rezakhosh78/3x-ui-Ratio"
GITHUB_API="https://api.github.com/repos/${REPO}/releases/latest"
TMP_DIR="$(mktemp -d -t 3xui-ratio-installer.XXXXXXXX)"
ARCHIVE="${TMP_DIR}/3xui-ratio.tar.gz"
EXTRACT_DIR="${TMP_DIR}/release"

red='\033[0;31m'
green='\033[0;32m'
yellow='\033[1;33m'
cyan='\033[0;36m'
reset='\033[0m'

info() { echo -e "${cyan}[3X-UI Ratio]${reset} $*"; }
ok()   { echo -e "${green}[OK]${reset} $*"; }
warn() { echo -e "${yellow}[!]${reset} $*"; }
die()  { echo -e "${red}[ERROR]${reset} $*" >&2; exit 1; }

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    die 'Run as root:
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/rezakhosh78/3x-ui-Ratio/main/install.sh)"'
fi

if ! command -v apt-get >/dev/null 2>&1; then
    die "This installer currently supports Ubuntu and Debian-based systems."
fi

install_requirements() {
    local missing=0

    command -v curl >/dev/null 2>&1 || missing=1
    command -v tar  >/dev/null 2>&1 || missing=1
    command -v grep >/dev/null 2>&1 || missing=1
    command -v sed  >/dev/null 2>&1 || missing=1
    command -v find >/dev/null 2>&1 || missing=1

    if (( missing )); then
        info "Installing required packages..."
        apt-get update
        DEBIAN_FRONTEND=noninteractive apt-get install -y \
            ca-certificates curl tar grep sed findutils
    fi
}

get_latest_release_url() {
    local release_json download_url

    release_json="$(
        curl -fsSL \
            --retry 3 \
            --connect-timeout 15 \
            --max-time 60 \
            -H "Accept: application/vnd.github+json" \
            -H "X-GitHub-Api-Version: 2022-11-28" \
            "$GITHUB_API"
    )" || die "Could not read the latest GitHub release."

    download_url="$(
        printf '%s\n' "$release_json" \
        | grep -Eo '"browser_download_url"[[:space:]]*:[[:space:]]*"[^"]+\.tar\.gz"' \
        | sed -E 's/^.*"([^"]+)"$/\1/' \
        | grep -E '/3X-UI-Ratio-v[^/]+\.tar\.gz$' \
        | head -n 1
    )"

    [[ -n "$download_url" ]] || die \
        "No 3X-UI Ratio .tar.gz asset was found in the latest GitHub release."

    printf '%s' "$download_url"
}

run_release_installer() {
    local download_url project_dir local_installer exit_code

    download_url="$(get_latest_release_url)"

    info "Downloading the latest release..."
    echo "$download_url"

    curl -fL \
        --retry 3 \
        --connect-timeout 15 \
        --max-time 300 \
        "$download_url" \
        -o "$ARCHIVE" \
        || die "Release download failed."

    mkdir -p "$EXTRACT_DIR"

    info "Extracting release package..."
    tar -xzf "$ARCHIVE" -C "$EXTRACT_DIR" \
        || die "The downloaded release archive is invalid."

    # Preferred name for future packages.
    local_installer="$(
        find "$EXTRACT_DIR" -maxdepth 4 -type f \
            \( -name "install-local.sh" -o -name "install.sh" \) \
            -print \
        | sort \
        | head -n 1
    )"

    [[ -n "$local_installer" && -f "$local_installer" ]] || die \
        "No local installer was found inside the release archive."

    project_dir="$(dirname "$local_installer")"

    # A release must contain the application files, not only the bootstrap script.
    [[ -f "$project_dir/docker-compose.yml" ]] || die \
        "The release package does not contain docker-compose.yml beside its installer."

    chmod +x "$local_installer"

    info "Starting the local installer..."
    (
        cd "$project_dir"
        bash "$local_installer"
    )
    exit_code=$?

    if (( exit_code != 0 )); then
        die "The local installer exited with code ${exit_code}."
    fi

    ok "Installation process completed."
}

install_requirements
run_release_installer

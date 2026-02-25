#!/usr/bin/env bash
# =============================================================================
# setup.sh — Checkmk CVE Scanner v4.0 Installationsscript
# =============================================================================
# Legt alle benötigten Verzeichnisse, Dateien und Berechtigungen an.
#
# Ausführung:
#   sudo bash setup.sh                  # Standard-Installation
#   sudo bash setup.sh --user myuser    # Eigenen Scanner-User angeben
#   sudo bash setup.sh --dry-run        # Nur anzeigen, nichts anlegen
#   sudo bash setup.sh --uninstall      # Alles rückgängig machen
# =============================================================================

set -euo pipefail

# ── Farben ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── Standardwerte ─────────────────────────────────────────────────────────────
SCANNER_USER="cve_scanner"
SCANNER_DIR="/opt/cve_scanner"
CONFIG_DIR="/etc/cve_scanner"
LOG_DIR="/var/log/cve_scanner"
CACHE_DIR="/var/cache/cve_scanner"
SCRIPT_SRC="checkmk_cve_scanner.py"
CONFIG_SRC="checkmk_cve_scanner.conf.example"
PKGMAP_SRC="package_map_custom.json"
DRY_RUN=false
UNINSTALL=false

# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
info()    { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*" >&2; }
section() { echo -e "\n${BOLD}${BLUE}── $* ${NC}"; }
dry()     { echo -e "${YELLOW}[DRY]${NC} $*"; }

run() {
    if $DRY_RUN; then
        dry "$*"
    else
        eval "$*"
    fi
}

# ── Argumente parsen ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --user)       SCANNER_USER="$2"; shift 2 ;;
        --dry-run)    DRY_RUN=true; shift ;;
        --uninstall)  UNINSTALL=true; shift ;;
        -h|--help)
            echo "Verwendung: sudo bash setup.sh [--user USER] [--dry-run] [--uninstall]"
            exit 0
            ;;
        *)
            error "Unbekannte Option: $1"
            exit 1
            ;;
    esac
done

# ── Root-Check ────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]] && ! $DRY_RUN; then
    error "Dieses Script muss als root ausgeführt werden."
    echo "  sudo bash setup.sh"
    exit 1
fi

# ── Quelldateien prüfen ───────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

check_source() {
    local file="$SCRIPT_DIR/$1"
    if [[ ! -f "$file" ]]; then
        warn "Quelldatei nicht gefunden: $file (wird übersprungen)"
        echo ""
    else
        echo "$file"
    fi
}

# =============================================================================
# UNINSTALL
# =============================================================================
if $UNINSTALL; then
    section "Deinstallation"

    warn "Folgendes wird GELÖSCHT:"
    echo "  • $SCANNER_DIR"
    echo "  • $CONFIG_DIR"
    echo "  • $LOG_DIR"
    echo "  • $CACHE_DIR"
    echo "  • /etc/cron.d/cve_scanner (falls vorhanden)"
    echo "  • System-User '$SCANNER_USER' (falls vorhanden)"
    echo ""

    if ! $DRY_RUN; then
        read -r -p "Wirklich deinstallieren? [j/N] " confirm
        [[ "$confirm" =~ ^[jJyY]$ ]] || { echo "Abgebrochen."; exit 0; }
    fi

    run "rm -rf '$SCANNER_DIR'"
    run "rm -rf '$CONFIG_DIR'"
    run "rm -rf '$LOG_DIR'"
    run "rm -rf '$CACHE_DIR'"
    run "rm -f /etc/cron.d/cve_scanner"

    if id "$SCANNER_USER" &>/dev/null 2>&1; then
        run "userdel '$SCANNER_USER'"
        info "System-User '$SCANNER_USER' gelöscht"
    fi

    info "Deinstallation abgeschlossen."
    exit 0
fi

# =============================================================================
# INSTALL
# =============================================================================
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   Checkmk CVE Scanner v4.0 — Setup          ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
$DRY_RUN && warn "DRY-RUN Modus — es werden keine Änderungen vorgenommen\n"

# ── 1. System-User anlegen ────────────────────────────────────────────────────
section "System-User"

if id "$SCANNER_USER" &>/dev/null 2>&1; then
    info "User '$SCANNER_USER' existiert bereits"
else
    run "useradd --system --no-create-home --shell /usr/sbin/nologin \
        --comment 'Checkmk CVE Scanner' '$SCANNER_USER'"
    info "System-User '$SCANNER_USER' angelegt"
fi

# ── 2. Verzeichnisse anlegen ──────────────────────────────────────────────────
section "Verzeichnisse"

declare -A DIRS=(
    ["$SCANNER_DIR"]="755"        # Scanner-Script
    ["$CONFIG_DIR"]="750"         # Konfiguration (enthält API-Keys)
    ["$LOG_DIR"]="755"            # Reports (JSON, CSV)
    ["$LOG_DIR/archive"]="755"    # Archiv älterer Reports
    ["$CACHE_DIR"]="750"          # API-Cache
)

for dir in "${!DIRS[@]}"; do
    mode="${DIRS[$dir]}"
    if [[ -d "$dir" ]]; then
        info "Verzeichnis existiert bereits: $dir"
    else
        run "mkdir -p '$dir'"
        info "Verzeichnis angelegt: $dir"
    fi
    run "chmod '$mode' '$dir'"
done

# ── 3. Berechtigungen setzen ──────────────────────────────────────────────────
section "Berechtigungen"

run "chown root:'$SCANNER_USER'  '$SCANNER_DIR'"
run "chown root:'$SCANNER_USER'  '$CONFIG_DIR'"
run "chown '$SCANNER_USER':'$SCANNER_USER' '$LOG_DIR'"
run "chown '$SCANNER_USER':'$SCANNER_USER' '$LOG_DIR/archive'"
run "chown '$SCANNER_USER':'$SCANNER_USER' '$CACHE_DIR'"
info "Berechtigungen gesetzt"

# ── 4. Scanner-Script installieren ───────────────────────────────────────────
section "Scanner-Script"

src=$(check_source "$SCRIPT_SRC")
if [[ -n "$src" ]]; then
    dest="$SCANNER_DIR/checkmk_cve_scanner.py"
    if [[ -f "$dest" ]] && ! $DRY_RUN; then
        run "cp '$dest' '${dest}.bak'"
        warn "Backup angelegt: ${dest}.bak"
    fi
    run "cp '$src' '$dest'"
    run "chmod 750 '$dest'"
    run "chown root:'$SCANNER_USER' '$dest'"
    info "Script installiert: $dest"
else
    warn "checkmk_cve_scanner.py nicht gefunden — bitte manuell nach $SCANNER_DIR kopieren"
fi

# ── 5. Konfigurationsdatei installieren ───────────────────────────────────────
section "Konfiguration"

cfg_dest="$CONFIG_DIR/scanner.conf"
src=$(check_source "$CONFIG_SRC")

if [[ -f "$cfg_dest" ]]; then
    warn "Konfiguration existiert bereits: $cfg_dest (nicht überschrieben)"
    info "Beispiel-Config: $cfg_dest.example"
    [[ -n "$src" ]] && run "cp '$src' '$cfg_dest.example'"
else
    if [[ -n "$src" ]]; then
        run "cp '$src' '$cfg_dest'"
        run "chmod 640 '$cfg_dest'"
        run "chown root:'$SCANNER_USER' '$cfg_dest'"
        info "Konfiguration installiert: $cfg_dest"
        warn "Bitte anpassen: $cfg_dest"
    else
        # Minimale Default-Config anlegen
        if ! $DRY_RUN; then
            cat > "$cfg_dest" << 'CONF'
[checkmk]
omd_root = /omd/sites
sites    =
hosts    =

[osv]
enabled = true

[oss_index]
enabled  = true
username =
token    =

[cisa_kev]
enabled   = true
cache_dir = /var/cache/cve_scanner

[nvd]
enabled        = true
api_key        =
min_cvss_score = 0.0

[cache]
enabled   = true
file      = /var/cache/cve_scanner/api_cache.json
ttl_hours = 24

[package_map]
file =

[output]
directory = /var/log/cve_scanner
CONF
        else
            dry "cat > '$cfg_dest' << 'CONF' ... CONF"
        fi
        run "chmod 640 '$cfg_dest'"
        run "chown root:'$SCANNER_USER' '$cfg_dest'"
        info "Minimal-Konfiguration angelegt: $cfg_dest"
        warn "Bitte anpassen: $cfg_dest"
    fi
fi

# ── 6. Package-Map installieren ───────────────────────────────────────────────
section "Package-Map"

pkgmap_dest="$CONFIG_DIR/package_map_custom.json"
src=$(check_source "$PKGMAP_SRC")

if [[ -f "$pkgmap_dest" ]]; then
    info "Package-Map existiert bereits: $pkgmap_dest (nicht überschrieben)"
else
    if [[ -n "$src" ]]; then
        run "cp '$src' '$pkgmap_dest'"
    else
        if ! $DRY_RUN; then
            echo '{}' > "$pkgmap_dest"
        else
            dry "echo '{}' > '$pkgmap_dest'"
        fi
    fi
    run "chmod 640 '$pkgmap_dest'"
    run "chown root:'$SCANNER_USER' '$pkgmap_dest'"
    info "Package-Map angelegt: $pkgmap_dest"
fi

# ── 7. Log-Dateien anlegen ────────────────────────────────────────────────────
section "Log-Dateien"

log_file="$LOG_DIR/scanner.log"
if [[ -f "$log_file" ]]; then
    info "Log-Datei existiert bereits: $log_file"
else
    run "touch '$log_file'"
    run "chmod 644 '$log_file'"
    run "chown '$SCANNER_USER':'$SCANNER_USER' '$log_file'"
    info "Log-Datei angelegt: $log_file"
fi

# ── 8. Cache-Datei vorbereiten ────────────────────────────────────────────────
section "Cache"

cache_file="$CACHE_DIR/api_cache.json"
if [[ -f "$cache_file" ]]; then
    info "Cache-Datei existiert bereits: $cache_file"
else
    if ! $DRY_RUN; then
        echo '{}' > "$cache_file"
    else
        dry "echo '{}' > '$cache_file'"
    fi
    run "chmod 640 '$cache_file'"
    run "chown '$SCANNER_USER':'$SCANNER_USER' '$cache_file'"
    info "Cache-Datei angelegt: $cache_file"
fi

# ── 9. Python-Abhängigkeiten prüfen ──────────────────────────────────────────
section "Python-Abhängigkeiten"

if command -v python3 &>/dev/null; then
    PYTHON=$(command -v python3)
    info "Python gefunden: $PYTHON ($(python3 --version 2>&1))"
else
    error "python3 nicht gefunden — bitte installieren"
fi

if python3 -c "import requests" &>/dev/null 2>&1; then
    info "requests: installiert"
else
    warn "requests nicht gefunden — installiere..."
    run "pip3 install requests --break-system-packages 2>/dev/null || pip3 install requests"
fi

if python3 -c "import yaml" &>/dev/null 2>&1; then
    info "pyyaml: installiert (YAML Package-Map möglich)"
else
    warn "pyyaml nicht installiert (optional, nur für YAML Package-Map nötig)"
    warn "  pip3 install pyyaml"
fi

# ── 10. Checkmk Site-Zugriffsrechte ──────────────────────────────────────────
section "Checkmk Site-Zugriff"

if [[ -d /omd/sites ]]; then
    sites=$(ls /omd/sites 2>/dev/null || true)
    if [[ -n "$sites" ]]; then
        echo "  Gefundene Sites:"
        for site in $sites; do
            run "usermod -aG '$site' '$SCANNER_USER' 2>/dev/null || true"
            info "  $SCANNER_USER → Gruppe '$site' hinzugefügt"
        done
    else
        warn "/omd/sites existiert, aber keine Sites gefunden"
    fi
else
    warn "/omd/sites nicht gefunden — Checkmk nicht installiert oder falscher Server"
    warn "Berechtigungen später manuell setzen:"
    echo "  sudo usermod -aG <site> $SCANNER_USER"
fi

# ── 11. Cronjob anlegen ───────────────────────────────────────────────────────
section "Cronjob"

cron_file="/etc/cron.d/cve_scanner"
if [[ -f "$cron_file" ]]; then
    info "Cronjob existiert bereits: $cron_file (nicht überschrieben)"
else
    if ! $DRY_RUN; then
        cat > "$cron_file" << CRON
# Checkmk CVE Scanner — täglich um 02:30 Uhr
# API-Keys als Umgebungsvariablen setzen (optional):
# NVD_API_KEY="dein-key"
# OSS_INDEX_USER="user@example.com"
# OSS_INDEX_TOKEN="dein-token"

30 2 * * * $SCANNER_USER /usr/bin/python3 $SCANNER_DIR/checkmk_cve_scanner.py \\
    --config $CONFIG_DIR/scanner.conf \\
    >> $LOG_DIR/scanner.log 2>&1
CRON
    else
        dry "cat > '$cron_file' << CRON ... CRON"
    fi
    run "chmod 644 '$cron_file'"
    info "Cronjob angelegt: $cron_file (täglich 02:30 Uhr)"
    warn "Cronjob ist auskommentiert — bitte API-Keys eintragen und aktivieren"
fi

# ── 12. Zusammenfassung ───────────────────────────────────────────────────────
section "Zusammenfassung"

echo ""
echo -e "${BOLD}Installierte Dateien:${NC}"
echo "  $SCANNER_DIR/checkmk_cve_scanner.py   (750, root:$SCANNER_USER)"
echo "  $CONFIG_DIR/scanner.conf              (640, root:$SCANNER_USER)"
echo "  $CONFIG_DIR/package_map_custom.json   (640, root:$SCANNER_USER)"
echo "  $LOG_DIR/scanner.log                  (644, $SCANNER_USER:$SCANNER_USER)"
echo "  $CACHE_DIR/api_cache.json             (640, $SCANNER_USER:$SCANNER_USER)"
echo "  /etc/cron.d/cve_scanner               (644, root:root)"
echo ""
echo -e "${BOLD}Verzeichnisse:${NC}"
echo "  $SCANNER_DIR       (755, root:$SCANNER_USER)  ← Script"
echo "  $CONFIG_DIR    (750, root:$SCANNER_USER)  ← Konfiguration + API-Keys"
echo "  $LOG_DIR  (755, $SCANNER_USER)        ← Reports + Logs"
echo "  $CACHE_DIR (750, $SCANNER_USER)      ← API-Cache"
echo ""
echo -e "${BOLD}Nächste Schritte:${NC}"
echo -e "  ${YELLOW}1.${NC} Konfiguration anpassen:"
echo "       sudo nano $CONFIG_DIR/scanner.conf"
echo ""
echo -e "  ${YELLOW}2.${NC} Optionale API-Keys eintragen (schnellere Scans):"
echo "       NVD:       https://nvd.nist.gov/developers/request-an-api-key"
echo "       OSS Index: https://ossindex.sonatype.org"
echo ""
echo -e "  ${YELLOW}3.${NC} Testlauf:"
echo "       sudo -u $SCANNER_USER python3 $SCANNER_DIR/checkmk_cve_scanner.py \\"
echo "           --config $CONFIG_DIR/scanner.conf \\"
echo "           --no-nvd --no-oss --list-hosts"
echo ""
echo -e "  ${YELLOW}4.${NC} Erster Scan:"
echo "       sudo -u $SCANNER_USER python3 $SCANNER_DIR/checkmk_cve_scanner.py \\"
echo "           --config $CONFIG_DIR/scanner.conf \\"
echo "           --no-nvd --min-cvss 7.0"
echo ""
echo -e "  ${YELLOW}5.${NC} Cronjob aktivieren:"
echo "       sudo nano /etc/cron.d/cve_scanner"
echo ""

if $DRY_RUN; then
    echo -e "${YELLOW}DRY-RUN: Keine Änderungen wurden vorgenommen.${NC}"
    echo "  Ohne --dry-run erneut ausführen um zu installieren."
fi

echo ""
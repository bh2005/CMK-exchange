# Installation — Checkmk CVE Scanner v4.0

---

## Voraussetzungen

| Anforderung | Minimum | Empfohlen |
|---|---|---|
| Betriebssystem | Debian 11 / RHEL 8 | Debian 12 / RHEL 9 |
| Python | 3.9 | 3.11+ |
| Checkmk | 2.0 | 2.4 |
| RAM | 512 MB | 1 GB |
| Disk | 500 MB (Reports + Cache) | 2 GB |
| Netzwerk | Ausgehend zu OSV/OSS/NVD/CISA | — |

---

## Schnellinstallation

```bash
# 1. Dateien in ein Verzeichnis legen
cd /tmp
# checkmk_cve_scanner.py, setup.sh, checkmk_cve_scanner.conf.example,
# package_map_custom.json müssen im selben Verzeichnis liegen

# 2. Script ausführen
sudo bash setup.sh

# 3. Konfiguration anpassen
sudo nano /etc/cve_scanner/scanner.conf

# 4. Erster Testlauf
sudo -u cve_scanner python3 /opt/cve_scanner/checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    --no-nvd --list-hosts
```

---

## Setup-Script

### Modi

```bash
# Standard-Installation
sudo bash setup.sh

# Vorschau ohne Änderungen (empfohlen vor erster Ausführung)
sudo bash setup.sh --dry-run

# Eigenen Scanner-User verwenden
sudo bash setup.sh --user monitoring

# Deinstallation (löscht alle Verzeichnisse und den System-User)
sudo bash setup.sh --uninstall
```

### Was das Script anlegt

```
/opt/cve_scanner/                     (755  root:cve_scanner)
└── checkmk_cve_scanner.py            (750  root:cve_scanner)

/etc/cve_scanner/                     (750  root:cve_scanner)
├── scanner.conf                      (640  root:cve_scanner)
└── package_map_custom.json           (640  root:cve_scanner)

/var/log/cve_scanner/                 (755  cve_scanner:cve_scanner)
├── scanner.log                       (644  cve_scanner:cve_scanner)
└── archive/                          (755  cve_scanner:cve_scanner)

/var/cache/cve_scanner/               (750  cve_scanner:cve_scanner)
└── api_cache.json                    (640  cve_scanner:cve_scanner)

/etc/cron.d/cve_scanner               (644  root:root)
```

### Berechtigungskonzept

| Verzeichnis | Modus | Grund |
|---|---|---|
| `/etc/cve_scanner/` | `750` | Enthält API-Keys — kein Lesezugriff für andere User |
| `/opt/cve_scanner/` | `755` | Script lesbar, aber nur Gruppe darf ausführen |
| `/var/log/cve_scanner/` | `755` | Reports lesbar für Admins |
| `/var/cache/cve_scanner/` | `750` | Cache nur für Scanner-User |

---

## Python-Abhängigkeiten

```bash
# Pflicht
pip3 install requests

# Optional: YAML-Support für externe Package-Map
pip3 install pyyaml
```

Das Setup-Script prüft `requests` automatisch und installiert es bei Bedarf.

---

## Konfiguration

Die Konfigurationsdatei liegt nach der Installation unter
`/etc/cve_scanner/scanner.conf`. Mindestens `sites` muss gesetzt werden:

```ini
[checkmk]
omd_root = /omd/sites
sites    = production          # ← anpassen
hosts    =                     # leer = alle Hosts

[osv]
enabled = true                 # kostenlos, kein Key

[oss_index]
enabled  = true
username =                     # optional, erhöht Rate-Limit
token    =                     # https://ossindex.sonatype.org

[cisa_kev]
enabled   = true
cache_dir = /var/cache/cve_scanner

[nvd]
enabled        = true
api_key        =               # optional: https://nvd.nist.gov/developers/request-an-api-key
min_cvss_score = 0.0

[cache]
enabled   = true
file      = /var/cache/cve_scanner/api_cache.json
ttl_hours = 24

[package_map]
file =                         # optional: /etc/cve_scanner/package_map_custom.json

[output]
directory = /var/log/cve_scanner
```

---

## Checkmk Site-Zugriffsrechte

Der Scanner-User braucht Lesezugriff auf die Inventory-Dateien der Checkmk Sites.
Das Setup-Script erledigt das automatisch für alle gefundenen Sites.

### Manuell nachträglich

```bash
# Einzelne Site
sudo usermod -aG production cve_scanner

# Mehrere Sites
sudo usermod -aG production cve_scanner
sudo usermod -aG dmz cve_scanner
sudo usermod -aG monitoring cve_scanner

# Prüfen
groups cve_scanner
# Ausgabe: cve_scanner : cve_scanner production dmz monitoring
```

### Inventory-Pfad prüfen

```bash
# Inventory-Dateien müssen vorhanden sein
ls /omd/sites/production/var/check_mk/inventory/ | head -5

# Falls leer: mk_inventory-Plugin auf den Hosts deployen
# In Checkmk: Setup → Agents → Agent plugins → HW/SW Inventory
```

---

## Testlauf

### 1. Hosts auflisten (kein Scan, schnellster Test)

```bash
sudo -u cve_scanner python3 /opt/cve_scanner/checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    --list-hosts
```

Erwartete Ausgabe:
```
[production] — 47 Hosts:
  dbserver01
  webserver01
  ...
```

### 2. Schneller Funktionstest (1 Host, nur OSV)

```bash
sudo -u cve_scanner python3 /opt/cve_scanner/checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    --hosts webserver01 \
    --no-nvd --no-oss \
    --output /tmp/cve_test
```

### 3. Vollständiger erster Scan

```bash
sudo -u cve_scanner python3 /opt/cve_scanner/checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    --no-nvd \
    --min-cvss 7.0 \
    --output /var/log/cve_scanner
```

> **Hinweis:** Der erste Scan ohne NVD dauert 15–30 Minuten.
> Mit NVD und ohne API-Key bis zu 3 Stunden.

---

## Cronjob

Der Cronjob wird vom Setup-Script als `/etc/cron.d/cve_scanner` angelegt
und muss nach dem Eintragen der API-Keys aktiviert werden:

```bash
sudo nano /etc/cron.d/cve_scanner
```

```cron
# Checkmk CVE Scanner — täglich um 02:30 Uhr
NVD_API_KEY="dein-nvd-key"
OSS_INDEX_USER="user@example.com"
OSS_INDEX_TOKEN="dein-oss-token"

30 2 * * * cve_scanner /usr/bin/python3 /opt/cve_scanner/checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    >> /var/log/cve_scanner/scanner.log 2>&1
```

Umgebungsvariablen-Zeilen ohne Wert einfach weglassen — sie sind optional.

### Log überwachen

```bash
# Letzten Scan-Lauf ansehen
tail -100 /var/log/cve_scanner/scanner.log

# Live mitlesen
tail -f /var/log/cve_scanner/scanner.log

# Nur Fehler und Warnungen
grep -E '\[(ERROR|WARNING)\]' /var/log/cve_scanner/scanner.log
```

---

## Aktualisierung

```bash
# Neue Version des Scripts einspielen
sudo cp checkmk_cve_scanner.py /opt/cve_scanner/checkmk_cve_scanner.py
sudo chmod 750 /opt/cve_scanner/checkmk_cve_scanner.py
sudo chown root:cve_scanner /opt/cve_scanner/checkmk_cve_scanner.py

# Cache leeren (empfohlen nach Major-Updates)
sudo -u cve_scanner rm /var/cache/cve_scanner/api_cache.json

# Setup-Script erneut ausführen aktualisiert keine bestehenden Dateien —
# es legt nur fehlende an
sudo bash setup.sh
```

---

## Deinstallation

```bash
# Alles entfernen (Verzeichnisse, User, Cronjob)
sudo bash setup.sh --uninstall

# Nur den Cache löschen
sudo rm -rf /var/cache/cve_scanner/

# Nur den Cronjob deaktivieren
sudo rm /etc/cron.d/cve_scanner
```

---

## Troubleshooting

### Permission denied beim Lesen der Inventory-Dateien

```bash
# Symptom
[ERROR] Inventory nicht lesbar: /omd/sites/production/var/check_mk/inventory/server01

# Fix: Scanner-User zur Site-Gruppe hinzufügen
sudo usermod -aG production cve_scanner

# Neue Gruppe sofort aktiv (ohne Re-Login)
sudo -u cve_scanner python3 /opt/cve_scanner/checkmk_cve_scanner.py --list-hosts
```

### 0 Hosts / 0 Software-Einträge gefunden

```bash
# Inventory-Dateien prüfen
ls -la /omd/sites/production/var/check_mk/inventory/ | wc -l

# Falls leer: mk_inventory-Plugin fehlt
# Checkmk → Setup → Agents → Agent plugins → "HW/SW Inventory" aktivieren
# Dann Discovery auf betroffenen Hosts ausführen
```

### OSS Index Rate Limit (429)

```bash
# Symptom
[WARNING] OSS Index Rate Limit erreicht – warte 60s...

# Fix 1: Kostenlosen Account anlegen
# https://ossindex.sonatype.org → Settings → API Token
# In scanner.conf eintragen:
# username = user@example.com
# token    = dein-token

# Fix 2: OSS Index deaktivieren
python3 checkmk_cve_scanner.py --config scanner.conf --no-oss
```

### Cache liefert veraltete Ergebnisse

```bash
# Cache manuell zurücksetzen
sudo -u cve_scanner rm /var/cache/cve_scanner/api_cache.json

# Oder einmalig ohne Cache scannen
sudo -u cve_scanner python3 /opt/cve_scanner/checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    --no-cache
```

### Python-Modul nicht gefunden

```bash
# requests fehlt
pip3 install requests --break-system-packages

# pyyaml fehlt (nur für YAML Package-Map)
pip3 install pyyaml --break-system-packages
```

---

## Dateiübersicht nach Installation

```
/
├── opt/cve_scanner/
│   └── checkmk_cve_scanner.py      ← Haupt-Script
│
├── etc/
│   ├── cve_scanner/
│   │   ├── scanner.conf             ← Konfiguration (API-Keys hier)
│   │   └── package_map_custom.json  ← Eigene Paket-Mappings
│   └── cron.d/
│       └── cve_scanner              ← Cronjob
│
├── var/
│   ├── log/cve_scanner/
│   │   ├── scanner.log              ← Laufzeit-Log
│   │   ├── cve_report_*.json        ← Reports (JSON)
│   │   ├── cve_report_*.csv         ← Reports (CSV)
│   │   ├── cve_summary_*.csv        ← Host-Zusammenfassung
│   │   └── archive/                 ← Ältere Reports
│   └── cache/cve_scanner/
│       └── api_cache.json           ← API-Cache (24h TTL)
│
└── usr/
    └── sbin/nologin                 ← Shell des cve_scanner-Users
```
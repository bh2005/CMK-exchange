# Checkmk CVE Scanner v4.0 — Local Mode

Läuft **direkt auf dem Checkmk-Server** und liest Inventory-Daten aus dem
Dateisystem. Kein HTTP-Overhead, kein API-User nötig, Multi-Site-fähig.

**Neu in v4.0:** OSS Index + CISA KEV Integration, API-Cache, RAM-effizienter
Generator, versioniertes OSV-Ecosystem-Mapping, externe Package-Map.

---

## Architektur

```
/omd/sites/<site>/var/check_mk/inventory/
  ├── server01        ← Python-Literal-Format (ast.literal_eval)
  ├── server01.gz     ← komprimierte Variante (automatisch erkannt)
  └── ...
         │
         ▼
  CheckmkInventoryReader  ← Generator (RAM-effizient, kein all_software[])
         │
         ├─ OsvClient      → OSV.dev querybatch       (100er Batches, kein Key)
         ├─ OssIndexClient → Sonatype OSS Index        (128er Batches, kostenlos)
         ├─ NvdClient      → NVD API 2.0               (nur Mapping-Pakete, ~10%)
         └─ CisaKevClient  → CISA KEV Feed             (kein Key, gecacht)
                  │
                  ▼
             ApiCache      ← JSON-Cache (24h TTL, 2. Lauf: Minuten statt Stunden)
                  │
                  ▼
             CveMerger     ← OSV + OSS + NVD dedupliziert, höchster Score gewinnt
                  │
                  ▼
          ReportGenerator  → JSON + CSV + Summary
```

---

## Datenquellen im Vergleich

| Quelle | Batch? | Rate Limit | Stärke |
|---|---|---|---|
| **OSV.dev** | ✅ 100er | kein Limit | Debian/Ubuntu-nativ, GHSA, sehr vollständig |
| **OSS Index** | ✅ 128er | ~64/h anonym, mehr mit Account | PURL-basiert, gute Library-Abdeckung |
| **CISA KEV** | ✅ JSON-Feed | kein Limit | Markiert aktiv ausgenutzte CVEs |
| **NVD** | ❌ einzeln | 6s / 0,7s mit Key | Nur für bekannte Pakete (Mapping), ~10% der Pakete |

> **Empfehlung:** OSV + OSS Index + CISA KEV reichen für die meisten Umgebungen.
> NVD ist optional und wird nur für Pakete mit bekanntem Mapping abgefragt.

---

## Installation

```bash
# Scanner-Verzeichnis anlegen
sudo mkdir -p /opt/cve_scanner /etc/cve_scanner /var/log/cve_scanner

# Dateien kopieren
sudo cp checkmk_cve_scanner.py /opt/cve_scanner/
sudo cp checkmk_cve_scanner.conf.example /etc/cve_scanner/scanner.conf

# Optional: eigene Package-Map
sudo cp package_map_custom.json /etc/cve_scanner/

# Konfiguration absichern (enthält ggf. API-Keys)
sudo chmod 640 /etc/cve_scanner/scanner.conf

# Abhängigkeiten installieren
sudo pip3 install requests

# Optional: YAML-Support für Package-Map
sudo pip3 install pyyaml

# Konfiguration anpassen
sudo nano /etc/cve_scanner/scanner.conf
```

---

## Konfiguration (`scanner.conf`)

```ini
[checkmk]
omd_root = /omd/sites
# Kommagetrennt — oder leer für alle Sites automatisch
sites = production, dmz
# Optional: nur bestimmte Hosts
hosts =

[osv]
# OSV.dev – kostenlos, kein Key, 100er Batches
enabled = true

[oss_index]
# Sonatype OSS Index – kostenlos, 128er Batches
# Mit Account: https://ossindex.sonatype.org (erhöht Rate-Limit)
enabled  = true
username =
token    =

[cisa_kev]
# CISA Known Exploited Vulnerabilities – kein Key, kein Limit
# Markiert Findings als aktiv ausgenutzt (höher priorisiert als CVSS allein)
enabled   = true
cache_dir = /tmp

[nvd]
# NVD – nur für Pakete mit bekanntem Mapping (apache, openssl, etc.)
# Ohne Key: 6s/Request. Mit Key: 0,7s/Request
# Key beantragen: https://nvd.nist.gov/developers/request-an-api-key
enabled        = true
api_key        =
min_cvss_score = 0.0

[cache]
# Lokaler API-Cache – beschleunigt Folge-Scans drastisch
# 1. Lauf: 2-3h   →   Folge-Läufe: wenige Minuten
enabled   = true
file      = /tmp/cve_scanner_cache.json
ttl_hours = 24

[package_map]
# Eigene Package-Map-Datei (optional, ergänzt eingebaute Mappings)
# Format: JSON { "debian_paket": ["nvd_product", "nvd_vendor"] }
file =

[output]
directory = /var/log/cve_scanner
```

### OSS Index Account (empfohlen)

Ohne Account ist OSS Index auf ~64 Requests/Stunde limitiert. Mit einem
**kostenlosen** Account gibt es deutlich mehr:

1. Registrieren unter https://ossindex.sonatype.org
2. Token generieren unter "Settings → API Token"
3. In `scanner.conf` eintragen:
   ```ini
   [oss_index]
   username = deine@email.de
   token    = dein-api-token
   ```
   Alternativ via Umgebungsvariablen: `OSS_INDEX_USER`, `OSS_INDEX_TOKEN`

---

## Ausführung

### Manuell

```bash
# Mit Konfigurationsdatei (empfohlen)
python3 /opt/cve_scanner/checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf

# Direkt per CLI — nur High/Critical, nur bestimmte Hosts
python3 /opt/cve_scanner/checkmk_cve_scanner.py \
    --sites production dmz \
    --hosts webserver01 dbserver02 \
    --min-cvss 7.0 \
    --output /var/log/cve_scanner

# Als Site-User (ohne root, nur eigene Site)
su - production
python3 /opt/cve_scanner/checkmk_cve_scanner.py \
    --sites production \
    --output ~/var/cve_reports

# Schnell: nur OSV + CISA KEV, kein NVD, kein OSS Index
python3 checkmk_cve_scanner.py --sites mysite --no-nvd --no-oss

# Ohne Cache (erzwingt frische API-Anfragen)
python3 checkmk_cve_scanner.py --sites mysite --no-cache
```

### Hosts anzeigen (ohne Scan)

```bash
python3 checkmk_cve_scanner.py --sites mysite --list-hosts
```

---

## Cache

Der eingebaute API-Cache verhindert, dass `openssl 3.0.18` bei einem
nächtlichen Scan 200 Mal neu abgefragt wird:

```
1. Lauf (kalter Cache):   ~2-3 Stunden (1.693 unique Pakete x alle Quellen)
2. Lauf (warmer Cache):   ~2-3 Minuten  (Cache-Hits werden übersprungen)
```

Cache-Datei: `/tmp/cve_scanner_cache.json` (konfigurierbar)
TTL: 24 Stunden (konfigurierbar)

```bash
# Cache zurücksetzen (erzwingt vollständigen Neuscan)
rm /tmp/cve_scanner_cache.json

# Oder per Flag
python3 checkmk_cve_scanner.py --config scanner.conf --no-cache

# Eigene TTL und Pfad
python3 checkmk_cve_scanner.py --cache-file /var/cache/cve.json --cache-ttl 48
```

---

## Package-Map anpassen

Die eingebaute Package-Map enthält über 160 Pakete (apache, openssl, nginx,
php, mariadb, docker, etc.). Für eigene Pakete oder Korrekturen:

1. `package_map_custom.json` bearbeiten:
   ```json
   {
     "mein-paket":         ["nvd_produktname", "nvd_vendor"],
     "haproxy-enterprise": ["haproxy",         "haproxy"],
     "custom-webserver":   ["apache_http_server", null]
   }
   ```
   `null` als Vendor = nur Keyword-Suche in NVD.

2. In `scanner.conf` eintragen:
   ```ini
   [package_map]
   file = /etc/cve_scanner/package_map_custom.json
   ```

3. Alternativ per CLI:
   ```bash
   python3 checkmk_cve_scanner.py --package-map /etc/cve_scanner/package_map_custom.json
   ```

Die externe Datei **ergänzt** das eingebaute Mapping — bestehende Einträge
bleiben erhalten, können aber überschrieben werden. YAML wird unterstützt
wenn `pyyaml` installiert ist.

---

## CISA KEV — Aktiv ausgenutzte CVEs

Die CISA "Known Exploited Vulnerabilities"-Liste enthält CVEs, die nachweislich
aktiv in freier Wildbahn ausgenutzt werden. Der Scanner lädt diesen Feed beim
ersten Lauf von CISA und cached ihn lokal (TTL: 1 Stunde).

Findings die in der KEV-Liste stehen werden:
- In der Ausgabe **an erster Stelle** priorisiert (vor reinen CVSS-Scores)
- Als **aktiv ausgenutzt** markiert (`kev_exploited: true` im JSON)
- Auf mindestens **Severity HIGH** hochgestuft (auch wenn CVSS-Score niedrig ist)

```
⚠️  CISA KEV (aktiv ausgenutzt): 3 Findings
```

---

## Cronjob

```bash
sudo crontab -e
```

```cron
# CVE Scan täglich um 02:30 Uhr
30 2 * * * /usr/bin/python3 /opt/cve_scanner/checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    >> /var/log/cve_scanner/scanner.log 2>&1
```

### API Keys sicher übergeben

```cron
30 2 * * * NVD_API_KEY="dein-nvd-key" \
    OSS_INDEX_USER="user@example.com" \
    OSS_INDEX_TOKEN="dein-oss-token" \
    /usr/bin/python3 /opt/cve_scanner/checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    >> /var/log/cve_scanner/scanner.log 2>&1
```

---

## Output-Dateien

Alle Reports werden mit Timestamp im konfigurierten Verzeichnis abgelegt:

| Datei | Inhalt |
|---|---|
| `cve_report_YYYYMMDD_HHMMSS.json` | Vollständiger Report mit Meta, Summary, allen Findings |
| `cve_report_YYYYMMDD_HHMMSS.csv` | Alle Findings als flache Tabelle (Excel / SIEM) |
| `cve_summary_YYYYMMDD_HHMMSS.csv` | Eine Zeile pro Host: Anzahl Critical/High/Medium/Low |

### Felder im JSON/CSV

| Feld | Beschreibung |
|---|---|
| `site` | Checkmk Site-Name |
| `host` | Hostname |
| `software_name` | Paketname |
| `software_version` | Version |
| `cve_id` | CVE-ID (z.B. `CVE-2024-1234`) |
| `severity` | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `NONE` |
| `cvss_score` | CVSS Base Score (0.0–10.0) |
| `source` | `OSV`, `OSS`, `NVD`, `NVD+OSV` |
| `kev_exploited` | `true` = aktiv in CISA KEV ausgenutzt |
| `aliases` | GHSA-IDs, OSV-IDs, weitere Referenzen |

---

## Inventory-Dateiformat

Checkmk speichert Inventory-Daten als Python-Literal unter:
```
/omd/sites/<site>/var/check_mk/inventory/<hostname>
/omd/sites/<site>/var/check_mk/inventory/<hostname>.gz
```

Der Scanner liest beide Varianten automatisch und parst sie sicher mit
`ast.literal_eval` (kein `eval`).

**Checkmk 2.x Struktur (vereinfacht):**
```python
{
  "Nodes": {
    "software": {
      "Nodes": {
        "packages": {
          "Table": {
            "Rows": [                          # Grosses R!
              {"name": "openssl", "version": "3.0.18",
               "package_type": "deb"},
              ...
            ]
          }
        },
        "os": {
          "Attributes": {
            "Pairs": {
              "name": "Debian GNU/Linux 12 (bookworm)",
              "version": "12"
            }
          }
        }
      }
    }
  }
}
```

---

## Berechtigungen

| Ausführung als | Zugriff | Sites |
|---|---|---|
| `root` | Alle Sites | Alle |
| Site-User (`su - mysite`) | Nur eigene Site | `--sites mysite` |
| Dedizierter Scanner-User | Gruppe `<site>` | Nur Mitglieds-Sites |

```bash
sudo useradd -r cve_scanner
sudo usermod -aG production cve_scanner
sudo usermod -aG dmz cve_scanner
```

---

## Troubleshooting

| Problem | Ursache | Lösung |
|---|---|---|
| `Keine Sites gefunden` | `/omd/sites` nicht zugänglich | Als root ausführen oder `--omd-root` setzen |
| `0 Software-Einträge` | Inventory nicht aktiviert | `mk_inventory`-Plugin auf Hosts deployen |
| `Parse-Fehler` | Checkmk 1.x Format | Nur Checkmk 2.x wird unterstützt |
| NVD 404 überall | Normale API-Antwort bei keinen Treffern | Kein Handlungsbedarf (kein Warning mehr) |
| OSS Index 429 | Rate Limit ohne Account | Kostenlosen Account anlegen, Token eintragen |
| OSV keine/falsche Treffer | Falsches Ecosystem | `--verbose`: prüfen ob `Debian:12` statt `Debian` ausgegeben wird |
| Cache liefert veraltete Daten | TTL noch nicht abgelaufen | `rm /tmp/cve_scanner_cache.json` oder `--no-cache` |
| CISA KEV nicht erreichbar | Netzwerk/Proxy | KEV wird gecacht; beim nächsten erfolgreichen Lauf aktualisiert |
| `No module named yaml` | PyYAML fehlt | `pip3 install pyyaml` (nur für YAML Package-Map nötig) |

---

## Changelog

| Version | Änderungen |
|---|---|
| **v4.0** | OSS Index (128er Batch, PURL); CISA KEV (aktiv ausgenutzte CVEs); API-Cache (JSON, 24h TTL); Generator `iter_software()` (RAM-effizient); OSV Ecosystem mit Versionsnummer (`Debian:12`); NVD auf Mapping-Pakete reduziert (~10%); externe Package-Map (JSON/YAML) |
| v3.1 | Package-Name-Mapping (130+ Pakete); NVD 404 als Nicht-Fehler behandelt; Debian-Versions-Bereinigung für NVD |
| v3.0 | Local Mode: Dateisystem statt REST API; Multi-Site; `scanner.conf`; `--list-hosts` |
| v2.0 | OSV.dev Integration; CveMerger; `--no-nvd` / `--no-osv` |
| v1.0 | NVD-only via REST API |
# CLI Usage — Checkmk CVE Scanner v4.0

Aufrufe sortiert von **schnellsten** (warmer Cache, wenige Quellen)
bis **genauesten** (alle Quellen, kein Cache, alle Pakete).

---

## Schnellreferenz

```
python3 checkmk_cve_scanner.py [--config FILE] [OPTIONEN]
```

| Gruppe | Optionen |
|---|---|
| **Sites & Hosts** | `--sites` `--all-sites` `--hosts` `--omd-root` `--list-hosts` |
| **Quellen** | `--no-nvd` `--no-osv` `--no-oss` `--no-kev` `--nvd-key` `--oss-user` `--oss-token` |
| **Filter** | `--min-cvss` |
| **Cache** | `--no-cache` `--cache-file` `--cache-ttl` |
| **Package-Map** | `--package-map` |
| **Output** | `--output` `--verbose` / `-v` |

---

## 1. Schnellster Scan — warmer Cache, nur OSV

```bash
python3 checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    --no-nvd \
    --no-oss
```

**~2–5 Minuten** bei warmem Cache.
OSV.dev als einzige Quelle, CISA KEV-Anreicherung bleibt aktiv.
Ideal für tägliche Routine-Scans wenn der Cache noch frisch ist.

---

## 2. Schneller Tagescan — OSV + KEV, kein NVD

```bash
python3 checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    --no-nvd \
    --min-cvss 7.0 \
    --output /var/log/cve_scanner
```

**~5–15 Minuten** (abhängig von Cache-Wärme).
Filtert auf High/Critical, spart NVD-Rate-Limit komplett.
Empfohlen für nächtliche Cronjobs ohne NVD-Key.

---

## 3. Standardscan — alle Quellen, mit Cache

```bash
python3 checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf
```

**~15–30 Minuten** (warmer Cache) / **2–3 Stunden** (kalter Cache).
OSV + OSS Index + NVD (nur Mapping-Pakete) + CISA KEV.
Empfohlen als täglicher Standardlauf per Cronjob.

---

## 4. Standardscan mit Authentifizierung

```bash
NVD_API_KEY="dein-nvd-key" \
OSS_INDEX_USER="user@example.com" \
OSS_INDEX_TOKEN="dein-oss-token" \
python3 checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf
```

Wie Scan 3, aber mit API-Keys für höhere Rate-Limits:
- NVD: 0,7s statt 6s pro Request (8x schneller)
- OSS Index: deutlich mehr als 64 Requests/Stunde

---

## 5. Bestimmte Sites und Hosts

```bash
python3 checkmk_cve_scanner.py \
    --sites production dmz \
    --hosts webserver01 webserver02 dbserver01 \
    --output /var/log/cve_scanner
```

Scannt nur die angegebenen Sites und Hosts.
Nützlich für gezielte Nachscans nach Patch-Aktionen.

---

## 6. Alle Sites automatisch erkennen

```bash
python3 checkmk_cve_scanner.py \
    --all-sites \
    --config /etc/cve_scanner/scanner.conf
```

Erkennt alle Sites unter `/omd/sites` automatisch.
Entspricht `sites =` (leer) in der Konfigurationsdatei.

---

## 7. Nur Critical & High — schnelle Übersicht

```bash
python3 checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    --min-cvss 7.0 \
    --output /var/log/cve_scanner/high_only
```

Filtert auf CVSS ≥ 7.0 (High + Critical).
Reduziert Report-Größe drastisch, ideal für Executive-Reports.

---

## 8. Nur CISA KEV — aktiv ausgenutzte Schwachstellen

```bash
python3 checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    --no-nvd \
    --no-oss \
    --min-cvss 0.0 \
    --output /var/log/cve_scanner/kev_only
```

OSV + CISA KEV: findet alle Pakete mit aktiv ausgenutzten CVEs.
Sehr schnell, liefert die dringendsten Findings.

---

## 9. Frischer Scan — Cache umgehen

```bash
python3 checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    --no-cache
```

Ignoriert den Cache, fragt alle APIs neu ab.
Sinnvoll nach größeren Patch-Wellen oder wenn der Cache
manuell gelöscht wurde.

---

## 10. Cache-TTL anpassen

```bash
python3 checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    --cache-file /var/cache/cve_scanner.json \
    --cache-ttl 48
```

Cache mit 48h TTL in eigenem Verzeichnis.
Sinnvoll wenn der Scanner seltener als täglich läuft.

---

## 11. Eigene Package-Map

```bash
python3 checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    --package-map /etc/cve_scanner/package_map_custom.json
```

Lädt zusätzliche Paketnamen-Mappings aus einer JSON-Datei.
Ergänzt die eingebauten 160+ Mappings ohne Skript-Änderungen.

---

## 12. Vollständiger Scan — maximale Genauigkeit

```bash
NVD_API_KEY="dein-nvd-key" \
OSS_INDEX_USER="user@example.com" \
OSS_INDEX_TOKEN="dein-oss-token" \
python3 checkmk_cve_scanner.py \
    --sites production dmz monitoring \
    --omd-root /omd/sites \
    --no-cache \
    --package-map /etc/cve_scanner/package_map_custom.json \
    --min-cvss 0.0 \
    --output /var/log/cve_scanner/full \
    --verbose
```

**~2–3 Stunden** (alle APIs, kein Cache).
Alle Quellen, alle Pakete, alle Schweregrade, Debug-Ausgabe.
Empfohlen für den initialen Scan oder monatliche Vollprüfungen.

---

## Hilfsfunktionen

### Hosts auflisten (ohne Scan)

```bash
python3 checkmk_cve_scanner.py --sites mysite --list-hosts
```

```
[mysite] — 47 Hosts:
  dbserver01
  mailserver02
  webserver01
  ...
```

### Debug-Ausgabe aktivieren

```bash
python3 checkmk_cve_scanner.py \
    --config /etc/cve_scanner/scanner.conf \
    --verbose
```

Zeigt Cache-Hits, Ecosystem-Erkennung, API-Antworten im Detail.

---

## Alle Optionen

| Option | Standard | Beschreibung |
|---|---|---|
| `--config FILE` | — | INI-Konfigurationsdatei |
| `--sites SITE …` | alle | Checkmk Sites |
| `--all-sites` | — | Alle Sites automatisch erkennen |
| `--hosts HOST …` | alle | Nur diese Hosts scannen |
| `--omd-root DIR` | `/omd/sites` | OMD Root-Verzeichnis |
| `--list-hosts` | — | Hosts auflisten, nicht scannen |
| `--no-nvd` | — | NVD deaktivieren |
| `--no-osv` | — | OSV.dev deaktivieren |
| `--no-oss` | — | OSS Index deaktivieren |
| `--no-kev` | — | CISA KEV Anreicherung deaktivieren |
| `--nvd-key KEY` | `$NVD_API_KEY` | NVD API Key |
| `--oss-user USER` | `$OSS_INDEX_USER` | OSS Index Benutzername |
| `--oss-token TOKEN` | `$OSS_INDEX_TOKEN` | OSS Index API Token |
| `--min-cvss SCORE` | `0.0` | Minimaler CVSS Score (z.B. `7.0`) |
| `--package-map FILE` | — | Externe JSON/YAML Package-Map |
| `--no-cache` | — | API-Cache deaktivieren |
| `--cache-file FILE` | `/tmp/cve_scanner_cache.json` | Cache-Dateipfad |
| `--cache-ttl HOURS` | `24` | Cache-Gültigkeitsdauer in Stunden |
| `--output DIR` | `./reports` | Ausgabeverzeichnis |
| `--verbose` / `-v` | — | Debug-Ausgabe |

### Umgebungsvariablen

| Variable | Entspricht |
|---|---|
| `NVD_API_KEY` | `--nvd-key` |
| `OSS_INDEX_USER` | `--oss-user` |
| `OSS_INDEX_TOKEN` | `--oss-token` |

---

## Geschwindigkeit vs. Genauigkeit

```
Schnellster                                               Genauester
    │                                                         │
    ▼                                                         ▼
--no-nvd          Standard-        --no-cache       --no-cache
--no-oss          scan mit         + alle Keys      + alle Keys
(warmer Cache)    warmem Cache     (warmer Cache)   + --verbose
    │                  │                │                │
  2-5 min          15-30 min        30-60 min        2-3 Stunden
```
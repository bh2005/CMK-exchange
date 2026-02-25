#!/usr/bin/env python3
"""
checkmk_cve_scanner.py  v4.0  – Local Mode
===========================================
Läuft direkt auf dem Checkmk-Server als Site-User.
Liest Inventory-Daten aus dem Dateisystem statt über die REST API.
Unterstützt mehrere Sites auf einem Server.

Ablauf:
  1. Sites aus Konfiguration oder /omd/sites/* ermitteln
  2. Inventory-Dateien unter /omd/sites/<site>/var/check_mk/inventory/ einlesen
  3. Softwareliste gegen OSV.dev + OSS Index + CISA KEV + NVD* abgleichen
     (* NVD nur fuer Pakete mit bekanntem Mapping, spart 90% der Anfragen)
  4. JSON + CSV Report schreiben

Ausführung (als Site-User):
  su - <site>
  python3 /path/to/checkmk_cve_scanner.py --config /etc/cve_scanner/scanner.conf

Ausführung als root (alle Sites automatisch):
  python3 checkmk_cve_scanner.py --all-sites
"""

import argparse
import ast
import configparser
import csv
import gzip
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

OMD_ROOT        = Path("/omd/sites")
NVD_DELAY_NO_KEY  = 6.5
NVD_DELAY_WITH_KEY = 0.7
OSV_QUERYBATCH_URL  = "https://api.osv.dev/v1/querybatch"
OSV_VULNS_URL       = "https://api.osv.dev/v1/vulns"
OSV_BATCH_SIZE      = 100

OSS_INDEX_URL       = "https://ossindex.sonatype.org/api/v3/component-report"
OSS_INDEX_BATCH     = 128   # max. Pakete pro Request laut API-Doku

CISA_KEV_URL        = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
CISA_KEV_CACHE_TTL  = 3600  # Sekunden – Feed wird max. 1x pro Stunde neu geladen

# Pakettyp / OS-Name → OSV Ecosystem
OSV_ECOSYSTEM_MAP: dict[str, str] = {
    "deb": "Debian", "debian": "Debian",
    "ubuntu": "Ubuntu",
    "rpm": "Red Hat", "redhat": "Red Hat", "rhel": "Red Hat", "centos": "Red Hat",
    "rocky": "Rocky Linux", "almalinux": "AlmaLinux",
    "suse": "SUSE", "opensuse": "openSUSE",
    "fedora": "Fedora", "alpine": "Alpine",
    "arch": "Arch Linux", "gentoo": "Gentoo",
    "nixos": "NixOS", "wolfi": "Wolfi",
    "python": "PyPI", "pip": "PyPI",
    "nodejs": "npm", "npm": "npm",
    "gem": "RubyGems", "ruby": "RubyGems",
    "maven": "Maven", "java": "Maven",
    "cargo": "crates.io", "rust": "crates.io",
    "go": "Go", "nuget": "NuGet", "dotnet": "NuGet",
    "packagist": "Packagist", "php": "Packagist",
}

OSV_OS_ECOSYSTEM_MAP: dict[str, Optional[str]] = {
    "debian": "Debian", "ubuntu": "Ubuntu",
    "red hat": "Red Hat", "rhel": "Red Hat",
    "centos": "Red Hat", "rocky": "Rocky Linux",
    "almalinux": "AlmaLinux", "suse": "SUSE",
    "opensuse": "openSUSE", "fedora": "Fedora",
    "alpine": "Alpine", "arch linux": "Arch Linux",
    "gentoo": "Gentoo", "windows": None,
}

# ---------------------------------------------------------------------------
# Package-Name-Mapping
# ---------------------------------------------------------------------------
# Viele Pakete heißen unter Debian/Ubuntu anders als in der NVD/CVE-Datenbank.
# Dieses Mapping übersetzt Debian-Paketnamen → (NVD-Produktname, NVD-Vendor)
# damit CVE-Suchen zuverlässig treffen.
#
# Format:  "debian_paketname": ("nvd_product_name", "nvd_vendor")
#          nvd_vendor kann None sein → keyword-only Suche
# ---------------------------------------------------------------------------

PACKAGE_NAME_MAP: dict[str, tuple[str, Optional[str]]] = {
    # Web-Server / Proxies
    "apache2":                  ("http_server",           "apache"),
    "apache2-bin":              ("http_server",           "apache"),
    "apache2-utils":            ("http_server",           "apache"),
    "nginx":                    ("nginx",                 "nginx"),
    "nginx-full":               ("nginx",                 "nginx"),
    "nginx-light":              ("nginx",                 "nginx"),
    "lighttpd":                 ("lighttpd",              "lighttpd"),
    "haproxy":                  ("haproxy",               "haproxy"),
    "varnish":                  ("varnish",               "varnish"),
    "squid3":                   ("squid",                 "squid"),
    "squid":                    ("squid",                 "squid"),
    "traefik":                  ("traefik",               "traefik"),

    # TLS / Crypto
    "openssl":                  ("openssl",               "openssl"),
    "libssl3":                  ("openssl",               "openssl"),
    "libssl1.1":                ("openssl",               "openssl"),
    "libssl-dev":               ("openssl",               "openssl"),
    "gnutls-bin":               ("gnutls",                "gnu"),
    "libgnutls30":              ("gnutls",                "gnu"),
    "libgcrypt20":              ("libgcrypt",             "gnupg"),
    "nss":                      ("network_security_services", "mozilla"),
    "libnss3":                  ("network_security_services", "mozilla"),
    "libmbedtls14":             ("mbed_tls",              "arm"),
    "libmbedcrypto7":           ("mbed_tls",              "arm"),

    # SSH
    "openssh-server":           ("openssh",               "openbsd"),
    "openssh-client":           ("openssh",               "openbsd"),
    "openssh-sftp-server":      ("openssh",               "openbsd"),

    # PHP
    "php8.2":                   ("php",                   "php"),
    "php8.1":                   ("php",                   "php"),
    "php8.0":                   ("php",                   "php"),
    "php7.4":                   ("php",                   "php"),
    "php":                      ("php",                   "php"),
    "php-common":               ("php",                   "php"),
    "php8.2-cli":               ("php",                   "php"),
    "php8.2-fpm":               ("php",                   "php"),
    "php8.2-cgi":               ("php",                   "php"),
    "php8.2-common":            ("php",                   "php"),
    "php8.2-curl":              ("php",                   "php"),
    "php8.2-gd":                ("php",                   "php"),
    "php8.2-xml":               ("php",                   "php"),
    "php8.2-mbstring":          ("php",                   "php"),
    "php8.2-mysql":             ("php",                   "php"),
    "php8.2-sqlite3":           ("php",                   "php"),
    "php8.2-intl":              ("php",                   "php"),
    "php8.2-opcache":           ("php",                   "php"),
    "libapache2-mod-php8.2":    ("php",                   "php"),

    # Datenbanken
    "mariadb-server":           ("mariadb",               "mariadb"),
    "mariadb-client":           ("mariadb",               "mariadb"),
    "libmariadb3":              ("mariadb_connector_c",   "mariadb"),
    "mysql-server":             ("mysql",                 "oracle"),
    "mysql-client":             ("mysql",                 "oracle"),
    "postgresql":               ("postgresql",            "postgresql"),
    "postgresql-15":            ("postgresql",            "postgresql"),
    "postgresql-14":            ("postgresql",            "postgresql"),
    "postgresql-13":            ("postgresql",            "postgresql"),
    "postgresql-client-15":     ("postgresql",            "postgresql"),
    "redis-server":             ("redis",                 "redis"),
    "redis":                    ("redis",                 "redis"),
    "redis-tools":              ("redis",                 "redis"),
    "mongodb":                  ("mongodb",               "mongodb"),
    "mongodb-server":           ("mongodb",               "mongodb"),
    "sqlite3":                  ("sqlite",                "sqlite"),
    "libsqlite3-0":             ("sqlite",                "sqlite"),
    "memcached":                ("memcached",             "memcached"),
    "elasticsearch":            ("elasticsearch",         "elastic"),

    # Container / Virtualisierung
    "docker-ce":                ("docker",                "docker"),
    "docker-ce-cli":            ("docker",                "docker"),
    "containerd.io":            ("containerd",            "docker"),
    "docker-compose-plugin":    ("docker_compose",        "docker"),
    "docker-buildx-plugin":     ("buildx",               "docker"),

    # Java
    "openjdk-17-jdk":           ("openjdk",               "oracle"),
    "openjdk-17-jre":           ("openjdk",               "oracle"),
    "openjdk-17-jdk-headless":  ("openjdk",               "oracle"),
    "openjdk-17-jre-headless":  ("openjdk",               "oracle"),
    "openjdk-11-jdk":           ("openjdk",               "oracle"),
    "openjdk-11-jre":           ("openjdk",               "oracle"),
    "openjdk-21-jdk":           ("openjdk",               "oracle"),
    "openjdk-21-jre":           ("openjdk",               "oracle"),
    "default-jre":              ("openjdk",               "oracle"),
    "default-jdk":              ("openjdk",               "oracle"),

    # Python
    "python3":                  ("python",                "python_software_foundation"),
    "python3.11":               ("python",                "python_software_foundation"),
    "python3.10":               ("python",                "python_software_foundation"),
    "python3.9":                ("python",                "python_software_foundation"),
    "python2.7":                ("python",                "python_software_foundation"),
    "python3-pip":              ("pip",                   "pypa"),
    "python3-setuptools":       ("setuptools",            "pypa"),
    "python3-requests":         ("requests",              "psf"),
    "python3-cryptography":     ("cryptography",          "cryptography_project"),
    "python3-urllib3":          ("urllib3",               "urllib3"),
    "python3-jinja2":           ("jinja2",                "palletsprojects"),

    # Node.js
    "nodejs":                   ("node.js",               "nodejs"),
    "npm":                      ("npm",                   "npmjs"),

    # Ruby
    "ruby":                     ("ruby",                  "ruby-lang"),
    "ruby3.1":                  ("ruby",                  "ruby-lang"),
    "ruby2.7":                  ("ruby",                  "ruby-lang"),

    # Perl
    "perl":                     ("perl",                  "perl"),

    # Mail
    "exim4":                    ("exim",                  "exim"),
    "exim4-daemon-light":       ("exim",                  "exim"),
    "postfix":                  ("postfix",               "postfix"),
    "dovecot-core":             ("dovecot",               "dovecot"),

    # DNS / DHCP / NTP
    "bind9":                    ("bind",                  "isc"),
    "bind9-dnsutils":           ("bind",                  "isc"),
    "isc-dhcp-server":          ("dhcp",                  "isc"),
    "isc-dhcp-client":          ("dhcp",                  "isc"),
    "ntpsec":                   ("ntpsec",                "ntpsec"),
    "ntp":                      ("ntp",                   "ntp"),
    "chrony":                   ("chrony",                "tuxfamily"),

    # Monitoring / Logging
    "grafana":                  ("grafana",               "grafana"),
    "prometheus":               ("prometheus",            "prometheus"),
    "nagios4":                  ("nagios",                "nagios"),
    "zabbix-server-mysql":      ("zabbix",                "zabbix"),
    "rsyslog":                  ("rsyslog",               "rsyslog"),

    # Samba / LDAP
    "samba":                    ("samba",                 "samba"),
    "samba-common":             ("samba",                 "samba"),
    "samba-libs":               ("samba",                 "samba"),
    "smbclient":                ("samba",                 "samba"),
    "winbind":                  ("samba",                 "samba"),
    "slapd":                    ("openldap",              "openldap"),
    "ldap-utils":               ("openldap",              "openldap"),
    "libldap-2.5-0":            ("openldap",              "openldap"),

    # Systemtools
    "sudo":                     ("sudo",                  "sudo"),
    "bash":                     ("bash",                  "gnu"),
    "curl":                     ("curl",                  "haxx"),
    "wget":                     ("wget",                  "gnu"),
    "git":                      ("git",                   "git"),
    "vim":                      ("vim",                   "vim"),
    "vim-tiny":                 ("vim",                   "vim"),
    "tar":                      ("tar",                   "gnu"),
    "gzip":                     ("gzip",                  "gnu"),
    "xz-utils":                 ("xz",                   "tukaani"),
    "unzip":                    ("unzip",                 "info-zip"),
    "rsync":                    ("rsync",                 "samba"),
    "less":                     ("less",                  "gnu"),
    "nmap":                     ("nmap",                  "nmap"),
    "tcpdump":                  ("tcpdump",               "tcpdump"),
    "socat":                    ("socat",                 "dest-unreach"),
    "netcat-traditional":       ("netcat",                None),

    # Libraries mit bekannten CVEs
    "libexpat1":                ("expat",                 "libexpat"),
    "libexpat1-dev":            ("expat",                 "libexpat"),
    "libxml2":                  ("libxml2",               "xmlsoft"),
    "libxml2-dev":              ("libxml2",               "xmlsoft"),
    "libxslt1.1":               ("libxslt",               "xmlsoft"),
    "libpng16-16":              ("libpng",                "libpng"),
    "libjpeg62-turbo":          ("libjpeg-turbo",         "libjpeg-turbo"),
    "libtiff6":                 ("libtiff",               "libtiff"),
    "libwebp7":                 ("libwebp",               "google"),
    "libcurl4":                 ("curl",                  "haxx"),
    "libcurl3-gnutls":          ("curl",                  "haxx"),
    "libfreetype6":             ("freetype",              "freetype"),
    "libgd3":                   ("gd",                    "libgd"),
    "zlib1g":                   ("zlib",                  "zlib"),
    "liblzma5":                 ("xz",                   "tukaani"),
    "libarchive13":             ("libarchive",            "libarchive"),
    "libbz2-1.0":               ("bzip2",                 "bzip"),
    "libpcre3":                 ("pcre",                  "pcre"),
    "libpcre2-8-0":             ("pcre2",                 "pcre"),
    "libglib2.0-0":             ("glib",                  "gnome"),
    "libdbus-1-3":              ("dbus",                  "freedesktop"),
    "dbus":                     ("dbus",                  "freedesktop"),
    "libsystemd0":              ("systemd",               "freedesktop"),
    "systemd":                  ("systemd",               "freedesktop"),
    "snapd":                    ("snapd",                 "canonical"),
    "polkitd":                  ("polkit",                "polkit"),
    "pkexec":                   ("polkit",                "polkit"),

    # Checkmk selbst
    "check-mk-enterprise-2.4.0p21": ("checkmk",          "tribe29"),
    "check-mk-enterprise-2.4.0p18": ("checkmk",          "tribe29"),
    "check-mk-enterprise-2.4.0p9":  ("checkmk",          "tribe29"),
    "check-mk-enterprise-2.1.0p44": ("checkmk",          "tribe29"),
    "check-mk-agent":               ("checkmk",          "tribe29"),
}


def load_package_map(extra_file: Optional[str] = None) -> dict:
    """Lädt das Package-Name-Mapping.

    Reihenfolge:
      1. Eingebautes PACKAGE_NAME_MAP (immer verfügbar)
      2. Externe JSON/YAML-Datei (überschreibt/ergänzt eingebautes Mapping)

    Externe Datei erlaubt Updates ohne das Skript anzupassen.
    Format JSON:  { "paketname": ["nvd_product", "nvd_vendor"] }
    Format YAML:  paketname: [nvd_product, nvd_vendor]
    """
    mapping = dict(PACKAGE_NAME_MAP)  # Kopie des eingebauten Mappings

    if not extra_file:
        return mapping

    path = Path(extra_file)
    if not path.exists():
        log.warning(f"Package-Map-Datei nicht gefunden: {path}")
        return mapping

    try:
        with open(path, encoding="utf-8") as fh:
            if path.suffix.lower() in (".yaml", ".yml"):
                try:
                    import yaml  # type: ignore
                    data = yaml.safe_load(fh)
                except ImportError:
                    log.warning("PyYAML nicht installiert – YAML-Mapping ignoriert. "
                                "pip install pyyaml")
                    return mapping
            else:
                data = json.load(fh)

        added = 0
        for pkg, val in data.items():
            if isinstance(val, (list, tuple)) and len(val) == 2:
                mapping[pkg] = (val[0], val[1] if val[1] else None)
                added += 1
        log.info(f"Package-Map: {added} Einträge aus {path} geladen "
                 f"(gesamt: {len(mapping)})")
    except Exception as e:
        log.warning(f"Package-Map konnte nicht geladen werden: {e}")

    return mapping


# Aktives Mapping – wird beim Start einmal befüllt (ggf. mit externer Datei)
_ACTIVE_PACKAGE_MAP: dict = {}


def init_package_map(extra_file: Optional[str] = None):
    """Initialisiert das aktive Package-Mapping (einmalig beim Start aufrufen)."""
    global _ACTIVE_PACKAGE_MAP
    _ACTIVE_PACKAGE_MAP = load_package_map(extra_file)
    log.info(f"Package-Map: {len(_ACTIVE_PACKAGE_MAP)} Einträge geladen")


def map_package_name(debian_name: str) -> tuple[str, Optional[str]]:
    """Gibt (nvd_product, nvd_vendor) für einen Debian-Paketnamen zurück.
    Falls kein Mapping vorhanden: (debian_name, None)."""
    mapping = _ACTIVE_PACKAGE_MAP or PACKAGE_NAME_MAP
    # Direkt-Treffer
    if debian_name in mapping:
        return mapping[debian_name]
    # Prefix-Treffer für versionierte Pakete (z.B. php8.3-xxx → php)
    for prefix in ("libapache2-mod-php", "php8.", "php7.", "openjdk-",
                   "python3.", "ruby", "libssl", "libnss"):
        if debian_name.startswith(prefix):
            for key, val in mapping.items():
                if debian_name.startswith(key) or key.startswith(prefix):
                    return val
    return (debian_name, None)


# ---------------------------------------------------------------------------
# Datenmodelle
# ---------------------------------------------------------------------------

@dataclass
class SoftwareEntry:
    site:         str           # Checkmk Site-Name
    host:         str
    name:         str
    version:      str
    vendor:       str = ""
    package_type: str = ""
    os_name:      str = ""
    os_version:   str = ""   # Major-Version des OS (z.B. "12" für Debian 12)
    path:         str = ""


@dataclass
class CveMatch:
    cve_id:        str
    severity:      str
    cvss_score:    float
    cvss_vector:   str
    description:   str
    published:     str
    last_modified: str
    source:        str = "NVD"
    aliases:       list = field(default_factory=list)
    references:    list = field(default_factory=list)
    kev_exploited: bool = False   # True = aktiv in CISA KEV ausgenutzt


@dataclass
class VulnerabilityFinding:
    site:             str
    host:             str
    software_name:    str
    software_version: str
    vendor:           str
    cve:              CveMatch
    scan_timestamp:   str = ""

    def __post_init__(self):
        if not self.scan_timestamp:
            self.scan_timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["cve_id"]        = self.cve.cve_id
        d["severity"]      = self.cve.severity
        d["cvss_score"]    = self.cve.cvss_score
        d["cvss_vector"]   = self.cve.cvss_vector
        d["description"]   = self.cve.description
        d["published"]     = self.cve.published
        d["last_modified"] = self.cve.last_modified
        d["source"]        = self.cve.source
        d["aliases"]       = "; ".join(self.cve.aliases[:5])
        d["references"]    = "; ".join(self.cve.references[:5])
        del d["cve"]
        return d


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _cvss_score_to_severity(score: float) -> str:
    if score >= 9.0: return "CRITICAL"
    if score >= 7.0: return "HIGH"
    if score >= 4.0: return "MEDIUM"
    if score > 0.0:  return "LOW"
    return "NONE"


# ---------------------------------------------------------------------------
# Checkmk Inventory Reader (Dateisystem – kein HTTP)
# ---------------------------------------------------------------------------

class CheckmkInventoryReader:
    """
    Liest Inventory-Daten direkt vom Checkmk-Dateisystem.

    Pfadstruktur:
      /omd/sites/<site>/var/check_mk/inventory/<hostname>       ← Python-Format
      /omd/sites/<site>/var/check_mk/inventory/<hostname>.gz    ← komprimiert

    Das Format ist Python-Literal-Syntax (kein JSON), parsbar mit ast.literal_eval.
    Checkmk 2.x Struktur:
      {
        "Attributes": {},
        "Nodes": {
          "software": {
            "Nodes": {
              "packages": {
                "Table": { "rows": [...], "key_columns": [...] }
              },
              "os": {
                "Attributes": { "Pairs": { "name": ..., "version": ... } }
              }
            }
          }
        },
        "Table": {}
      }
    """

    def __init__(self, omd_root: Path = OMD_ROOT):
        self.omd_root = omd_root

    def discover_sites(self) -> list[str]:
        """Findet alle vorhandenen Checkmk Sites auf diesem Server."""
        if not self.omd_root.exists():
            log.error(f"OMD Root {self.omd_root} nicht gefunden!")
            return []
        sites = [d.name for d in self.omd_root.iterdir()
                 if d.is_dir() and (d / "var" / "check_mk" / "inventory").exists()]
        log.info(f"Gefundene Sites: {sites}")
        return sorted(sites)

    def get_inventory_dir(self, site: str) -> Path:
        return self.omd_root / site / "var" / "check_mk" / "inventory"

    def get_hosts(self, site: str) -> list[str]:
        """Gibt alle Hostnamen zurück, für die Inventory-Dateien existieren."""
        inv_dir = self.get_inventory_dir(site)
        if not inv_dir.exists():
            log.warning(f"Inventory-Verzeichnis nicht gefunden: {inv_dir}")
            return []
        hosts = set()
        for f in inv_dir.iterdir():
            if f.is_file() and not f.name.startswith("."):
                # .gz Dateien → Basename ohne .gz
                name = f.stem if f.suffix == ".gz" else f.name
                hosts.add(name)
        return sorted(hosts)

    def read_inventory(self, site: str, hostname: str) -> Optional[dict]:
        """
        Liest und parst die Inventory-Datei eines Hosts.
        Bevorzugt unkomprimierte Datei, fällt auf .gz zurück.
        """
        inv_dir = self.get_inventory_dir(site)
        plain_file = inv_dir / hostname
        gz_file    = inv_dir / f"{hostname}.gz"

        raw = None

        # 1. Unkomprimierte Datei bevorzugen
        if plain_file.exists():
            try:
                raw = plain_file.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                log.warning(f"Lesen fehlgeschlagen {plain_file}: {e}")

        # 2. Komprimierte Datei als Fallback
        if raw is None and gz_file.exists():
            try:
                with gzip.open(gz_file, "rt", encoding="utf-8",
                               errors="replace") as fh:
                    raw = fh.read()
            except OSError as e:
                log.warning(f"Lesen fehlgeschlagen {gz_file}: {e}")

        if raw is None:
            log.debug(f"Keine Inventory-Datei für {site}/{hostname}")
            return None

        # Python-Literal parsen (sicher, kein eval)
        try:
            return ast.literal_eval(raw)
        except (ValueError, SyntaxError) as e:
            log.warning(f"Parse-Fehler {site}/{hostname}: {e}")
            return None

    def iter_software(self, site: str,
                      hosts: Optional[list[str]] = None):
        """Generator: liefert SoftwareEntry-Objekte einzeln (RAM-effizient).
        Anstatt alle 500.000 Einträge in eine Liste zu laden, werden sie
        host-für-host verarbeitet und direkt weitergegeben.
        """
        target_hosts = hosts or self.get_hosts(site)
        log.info(f"[{site}] Lese Inventory für {len(target_hosts)} Hosts...")
        count = 0
        for hostname in target_hosts:
            inv = self.read_inventory(site, hostname)
            if inv is None:
                continue
            for entry in self._parse_inventory(site, hostname, inv):
                count += 1
                yield entry
        log.info(f"[{site}] → {count} Software-Einträge")

    def extract_software(self, site: str,
                         hosts: Optional[list[str]] = None) -> list[SoftwareEntry]:
        """Kompatibilitäts-Wrapper: gibt Liste zurück (für kleine Umgebungen).
        Für große Umgebungen (>500 Hosts) besser iter_software() nutzen.
        """
        return list(self.iter_software(site, hosts))

    # ── Inventory-Parsing ────────────────────────────────────────────────

    def _parse_inventory(self, site: str, hostname: str,
                         inv: dict) -> list[SoftwareEntry]:
        """
        Navigiert die Checkmk 2.x Inventory-Baumstruktur.
        Struktur: { Nodes: { software: { Nodes: { packages: {...}, os: {...} } } } }
        """
        entries: list[SoftwareEntry] = []

        # Checkmk 2.x Baumstruktur
        software_node = (
            inv.get("Nodes", {})
               .get("software", {})
               .get("Nodes", {})
        )

        # OS-Erkennung für Ecosystem-Mapping (mit Versionsnummer für OSV!)
        os_name    = self._extract_os_name(software_node)
        os_version = self._extract_os_version(software_node)

        # Pakete
        packages = self._extract_packages(site, hostname, software_node,
                                          os_name, os_version)
        entries.extend(packages)

        # OS selbst als Software-Eintrag
        os_entry = self._extract_os_entry(site, hostname, software_node, os_name)
        if os_entry:
            entries.append(os_entry)

        return entries

    def _extract_os_name(self, software_node: dict) -> str:
        """OS-Name aus dem Inventory-Baum für Ecosystem-Mapping."""
        os_node = software_node.get("os", {})
        pairs   = (
            os_node.get("Attributes", {}).get("Pairs", {})
            or os_node.get("Pairs", {})
        )
        return pairs.get("name", pairs.get("vendor", "")).lower()

    def _extract_os_version(self, software_node: dict) -> str:
        """Extrahiert die Major-Versionsnummer des OS (z.B. '12' aus 'Debian 12')."""
        import re
        os_node = software_node.get("os", {})
        pairs   = (
            os_node.get("Attributes", {}).get("Pairs", {})
            or os_node.get("Pairs", {})
        )
        raw = pairs.get("version", pairs.get("os_version", "")).strip()
        # Nur Major-Version: "12", "22.04" → "22", "2023" → "2023"
        m = re.match(r"([0-9]+)", raw)
        return m.group(1) if m else ""

    def _extract_packages(self, site: str, hostname: str,
                          software_node: dict,
                          os_name: str,
                          os_version: str = "") -> list[SoftwareEntry]:
        entries: list[SoftwareEntry] = []

        pkg_node = software_node.get("packages", {})

        # Checkmk 2.x: Pakete als "Table" mit "Rows" (Checkmk nutzt Großbuchstaben!)
        table  = pkg_node.get("Table", {})
        if isinstance(table, dict):
            # Checkmk 2.x schreibt "Rows" (Großbuchstabe)
            rows = table.get("Rows", table.get("rows", []))
        else:
            rows = table if isinstance(table, list) else []
        if not isinstance(rows, list):
            rows = []

        for pkg in rows:
            name    = pkg.get("name", "").strip()
            version = pkg.get("version", "").strip()
            if not name or not version:
                continue
            entries.append(SoftwareEntry(
                site=site, host=hostname,
                name=name, version=version,
                vendor=pkg.get("vendor", pkg.get("publisher", "")).strip(),
                package_type=pkg.get("package_type",
                                     pkg.get("install_type", "")).strip(),
                os_name=os_name,
                os_version=os_version,
                path="software.packages",
            ))
        return entries

    def _extract_os_entry(self, site: str, hostname: str,
                          software_node: dict,
                          os_name: str) -> Optional[SoftwareEntry]:
        os_node = software_node.get("os", {})
        pairs   = (
            os_node.get("Attributes", {}).get("Pairs", {})
            or os_node.get("Pairs", {})
        )
        if not pairs:
            return None

        name    = pairs.get("name", "").strip()
        version = (pairs.get("version", "")
                   or pairs.get("kernel_version", "")).strip()
        if not name:
            return None

        return SoftwareEntry(
            site=site, host=hostname,
            name=name, version=version,
            vendor=pairs.get("vendor", "").strip(),
            package_type="os",
            os_name=os_name,
            path="software.os",
        )


# ---------------------------------------------------------------------------
# API Result Cache  (Fix 3: verhindert wiederholte Abfragen gleicher Pakete)
# ---------------------------------------------------------------------------

class ApiCache:
    """Lokaler JSON-Cache für API-Ergebnisse.

    Verhindert, dass openssl 3.0.18 bei jedem Scan-Lauf tausende Male
    neu abgefragt wird. Default TTL: 24h (86400s).

    Struktur der Cache-Datei:
      { "<source>|<name>|<version>": {"ts": <unix_time>, "cves": [...]} }
    """

    def __init__(self, cache_file: str = "/tmp/cve_scanner_cache.json",
                 ttl_seconds: int = 86400):
        self.cache_file = Path(cache_file)
        self.ttl        = ttl_seconds
        self._data: dict = {}
        self._dirty      = False
        self._load()

    def _load(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as fh:
                    self._data = json.load(fh)
                # Abgelaufene Einträge beim Laden entfernen
                now = time.time()
                expired = [k for k, v in self._data.items()
                           if now - v.get("ts", 0) > self.ttl]
                for k in expired:
                    del self._data[k]
                if expired:
                    self._dirty = True
                log.debug(f"Cache geladen: {len(self._data)} Einträge "
                          f"({len(expired)} abgelaufen/entfernt)")
            except Exception as e:
                log.debug(f"Cache konnte nicht geladen werden: {e}")
                self._data = {}

    def save(self):
        if not self._dirty:
            return
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, separators=(",", ":"))
            log.debug(f"Cache gespeichert: {len(self._data)} Einträge → {self.cache_file}")
            self._dirty = False
        except Exception as e:
            log.warning(f"Cache konnte nicht gespeichert werden: {e}")

    def _key(self, source: str, name: str, version: str) -> str:
        return f"{source}|{name.lower()}|{version.lower()}"

    def get(self, source: str, name: str,
            version: str) -> Optional[list]:
        """Gibt gecachte CVE-Liste zurück oder None wenn kein/abgelaufener Eintrag."""
        k = self._key(source, name, version)
        entry = self._data.get(k)
        if entry is None:
            return None
        if time.time() - entry.get("ts", 0) > self.ttl:
            del self._data[k]
            self._dirty = True
            return None
        return entry.get("cves", [])

    def set(self, source: str, name: str, version: str,
            cves: list):
        """Speichert CVE-Liste für ein Paket im Cache."""
        k = self._key(source, name, version)
        self._data[k] = {"ts": time.time(), "cves": cves}
        self._dirty = True

    def stats(self) -> dict:
        now = time.time()
        fresh = sum(1 for v in self._data.values()
                    if now - v.get("ts", 0) <= self.ttl)
        return {"total": len(self._data), "fresh": fresh}


# ---------------------------------------------------------------------------
# NVD API Client
# ---------------------------------------------------------------------------

class NvdClient:
    BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def __init__(self, api_key: Optional[str] = None,
                 min_cvss_score: float = 0.0):
        self.min_cvss_score = min_cvss_score
        self._req_count     = 0
        self.delay          = NVD_DELAY_WITH_KEY if api_key else NVD_DELAY_NO_KEY
        self.session        = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if api_key:
            self.session.headers["apiKey"] = api_key

    def _throttle(self):
        if self._req_count > 0:
            time.sleep(self.delay)
        self._req_count += 1

    @staticmethod
    def _clean_version(version: str) -> str:
        """Bereinigt Debian-spezifische Versions-Suffixe fuer NVD.
        Beispiele:
          2:6.0.17          -> 6.0.17   (Epoch entfernen)
          2.4.66+dfsg       -> 2.4.66   (+dfsg... entfernen)
          9.2p1-2+deb12u7   -> 9.2p1    (Debian-Revision entfernen)
          3.0.18-1~deb12u2  -> 3.0.18   (Debian-Revision entfernen)
        """
        import re
        v = version.strip()
        # Epoch entfernen (z.B. "2:6.0.17" -> "6.0.17")
        if ":" in v:
            v = v.split(":", 1)[1]
        # Debian-Revision und Suffixe entfernen (+dfsg, ~deb, -N)
        v = re.split(r"[+~]|(?<=[0-9])-", v)[0]
        return v.strip()

    def search_by_keyword(self, name: str, version: str) -> list[CveMatch]:
        self._throttle()
        clean_ver = self._clean_version(version)
        try:
            resp = self.session.get(
                self.BASE_URL,
                params={"keywordSearch": f"{name} {clean_ver}",
                        "keywordExactMatch": "false",
                        "resultsPerPage": 100},
                timeout=30,
            )
            if resp.status_code == 404:
                return []   # 404 = keine Treffer, kein Fehler
            resp.raise_for_status()
            return self._parse(resp.json())
        except requests.RequestException as e:
            log.debug(f"NVD keyword '{name} {clean_ver}': {e}")
            return []

    def search_by_cpe(self, vendor: str, product: str,
                      version: str) -> list[CveMatch]:
        self._throttle()
        clean_ver = self._clean_version(version)
        v   = vendor.lower().replace(" ", "_").replace("-", "_") if vendor else "*"
        p   = product.lower().replace(" ", "_").replace("-", "_")
        cpe = f"cpe:2.3:*:{v}:{p}:{clean_ver or '*'}:*:*:*:*:*:*:*"
        try:
            resp = self.session.get(
                self.BASE_URL,
                params={"cpeName": cpe, "resultsPerPage": 100},
                timeout=30,
            )
            if resp.status_code == 404:
                return []   # 404 = keine Treffer, kein Fehler
            resp.raise_for_status()
            return self._parse(resp.json())
        except requests.RequestException as e:
            log.debug(f"NVD CPE '{cpe}': {e}")
            return []

    def _parse(self, data: dict) -> list[CveMatch]:
        results = []
        for item in data.get("vulnerabilities", []):
            cve_data = item.get("cve", {})
            cve_id   = cve_data.get("id", "")
            desc     = next((d["value"] for d in cve_data.get("descriptions", [])
                             if d.get("lang") == "en"), "")
            score, severity, vector = 0.0, "NONE", ""
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                mlist = cve_data.get("metrics", {}).get(key, [])
                if mlist:
                    m        = mlist[0].get("cvssData", {})
                    score    = float(m.get("baseScore", 0.0))
                    severity = m.get("baseSeverity", "NONE").upper()
                    vector   = m.get("vectorString", "")
                    break
            if score < self.min_cvss_score:
                continue
            results.append(CveMatch(
                cve_id=cve_id, severity=severity, cvss_score=score,
                cvss_vector=vector, description=desc[:500],
                published=cve_data.get("published", ""),
                last_modified=cve_data.get("lastModified", ""),
                source="NVD",
                references=[r.get("url", "")
                            for r in cve_data.get("references", [])[:10]],
            ))
        return results


# ---------------------------------------------------------------------------
# OSV.dev API Client
# ---------------------------------------------------------------------------

class OsvClient:
    def __init__(self, min_cvss_score: float = 0.0):
        self.min_cvss_score = min_cvss_score
        self.session        = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept":       "application/json",
            "User-Agent":   "checkmk-cve-scanner/3.0",
        })

    def detect_ecosystem(self, sw: SoftwareEntry) -> Optional[str]:
        """Bestimmt das OSV-Ecosystem für ein Paket.

        OSV erwartet für Debian/Ubuntu die Versionsnummer im Ecosystem:
          "Debian:12" statt "Debian"  → nur Treffer für Debian 12
          "Ubuntu:22.04" statt "Ubuntu"

        Ohne Versionsnummer liefert OSV zu viele unspezifische oder
        falsche Treffer (Pakete anderer Distro-Versionen).
        """
        # 1. OS-Name hat höchste Priorität (Ubuntu != Debian, auch wenn beide "deb")
        for os_key, eco in OSV_OS_ECOSYSTEM_MAP.items():
            if eco and os_key in sw.os_name:
                return self._versioned_eco(eco, sw.os_version)

        # 2. Ecosystem aus package_type (deb → Debian, rpm → Red Hat, ...)
        #    Nur als Fallback wenn OS-Name keinen Treffer ergab
        for key, eco in OSV_ECOSYSTEM_MAP.items():
            if key in sw.package_type.lower():
                return self._versioned_eco(eco, sw.os_version)

        # 3. Fallback: vendor
        for key, eco in OSV_ECOSYSTEM_MAP.items():
            if key in sw.vendor.lower():
                return eco

        return None

    @staticmethod
    def _versioned_eco(eco: str, os_version: str) -> str:
        """Hängt OS-Version an Ecosystem an: 'Debian' + '12' → 'Debian:12'."""
        distros_with_version = {"Debian", "Ubuntu", "Red Hat", "Rocky Linux",
                                 "AlmaLinux", "openSUSE", "SUSE", "Fedora",
                                 "Alpine", "Arch Linux"}
        if eco in distros_with_version and os_version:
            return f"{eco}:{os_version}"
        return eco

    def query_batch(self, sw_list: list[SoftwareEntry]
                    ) -> dict[str, list[CveMatch]]:
        results: dict[str, list[CveMatch]] = {}
        total = len(sw_list)

        for batch_start in range(0, total, OSV_BATCH_SIZE):
            batch = sw_list[batch_start:batch_start + OSV_BATCH_SIZE]
            log.info(
                f"  OSV Batch {batch_start // OSV_BATCH_SIZE + 1}/"
                f"{(total + OSV_BATCH_SIZE - 1) // OSV_BATCH_SIZE}: "
                f"{len(batch)} Pakete"
            )

            queries, batch_keys = [], []
            for sw in batch:
                eco = self.detect_ecosystem(sw)
                key = f"{sw.name.lower()}|{sw.version.lower()}"
                pkg = {"name": sw.name}
                if eco:
                    pkg["ecosystem"] = eco
                queries.append({"version": sw.version, "package": pkg})
                batch_keys.append(key)

            try:
                resp = self.session.post(
                    OSV_QUERYBATCH_URL,
                    json={"queries": queries},
                    timeout=60,
                )
                resp.raise_for_status()
                batch_results = resp.json().get("results", [])
            except requests.RequestException as e:
                log.warning(f"OSV Batch Fehler: {e}")
                continue

            ids_to_fetch: list[str]          = []
            key_to_ids:   dict[str, list[str]] = {}
            for idx, result in enumerate(batch_results):
                key      = batch_keys[idx]
                vuln_ids = [v["id"] for v in result.get("vulns", [])]
                if vuln_ids:
                    key_to_ids[key] = vuln_ids
                    ids_to_fetch.extend(vuln_ids)

            vuln_details = self._fetch_details(list(set(ids_to_fetch)))

            for key, ids in key_to_ids.items():
                cve_list = []
                for vid in ids:
                    if vid in vuln_details:
                        m = self._parse_osv_vuln(vuln_details[vid])
                        if m and m.cvss_score >= self.min_cvss_score:
                            cve_list.append(m)
                if cve_list:
                    results[key] = cve_list

        return results

    def _fetch_details(self, vuln_ids: list[str]) -> dict[str, dict]:
        details: dict[str, dict] = {}
        for vid in vuln_ids:
            try:
                resp = self.session.get(f"{OSV_VULNS_URL}/{vid}", timeout=15)
                if resp.status_code == 200:
                    details[vid] = resp.json()
            except requests.RequestException as e:
                log.debug(f"OSV Detail '{vid}': {e}")
        return details

    def _parse_osv_vuln(self, osv_vuln: dict) -> Optional[CveMatch]:
        osv_id  = osv_vuln.get("id", "")
        aliases = osv_vuln.get("aliases", [])
        primary_id = next((a for a in aliases if a.startswith("CVE-")), osv_id)

        desc = (osv_vuln.get("summary", "") or
                osv_vuln.get("details", ""))[:500]

        score, severity, vector = 0.0, "NONE", ""
        for sev in osv_vuln.get("severity", []):
            t, s = sev.get("type", ""), sev.get("score", "")
            if t in ("CVSS_V3", "CVSS_V4"):
                parsed = self._parse_cvss(s)
                if parsed:
                    score, severity, vector = parsed
                    break
            elif t == "CVSS_V2" and score == 0.0:
                parsed = self._parse_cvss(s)
                if parsed:
                    score, severity, vector = parsed

        if score == 0.0:
            db = osv_vuln.get("database_specific", {})
            raw = db.get("cvss", db.get("score", 0))
            try:
                score    = float(raw)
                severity = _cvss_score_to_severity(score)
            except (ValueError, TypeError):
                pass

        refs = [r.get("url", "") for r in osv_vuln.get("references", [])
                if r.get("url")][:10]

        return CveMatch(
            cve_id=primary_id, severity=severity, cvss_score=score,
            cvss_vector=vector, description=desc,
            published=osv_vuln.get("published", ""),
            last_modified=osv_vuln.get("modified", ""),
            source="OSV",
            aliases=[a for a in ([osv_id] + aliases) if a != primary_id][:5],
            references=refs,
        )

    @staticmethod
    def _parse_cvss(s: str) -> Optional[tuple]:
        if not s:
            return None
        try:
            score = float(s)
            return score, _cvss_score_to_severity(score), ""
        except ValueError:
            pass
        if "CVSS:" in s.upper():
            return 0.0, "NONE", s
        return None


# ---------------------------------------------------------------------------
# OSS Index Client (Sonatype) – Batch bis 128 Pakete, kostenlos
# ---------------------------------------------------------------------------

class OssIndexClient:
    """Sonatype OSS Index: https://ossindex.sonatype.org
    Kostenlos ohne Account (rate-limited ~64/h).
    Mit kostenlosem Account (username + API-Token) deutlich mehr.
    Nutzt Package-URL (PURL) Format: pkg:deb/debian/openssl@3.0.18
    """

    def __init__(self, username: str = "", token: str = "",
                 min_cvss_score: float = 0.0):
        self.min_cvss_score = min_cvss_score
        self.session        = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept":       "application/json",
            "User-Agent":   "checkmk-cve-scanner/4.0",
        })
        if username and token:
            self.session.auth = (username, token)

    @staticmethod
    def _make_purl(sw: SoftwareEntry) -> str:
        """Erstellt Package-URL (PURL) aus SoftwareEntry.
        Format: pkg:deb/debian/<name>@<version>
        """
        pkg_type = "deb"
        namespace = "debian"
        pt = sw.package_type.lower() if sw.package_type else ""
        os = sw.os_name.lower() if sw.os_name else ""
        if "rpm" in pt or "rhel" in os or "centos" in os or "red hat" in os:
            pkg_type  = "rpm"
            namespace = "redhat"
        elif "ubuntu" in os:
            pkg_type  = "deb"
            namespace = "ubuntu"
        elif "alpine" in os:
            pkg_type  = "apk"
            namespace = "alpine"
        # Version bereinigen (kein Epoch, kein Debian-Suffix)
        ver = NvdClient._clean_version(sw.version)
        name = sw.name.lower()
        return f"pkg:{pkg_type}/{namespace}/{name}@{ver}"

    def query_batch(self, sw_list: list["SoftwareEntry"]
                    ) -> dict[str, list[CveMatch]]:
        results: dict[str, list[CveMatch]] = {}
        total = len(sw_list)

        for batch_start in range(0, total, OSS_INDEX_BATCH):
            batch = sw_list[batch_start:batch_start + OSS_INDEX_BATCH]
            batch_num = batch_start // OSS_INDEX_BATCH + 1
            total_batches = (total + OSS_INDEX_BATCH - 1) // OSS_INDEX_BATCH
            log.info(f"  OSS Index Batch {batch_num}/{total_batches}: {len(batch)} Pakete")

            coordinates = []
            purl_to_key: dict[str, str] = {}
            for sw in batch:
                purl = self._make_purl(sw)
                key  = f"{sw.name.lower()}|{sw.version.lower()}"
                coordinates.append({"coordinates": purl})
                purl_to_key[purl] = key

            try:
                resp = self.session.post(
                    OSS_INDEX_URL,
                    json={"coordinates": [c["coordinates"] for c in coordinates]},
                    timeout=60,
                )
                if resp.status_code == 429:
                    log.warning("OSS Index Rate Limit erreicht – warte 60s...")
                    time.sleep(60)
                    resp = self.session.post(
                        OSS_INDEX_URL,
                        json={"coordinates": [c["coordinates"] for c in coordinates]},
                        timeout=60,
                    )
                resp.raise_for_status()
            except requests.RequestException as e:
                log.warning(f"OSS Index Batch Fehler: {e}")
                continue

            for component in resp.json():
                purl  = component.get("coordinates", "")
                vulns = component.get("vulnerabilities", [])
                if not vulns:
                    continue
                # PURL kann Abweichungen haben – normalisieren
                key = purl_to_key.get(purl)
                if not key:
                    # Fallback: Name aus PURL extrahieren
                    try:
                        bare = purl.split("/")[-1].split("@")[0].lower()
                        ver  = purl.split("@")[1].lower() if "@" in purl else ""
                        key  = f"{bare}|{ver}"
                    except Exception:
                        continue

                cve_list = []
                for v in vulns:
                    cve_id  = v.get("cve", v.get("id", ""))
                    score   = float(v.get("cvssScore", 0.0))
                    if score < self.min_cvss_score:
                        continue
                    severity = _cvss_score_to_severity(score)
                    title    = v.get("title", "")
                    desc     = v.get("description", title)[:500]
                    refs     = [v.get("reference", "")]
                    if not cve_id:
                        continue
                    cve_list.append(CveMatch(
                        cve_id=cve_id, severity=severity, cvss_score=score,
                        cvss_vector=v.get("cvssVector", ""),
                        description=desc,
                        published=v.get("publishedDate", ""),
                        last_modified=v.get("lastModifiedDate", ""),
                        source="OSS",
                        references=[r for r in refs if r],
                    ))
                if cve_list:
                    existing = results.get(key, [])
                    existing.extend(cve_list)
                    results[key] = existing

        return results


# ---------------------------------------------------------------------------
# CISA KEV Client – Known Exploited Vulnerabilities (aktiv ausgenutzt!)
# ---------------------------------------------------------------------------

class CisaKevClient:
    """CISA Known Exploited Vulnerabilities Catalog.
    Kein Rate-Limit, kein API-Key. JSON-Feed wird lokal gecacht.
    Liefert KEINEN CVSS-Score, aber markiert CVEs als aktiv ausgenutzt –
    das ist wertvoller als ein hoher CVSS-Score alleine.
    """

    def __init__(self, cache_dir: str = "/tmp"):
        self.cache_file  = Path(cache_dir) / "cisa_kev_cache.json"
        self._kev_ids: set[str] = set()
        self._kev_data: dict[str, dict] = {}
        self._loaded     = False
        self.session     = requests.Session()
        self.session.headers.update({"User-Agent": "checkmk-cve-scanner/4.0"})

    def _load(self):
        """Laedt den KEV-Feed (aus Cache wenn fresh genug, sonst von CISA)."""
        if self._loaded:
            return
        # Cache prüfen
        if self.cache_file.exists():
            age = time.time() - self.cache_file.stat().st_mtime
            if age < CISA_KEV_CACHE_TTL:
                try:
                    with open(self.cache_file, encoding="utf-8") as fh:
                        data = json.load(fh)
                    self._ingest(data)
                    log.info(f"CISA KEV: {len(self._kev_ids)} Einträge aus Cache")
                    self._loaded = True
                    return
                except Exception:
                    pass
        # Neu laden
        try:
            log.info("CISA KEV: Lade Feed von CISA...")
            resp = self.session.get(CISA_KEV_URL, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            with open(self.cache_file, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            self._ingest(data)
            log.info(f"CISA KEV: {len(self._kev_ids)} aktiv ausgenutzte CVEs geladen")
        except requests.RequestException as e:
            log.warning(f"CISA KEV Feed nicht erreichbar: {e}")
        self._loaded = True

    def _ingest(self, data: dict):
        for v in data.get("vulnerabilities", []):
            cve_id = v.get("cveID", "")
            if cve_id:
                self._kev_ids.add(cve_id)
                self._kev_data[cve_id] = {
                    "vendorProject":     v.get("vendorProject", ""),
                    "product":           v.get("product", ""),
                    "vulnerabilityName": v.get("vulnerabilityName", ""),
                    "dateAdded":         v.get("dateAdded", ""),
                    "shortDescription":  v.get("shortDescription", ""),
                    "requiredAction":    v.get("requiredAction", ""),
                    "dueDate":           v.get("dueDate", ""),
                    "knownRansomware":   v.get("knownRansomwareCampaignUse", "Unknown"),
                }

    def is_exploited(self, cve_id: str) -> bool:
        self._load()
        return cve_id in self._kev_ids

    def enrich_findings(self, findings: list) -> int:
        """Markiert Findings die in CISA KEV sind als aktiv ausgenutzt.
        Gibt Anzahl der markierten Findings zurück."""
        self._load()
        count = 0
        for f in findings:
            cve_id = f.cve.cve_id
            if cve_id in self._kev_ids:
                f.cve.kev_exploited = True
                kev = self._kev_data[cve_id]
                # Severity auf mindestens HIGH setzen wenn exploited
                if f.cve.severity in ("NONE", "LOW", "MEDIUM"):
                    f.cve.severity = "HIGH"
                    if f.cve.cvss_score == 0.0:
                        f.cve.cvss_score = 7.0
                # Beschreibung anreichern
                if kev["shortDescription"] and not f.cve.description:
                    f.cve.description = kev["shortDescription"]
                count += 1
        return count


# ---------------------------------------------------------------------------
# CVE Merger
# ---------------------------------------------------------------------------

class CveMerger:
    @staticmethod
    def merge(nvd: list[CveMatch], osv: list[CveMatch],
              oss: list[CveMatch] | None = None) -> list[CveMatch]:
        merged: dict[str, CveMatch] = {c.cve_id: c for c in nvd}
        for cve in (osv + (oss or [])):
            key = next((k for k in [cve.cve_id] + cve.aliases if k in merged), None)
            if key:
                merged[key] = CveMerger._combine(merged[key], cve)
            else:
                merged[cve.cve_id] = cve
        return list(merged.values())

    @staticmethod
    def _combine(a: CveMatch, b: CveMatch) -> CveMatch:
        hi = a if a.cvss_score >= b.cvss_score else b
        lo = b if a.cvss_score >= b.cvss_score else a
        return CveMatch(
            cve_id=a.cve_id,
            severity=hi.severity, cvss_score=hi.cvss_score,
            cvss_vector=hi.cvss_vector,
            description=a.description or b.description,
            published=a.published or b.published,
            last_modified=max(a.last_modified, b.last_modified),
            source="NVD+OSV",
            aliases=list(set(a.aliases + b.aliases +
                             ([b.cve_id] if b.cve_id != a.cve_id else [])))[:5],
            references=list(dict.fromkeys(a.references + b.references))[:10],
        )


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------

class ReportGenerator:
    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp  = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    def write_json(self, findings: list[VulnerabilityFinding],
                   summary: dict) -> Path:
        path = self.output_dir / f"cve_report_{self.timestamp}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({
                "meta": {
                    "generated_at":   datetime.utcnow().isoformat() + "Z",
                    "scanner":        "checkmk_cve_scanner",
                    "version":        "3.0.0",
                    "sources":        ["NVD", "OSV.dev"],
                    "total_findings": len(findings),
                },
                "summary":  summary,
                "findings": [f.to_dict() for f in findings],
            }, fh, indent=2, ensure_ascii=False)
        log.info(f"JSON Report: {path}")
        return path

    def write_csv(self, findings: list[VulnerabilityFinding]) -> Path:
        fieldnames = [
            "site", "host", "software_name", "software_version", "vendor",
            "cve_id", "severity", "cvss_score", "cvss_vector",
            "source", "aliases", "published", "last_modified",
            "description", "references", "scan_timestamp",
        ]
        path = self.output_dir / f"cve_report_{self.timestamp}.csv"
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            for f in findings:
                w.writerow(f.to_dict())
        log.info(f"CSV Report: {path}")
        return path

    def write_summary_csv(self, summary_by_host: dict) -> Path:
        path = self.output_dir / f"cve_summary_{self.timestamp}.csv"
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(
                fh,
                fieldnames=["site", "host", "total", "critical",
                            "high", "medium", "low", "top_cve", "sources"],
            )
            w.writeheader()
            for (site, host), data in sorted(summary_by_host.items()):
                w.writerow({
                    "site":     site,
                    "host":     host,
                    "total":    data["total"],
                    "critical": data.get("CRITICAL", 0),
                    "high":     data.get("HIGH", 0),
                    "medium":   data.get("MEDIUM", 0),
                    "low":      data.get("LOW", 0),
                    "top_cve":  data.get("top_cve", ""),
                    "sources":  data.get("sources", ""),
                })
        log.info(f"Summary CSV: {path}")
        return path


# ---------------------------------------------------------------------------
# Scanner Orchestration
# ---------------------------------------------------------------------------

class CveScanner:
    def __init__(self,
                 reader:      CheckmkInventoryReader,
                 nvd_client:  Optional[NvdClient],
                 osv_client:  Optional[OsvClient],
                 oss_client:  Optional[OssIndexClient] = None,
                 kev_client:  Optional[CisaKevClient]  = None,
                 cache:       Optional[ApiCache]        = None):
        self.reader = reader
        self.nvd    = nvd_client
        self.osv    = osv_client
        self.oss    = oss_client
        self.kev    = kev_client
        self.cache  = cache

    def scan(self, sites: list[str],
             host_filter: Optional[list[str]] = None
             ) -> list[VulnerabilityFinding]:

        # ── Inventory einlesen (Generator – RAM-effizient) ──────────────
        # Anstatt alle SoftwareEntry-Objekte in eine Liste zu laden,
        # werden sie per Generator einzeln verarbeitet. Bei 1.000 Hosts
        # mit je 500 Paketen = 500.000 Objekte → nur unique_sw bleibt im RAM.
        unique_sw:    dict[tuple, SoftwareEntry] = {}
        # host_map: (name, version) → Liste von (site, host) Tupeln
        # wird für das spätere Findings-Mapping gebraucht
        host_map:     dict[tuple, list[tuple]] = {}
        total_entries = 0

        for site in sites:
            for sw in self.reader.iter_software(site, hosts=host_filter):
                total_entries += 1
                if sw.package_type == "os":
                    continue  # OS-Info nur für Ecosystem-Mapping
                key = (sw.name.lower(), sw.version.lower())
                if key not in unique_sw:
                    unique_sw[key] = sw
                host_map.setdefault(key, []).append((sw.site, sw.host,
                                                      sw.name, sw.version,
                                                      sw.vendor))

        log.info(f"Gesamt Software-Einträge: {total_entries}")
        sw_list = list(unique_sw.values())
        log.info(f"Unique Software/Version: {len(unique_sw)}")

        # ── Cache-Status anzeigen ────────────────────────────────────────
        if self.cache:
            cs = self.cache.stats()
            log.info(f"Cache: {cs['fresh']} frische Einträge in {self.cache.cache_file}")

        # ── OSV.dev Batch-Lookup ─────────────────────────────────────────
        osv_results: dict[str, list[CveMatch]] = {}
        if self.osv:
            log.info("─" * 55)
            log.info("OSV.dev Batch-Lookup...")
            # Cache-Hits herausfiltern
            osv_uncached = [sw for sw in sw_list
                            if self.cache is None
                            or self.cache.get("osv", sw.name, sw.version) is None]
            cached_hits  = len(sw_list) - len(osv_uncached)
            if cached_hits:
                log.info(f"  OSV Cache-Hits: {cached_hits} Pakete übersprungen")
                for sw in sw_list:
                    if self.cache:
                        cached = self.cache.get("osv", sw.name, sw.version)
                        if cached is not None:
                            key = f"{sw.name.lower()}|{sw.version.lower()}"
                            osv_results[key] = [CveMatch(**c) for c in cached]
            # API-Abfragen für nicht gecachte Pakete
            if osv_uncached:
                fresh = self.osv.query_batch(osv_uncached)
                osv_results.update(fresh)
                if self.cache:
                    for key, cves in fresh.items():
                        n, v = key.split("|", 1)
                        self.cache.set("osv", n, v, [vars(c) for c in cves])
            log.info(f"OSV: {sum(len(v) for v in osv_results.values())} "
                     f"Vulnerabilities in {len(osv_results)} Paketen")

        # ── OSS Index Batch-Lookup ───────────────────────────────────────
        oss_results: dict[str, list[CveMatch]] = {}
        if self.oss:
            log.info("─" * 55)
            log.info("OSS Index Batch-Lookup...")
            oss_uncached = [sw for sw in sw_list
                            if self.cache is None
                            or self.cache.get("oss", sw.name, sw.version) is None]
            cached_hits = len(sw_list) - len(oss_uncached)
            if cached_hits:
                log.info(f"  OSS Cache-Hits: {cached_hits} Pakete übersprungen")
                for sw in sw_list:
                    if self.cache:
                        cached = self.cache.get("oss", sw.name, sw.version)
                        if cached is not None:
                            key = f"{sw.name.lower()}|{sw.version.lower()}"
                            oss_results[key] = [CveMatch(**c) for c in cached]
            if oss_uncached:
                fresh = self.oss.query_batch(oss_uncached)
                oss_results.update(fresh)
                if self.cache:
                    for key, cves in fresh.items():
                        n, v = key.split("|", 1)
                        self.cache.set("oss", n, v, [vars(c) for c in cves])
            log.info(f"OSS: {sum(len(v) for v in oss_results.values())} "
                     f"Vulnerabilities in {len(oss_results)} Paketen")

        # ── NVD Lookup – NUR Pakete mit bekanntem Mapping ────────────────
        nvd_results: dict[tuple, list[CveMatch]] = {}
        if self.nvd:
            log.info("─" * 55)
            mapped_sw = [(name, version, sw)
                         for (name, version), sw in unique_sw.items()
                         if name in PACKAGE_NAME_MAP]
            log.info(f"NVD Lookup (nur Mapping-Pakete): {len(mapped_sw)} / {len(unique_sw)} Pakete")
            nvd_skipped = 0
            for idx, (name, version, sw_proto) in enumerate(mapped_sw, 1):
                # Cache prüfen
                if self.cache:
                    cached = self.cache.get("nvd", name, version)
                    if cached is not None:
                        if cached:
                            nvd_results[(name, version)] = [CveMatch(**c) for c in cached]
                        nvd_skipped += 1
                        continue
                log.info(f"[{idx}/{len(mapped_sw)}] NVD: {name} {version}")
                nvd_product, nvd_vendor = map_package_name(name)
                cves = []
                if nvd_vendor:
                    cves = self.nvd.search_by_cpe(nvd_vendor, nvd_product, version)
                if not cves:
                    cves = self.nvd.search_by_keyword(nvd_product, version)
                if self.cache:
                    self.cache.set("nvd", name, version, [vars(c) for c in cves])
                if cves:
                    nvd_results[(name, version)] = cves
                    log.info(f"  → {len(cves)} CVE(s)")
            if nvd_skipped:
                log.info(f"NVD Cache-Hits: {nvd_skipped} Pakete übersprungen")

        # ── Findings zusammenführen ──────────────────────────────────────
        log.info("─" * 55)
        log.info("Merge OSV + OSS + NVD...")
        findings: list[VulnerabilityFinding] = []

        for (name, version), _ in unique_sw.items():
            key      = f"{name}|{version}"
            nvd_cves = nvd_results.get((name, version), [])
            osv_cves = osv_results.get(key, [])
            oss_cves = oss_results.get(key, [])
            if not nvd_cves and not osv_cves and not oss_cves:
                continue

            merged_cves = CveMerger.merge(nvd_cves, osv_cves, oss_cves)
            for (h_site, h_host, h_name, h_version, h_vendor) in                     host_map.get((name, version), []):
                for cve in merged_cves:
                    findings.append(VulnerabilityFinding(
                        site=h_site, host=h_host,
                        software_name=h_name, software_version=h_version,
                        vendor=h_vendor, cve=cve,
                    ))

        # ── CISA KEV Anreicherung ────────────────────────────────────────
        if self.kev:
            log.info("─" * 55)
            n = self.kev.enrich_findings(findings)
            log.info(f"CISA KEV: {n} Findings als aktiv ausgenutzt markiert")

        # ── Cache persistieren ───────────────────────────────────────────
        if self.cache:
            self.cache.save()

        findings.sort(key=lambda f: (f.cve.kev_exploited, f.cve.cvss_score),
                      reverse=True)
        return findings

    @staticmethod
    def build_summary(findings: list[VulnerabilityFinding]
                      ) -> tuple[dict, dict]:
        by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
        by_source   = {"NVD": 0, "OSV": 0, "OSS": 0, "NVD+OSV": 0, "OTHER": 0}
        kev_count   = 0
        by_host:    dict[tuple, dict] = {}

        for f in findings:
            by_severity[f.cve.severity] = \
                by_severity.get(f.cve.severity, 0) + 1
            by_source[f.cve.source] = by_source.get(f.cve.source, 0) + 1
            if f.cve.kev_exploited:
                kev_count += 1

            key = (f.site, f.host)
            if key not in by_host:
                by_host[key] = {"total": 0, "top_cve": "",
                                "top_score": 0.0, "sources": set()}
            by_host[key]["total"] += 1
            by_host[key][f.cve.severity] = by_host[key].get(f.cve.severity, 0) + 1
            by_host[key]["sources"].add(f.cve.source)
            if f.cve.cvss_score > by_host[key]["top_score"]:
                by_host[key]["top_score"] = f.cve.cvss_score
                by_host[key]["top_cve"]   = f.cve.cve_id

        for hd in by_host.values():
            hd["sources"] = ", ".join(sorted(hd["sources"]))

        sw_count: dict[str, int] = {}
        for f in findings:
            k = f"{f.software_name} {f.software_version}"
            sw_count[k] = sw_count.get(k, 0) + 1

        return {
            "total_findings":  len(findings),
            "by_severity":     by_severity,
            "by_source":       by_source,
            "affected_hosts":  len(by_host),
            "kev_exploited_count":      kev_count,
            "top_vulnerable_software": [
                {"software": s, "finding_count": c}
                for s, c in sorted(sw_count.items(),
                                   key=lambda x: x[1], reverse=True)[:10]
            ],
        }, by_host


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

def load_config(config_path: Optional[str]) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read_dict({
        "checkmk": {
            "omd_root":    "/omd/sites",
            "sites":       "",          # leer = alle Sites auto-erkennen
            "hosts":       "",          # leer = alle Hosts
        },
        "nvd": {
            "enabled":        "true",
            "api_key":        "",
            "min_cvss_score": "0.0",
        },
        "osv": {
            "enabled": "true",
        },
        "oss_index": {
            "enabled":  "true",
            "username": "",   # Sonatype OSS Index Account (optional, erhöht Rate-Limit)
            "token":    "",
        },
        "cisa_kev": {
            "enabled":   "true",
            "cache_dir": "/tmp",
        },
        "cache": {
            "enabled":  "true",
            "file":     "/tmp/cve_scanner_cache.json",
            "ttl_hours": "24",
        },
        "package_map": {
            "file": "",   # Pfad zu externer JSON/YAML Datei (leer = nur eingebaut)
        },
        "output": {
            "directory": "/var/log/cve_scanner",
        },
    })
    if config_path:
        read = cfg.read(config_path)
        if not read:
            log.error(f"Konfigurationsdatei nicht gefunden: {config_path}")
            sys.exit(1)
        log.info(f"Konfiguration geladen: {config_path}")
    return cfg


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Checkmk 2.4 CVE Scanner v3.0 — Local Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Alle Sites scannen (als root oder mit Zugriff auf /omd/sites)
  python3 checkmk_cve_scanner.py --config /etc/cve_scanner/scanner.conf

  # Als Site-User (nur die eigene Site)
  su - mysite
  python3 checkmk_cve_scanner.py --sites mysite --output ~/var/cve_reports

  # Bestimmte Sites + Hosts + nur High/Critical
  python3 checkmk_cve_scanner.py \\
      --sites site1 site2 \\
      --hosts server01 server02 \\
      --min-cvss 7.0 \\
      --output /var/reports/cve

  # Nur OSV (kein NVD-Key nötig, ~30 Sekunden)
  python3 checkmk_cve_scanner.py --sites mysite --no-nvd

  # Debug: Inventory einer einzelnen Site anzeigen
  python3 checkmk_cve_scanner.py --sites mysite --list-hosts
        """,
    )

    p.add_argument("--config", metavar="FILE",
                   help="Konfigurationsdatei (INI-Format)")

    site_grp = p.add_argument_group("Sites & Hosts")
    site_grp.add_argument("--sites", nargs="+", metavar="SITE",
                          help="Checkmk Sites (Standard: alle unter /omd/sites)")
    site_grp.add_argument("--all-sites", action="store_true",
                          help="Alle verfügbaren Sites automatisch erkennen")
    site_grp.add_argument("--hosts", nargs="+", metavar="HOSTNAME",
                          help="Nur diese Hosts scannen (Standard: alle)")
    site_grp.add_argument("--omd-root", default="/omd/sites",
                          help="OMD Root-Verzeichnis (Standard: /omd/sites)")
    site_grp.add_argument("--list-hosts", action="store_true",
                          help="Nur Hosts auflisten, nicht scannen")

    src_grp = p.add_argument_group("Quellen")
    src_grp.add_argument("--no-nvd", action="store_true",
                         help="NVD deaktivieren (Standard: nur Mapping-Pakete)")
    src_grp.add_argument("--no-osv", action="store_true",
                         help="OSV.dev deaktivieren")
    src_grp.add_argument("--no-oss", action="store_true",
                         help="OSS Index deaktivieren")
    src_grp.add_argument("--no-kev", action="store_true",
                         help="CISA KEV Anreicherung deaktivieren")
    src_grp.add_argument("--nvd-key",
                         default=os.environ.get("NVD_API_KEY"),
                         help="NVD API Key [env: NVD_API_KEY]")
    src_grp.add_argument("--oss-user",
                         default=os.environ.get("OSS_INDEX_USER"),
                         help="OSS Index Benutzername [env: OSS_INDEX_USER]")
    src_grp.add_argument("--oss-token",
                         default=os.environ.get("OSS_INDEX_TOKEN"),
                         help="OSS Index API Token [env: OSS_INDEX_TOKEN]")
    src_grp.add_argument("--min-cvss", type=float, default=0.0,
                         help="Minimaler CVSS Score (z.B. 7.0)")
    src_grp.add_argument("--package-map", metavar="FILE",
                         help="Externe JSON/YAML Package-Map Datei")
    src_grp.add_argument("--no-cache", action="store_true",
                         help="API-Cache deaktivieren")
    src_grp.add_argument("--cache-file", default=None,
                         metavar="FILE",
                         help="Pfad zur Cache-Datei (Standard: /tmp/cve_scanner_cache.json)")
    src_grp.add_argument("--cache-ttl", type=int, default=None,
                         metavar="HOURS",
                         help="Cache-Gültigkeitsdauer in Stunden (Standard: 24)")

    out_grp = p.add_argument_group("Output")
    out_grp.add_argument("--output", default="./reports",
                         help="Ausgabeverzeichnis")
    out_grp.add_argument("--verbose", "-v", action="store_true",
                         help="Debug-Ausgabe")

    return p.parse_args()


def main():
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Konfiguration laden
    cfg = load_config(args.config)

    # Parameter aus CLI (überschreiben Config)
    omd_root    = Path(args.omd_root or cfg.get("checkmk", "omd_root"))
    min_cvss    = args.min_cvss or cfg.getfloat("nvd", "min_cvss_score", fallback=0.0)
    nvd_key     = args.nvd_key or cfg.get("nvd", "api_key") or \
                  os.environ.get("NVD_API_KEY")
    output_dir  = args.output or cfg.get("output", "directory")
    use_cache   = not args.no_cache and cfg.getboolean("cache", "enabled", fallback=True)
    cache_file  = (args.cache_file or cfg.get("cache", "file", fallback="/tmp/cve_scanner_cache.json"))
    cache_ttl   = (args.cache_ttl or cfg.getint("cache", "ttl_hours", fallback=24)) * 3600
    pkg_map_file = args.package_map or cfg.get("package_map", "file", fallback="") or None

    # Package-Map initialisieren (eingebaut + optional externe Datei)
    init_package_map(pkg_map_file)

    use_nvd     = not args.no_nvd and cfg.getboolean("nvd", "enabled", fallback=True)
    use_osv     = not args.no_osv and cfg.getboolean("osv", "enabled", fallback=True)
    use_oss     = not args.no_oss and cfg.getboolean("oss_index", "enabled", fallback=True)
    use_kev     = not args.no_kev and cfg.getboolean("cisa_kev", "enabled", fallback=True)
    oss_user    = args.oss_user or cfg.get("oss_index", "username", fallback="")
    oss_token   = args.oss_token or cfg.get("oss_index", "token", fallback="")
    kev_cache   = cfg.get("cisa_kev", "cache_dir", fallback="/tmp")

    if not use_nvd and not use_osv and not use_oss:
        log.error("Mindestens eine Scan-Quelle muss aktiv sein!")
        sys.exit(1)

    # Reader initialisieren
    reader = CheckmkInventoryReader(omd_root=omd_root)

    # Sites ermitteln
    if args.sites:
        sites = args.sites
    elif args.all_sites or cfg.get("checkmk", "sites").strip() == "":
        sites = reader.discover_sites()
    else:
        sites = [s.strip() for s in cfg.get("checkmk", "sites").split(",")
                 if s.strip()]

    if not sites:
        log.error("Keine Sites gefunden! --sites angeben oder "
                  f"sicherstellen dass {omd_root} existiert.")
        sys.exit(1)

    # Host-Filter
    host_filter: Optional[list[str]] = None
    if args.hosts:
        host_filter = args.hosts
    elif cfg.get("checkmk", "hosts").strip():
        host_filter = [h.strip() for h in
                       cfg.get("checkmk", "hosts").split(",") if h.strip()]

    # --list-hosts: nur Hosts anzeigen, nicht scannen
    if args.list_hosts:
        for site in sites:
            hosts = reader.get_hosts(site)
            print(f"\n[{site}] — {len(hosts)} Hosts:")
            for h in hosts:
                print(f"  {h}")
        return

    # Clients
    nvd_client = NvdClient(api_key=nvd_key, min_cvss_score=min_cvss) \
                 if use_nvd else None
    osv_client = OsvClient(min_cvss_score=min_cvss) \
                 if use_osv else None
    oss_client   = OssIndexClient(username=oss_user, token=oss_token,
                                min_cvss_score=min_cvss) \
                   if use_oss else None
    kev_client   = CisaKevClient(cache_dir=kev_cache) \
                   if use_kev else None
    cache_client = ApiCache(cache_file=cache_file, ttl_seconds=cache_ttl) \
                   if use_cache else None

    reporter = ReportGenerator(output_dir=output_dir)
    scanner  = CveScanner(reader, nvd_client, osv_client, oss_client,
                          kev_client, cache_client)

    sources = []
    if use_osv: sources.append("OSV.dev (Batch)")
    if use_oss: sources.append(f"OSS Index (Batch{', Auth' if oss_user else ''})")
    if use_nvd: sources.append(f"NVD (nur Mapping-Pakete, {'mit' if nvd_key else 'ohne'} Key)")
    if use_kev:   sources.append("CISA KEV (Anreicherung)")
    if use_cache: sources.append(f"Cache ({cache_ttl//3600}h TTL, {cache_file})")

    log.info("=" * 60)
    log.info("Checkmk CVE Scanner v4.0 — Local Mode")
    log.info(f"  OMD Root: {omd_root}")
    log.info(f"  Sites:    {', '.join(sites)}")
    log.info(f"  Hosts:    {host_filter or 'alle'}")
    log.info(f"  Quellen:  {' + '.join(sources)}")
    log.info(f"  Min CVSS: {min_cvss}")
    log.info(f"  Output:   {output_dir}")
    log.info("=" * 60)

    findings         = scanner.scan(sites, host_filter=host_filter)
    summary, by_host = CveScanner.build_summary(findings)

    json_path    = reporter.write_json(findings, summary)
    csv_path     = reporter.write_csv(findings)
    summary_path = reporter.write_summary_csv(by_host)

    print("\n" + "=" * 60)
    print("SCAN ABGESCHLOSSEN")
    print("=" * 60)
    print(f"Sites gescannt:     {', '.join(sites)}")
    print(f"Gesamt Findings:    {summary['total_findings']}")
    print(f"Betroffene Hosts:   {summary['affected_hosts']}")
    print()
    print("Nach Schweregrad:")
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"):
        c = summary["by_severity"].get(sev, 0)
        if c:
            print(f"  {sev:<10} {c:>5}  {'█' * min(c, 40)}")
    print()
    kev_n = summary.get("kev_exploited_count", 0)
    if kev_n:
        print(f"⚠️  CISA KEV (aktiv ausgenutzt): {kev_n} Findings")
        print()
    print("Nach Quelle:")
    for src, c in summary.get("by_source", {}).items():
        if c:
            label = {"NVD": "NVD only   ", "OSV": "OSV.dev    ",
                     "OSS": "OSS Index  ", "NVD+OSV": "NVD + OSV  ",
                     "OTHER": "Andere     "}.get(src, src)
            print(f"  {label}  {c}")
    print()
    print("Top anfällige Software:")
    for e in summary["top_vulnerable_software"][:5]:
        print(f"  {e['software']:<40} {e['finding_count']} Findings")
    print()
    print("Reports:")
    print(f"  JSON:    {json_path}")
    print(f"  CSV:     {csv_path}")
    print(f"  Summary: {summary_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
XIQ Inventory → CMK Hosts
==========================
Liest die Switch- oder AP-Tabelle aus dem XIQ-Inventory eines CMK-Hosts
(Standard: 'extreme') und legt die Einträge als CMK-Hosts über die REST API an.

Voraussetzungen:
  - Als OMD-Site-User ausführen (oder Pfad zum Inventory über --inv-dir angeben)
  - CMK Automation-User mit Passwort (Setup → Users → automation)
  - Zielordner existiert in CMK (Setup → Hosts → Ordner)

Beispiele:
  # Dry-Run: zeigt welche Switches angelegt würden
  python3 xiq_create_hosts_from_inventory.py --password SECRET --dry-run

  # Switches anlegen im CMK-Ordner /sw
  python3 xiq_create_hosts_from_inventory.py --password SECRET --folder /sw

  # Nur verbundene Switches, anschließend Changes aktivieren
  python3 xiq_create_hosts_from_inventory.py --password SECRET --folder /sw
      --only-connected --activate

  # APs anlegen (statt Switches)
  python3 xiq_create_hosts_from_inventory.py --password SECRET --folder /ap --table ap

  # Andere Site / anderer Inventory-Host
  python3 xiq_create_hosts_from_inventory.py --site prod --inv-host extreme
      --password SECRET --folder /sw
"""

from __future__ import annotations

import argparse
import ast
import gzip
import json
import sys
import urllib.request
import ssl
from pathlib import Path


# ---------------------------------------------------------------------------
# Inventory lesen
# ---------------------------------------------------------------------------

def read_inventory(inv_dir: Path, hostname: str) -> dict:
    """
    Liest die CMK-Inventory-Datei eines Hosts.
    Unterstützt alle Formate: .json, .json.gz, Python-Literal, .gz
    """
    candidates: list[tuple[Path, bool, bool]] = [
        (inv_dir / f"{hostname}.json",    False, True),
        (inv_dir / f"{hostname}.json.gz", True,  True),
        (inv_dir / hostname,              False, False),
        (inv_dir / f"{hostname}.gz",      True,  False),
    ]

    for path, is_gz, is_json in candidates:
        if not path.exists():
            continue
        try:
            if is_gz:
                with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
                    raw = fh.read()
            else:
                raw = path.read_text(encoding="utf-8", errors="replace")

            return json.loads(raw) if is_json else ast.literal_eval(raw)
        except Exception as exc:
            print(f"  Warnung: {path} konnte nicht gelesen werden: {exc}", file=sys.stderr)

    raise FileNotFoundError(
        f"Keine Inventory-Datei für '{hostname}' in {inv_dir}"
    )


def extract_table(inv: dict, table_name: str) -> list[dict]:
    """
    Liest eine Tabelle aus dem XIQ-Inventory-Pfad:
      Nodes → extreme → Nodes → <table_name> → Table → Rows
    """
    try:
        table = inv["Nodes"]["extreme"]["Nodes"][table_name]["Table"]
        return table.get("Rows", table.get("rows", []))
    except (KeyError, TypeError):
        return []


# ---------------------------------------------------------------------------
# CMK REST API
# ---------------------------------------------------------------------------

def _make_ssl_ctx(verify: bool) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _request(method: str, url: str, username: str, password: str,
             payload: dict | None, verify: bool) -> tuple[int, dict]:
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {username} {password}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, context=_make_ssl_ctx(verify), timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        return exc.code, {"error": body}


def get_existing_hosts(base_url: str, username: str, password: str,
                       verify: bool) -> set[str]:
    """Alle bereits angelegten Hostnamen abfragen (CMK 2.5: kein folder-Filter)."""
    url = f"{base_url}/domain-types/host_config/collections/all?effective_attributes=false"
    status, body = _request("GET", url, username, password, None, verify)
    if status != 200:
        print(f"  Warnung: Hosts konnten nicht abgefragt werden "
              f"(HTTP {status}) — Duplikat-Erkennung deaktiviert", file=sys.stderr)
        return set()
    return {h["id"] for h in body.get("value", [])}


def create_host(base_url: str, username: str, password: str,
                hostname: str, ip: str, folder: str,
                labels: dict, verify: bool) -> str:
    """
    Legt einen Host an. Rückgabe: 'created', 'exists', 'error'.
    CMK 2.5: folder im Body als '/sw', Fehler 400 kann 'already exists' bedeuten.
    """
    folder_api = "/" + folder.strip("/")
    url = f"{base_url}/domain-types/host_config/collections/all"
    payload = {
        "host_name": hostname,
        "folder": folder_api,
        "attributes": {
            "ipaddress": ip,
            "labels": labels,
        },
    }
    status, body = _request("POST", url, username, password, payload, verify)
    if status in (200, 204):
        return "created"
    # "already exists" → als Skip werten, nicht als Fehler
    fields = body.get("fields", {})
    host_msgs = fields.get("host_name", [])
    if any("already exists" in str(m) for m in host_msgs):
        return "exists"
    err = body.get("title") or body.get("detail") or body.get("error", "")
    print(f"  FEHLER ({status}): {err[:120]}", file=sys.stderr)
    return "error"


def activate_changes(base_url: str, username: str, password: str,
                     site: str, verify: bool) -> bool:
    """Aktiviert alle ausstehenden Änderungen (CMK 2.5: If-Match + force_foreign_changes)."""
    url = (f"{base_url}/domain-types/activation_run"
           "/actions/activate-changes/invoke")
    payload = {
        "redirect": False,
        "sites": [site],
        "force_foreign_changes": True,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {username} {password}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "If-Match": "*",
        },
    )
    try:
        with urllib.request.urlopen(req, context=_make_ssl_ctx(verify), timeout=120) as r:
            return r.status in (200, 202)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"  Aktivierung HTTP {exc.code}: {body[:200]}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="XIQ-Inventory → CMK-Hosts anlegen (Switches oder APs)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--site",        default="test",
                        help="OMD-Site-Name (Standard: test)")
    parser.add_argument("--inv-host",    default="extreme",
                        help="CMK-Hostname dessen Inventory gelesen wird (Standard: extreme)")
    parser.add_argument("--inv-dir",     default=None,
                        help="Pfad zum Inventory-Verzeichnis (Standard: /omd/sites/<site>/var/check_mk/inventory)")
    parser.add_argument("--table",       default="sw", choices=["sw", "ap"],
                        help="Inventory-Tabelle: sw=Switches, ap=APs (Standard: sw)")
    parser.add_argument("--folder",      default="/sw",
                        help="Zielordner in CMK, z.B. /sw oder /ap (Standard: /sw)")
    parser.add_argument("--cmk-url",     default=None,
                        help="CMK-URL (Standard: http://localhost/<site>/check_mk/api/1.0)")
    parser.add_argument("--username",    default="automation",
                        help="CMK Automation-User (Standard: automation)")
    parser.add_argument("--password",    required=True,
                        help="Passwort / Secret des Automation-Users")
    parser.add_argument("--only-connected", action="store_true",
                        help="Nur Geräte mit connected=True anlegen")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Nur anzeigen was angelegt würde, nichts schreiben")
    parser.add_argument("--activate",    action="store_true",
                        help="CMK-Changes nach dem Anlegen aktivieren")
    parser.add_argument("--no-verify",   action="store_true",
                        help="TLS-Zertifikat nicht prüfen")
    args = parser.parse_args()

    inv_dir = Path(args.inv_dir) if args.inv_dir else Path(f"/omd/sites/{args.site}/var/check_mk/inventory")
    base_url = args.cmk_url or f"http://localhost/{args.site}/check_mk/api/1.0"
    verify = not args.no_verify

    # ── Inventory lesen ──────────────────────────────────────────────────────
    print(f"Lese Inventory: {inv_dir / args.inv_host}  (Tabelle: {args.table})")
    try:
        inv = read_inventory(inv_dir, args.inv_host)
    except FileNotFoundError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        sys.exit(1)

    rows = extract_table(inv, args.table)
    if not rows:
        print(f"FEHLER: Tabelle '{args.table}' ist leer oder nicht vorhanden.", file=sys.stderr)
        sys.exit(1)

    print(f"Gefunden: {len(rows)} Einträge")

    # ── Filter ───────────────────────────────────────────────────────────────
    if args.only_connected:
        before = len(rows)
        rows = [r for r in rows if r.get("connected")]
        print(f"Nach Filter 'only-connected': {len(rows)} (von {before})")

    # Einträge ohne Hostname oder IP überspringen
    valid = [(r["hostname"].strip(), r["ip"].strip()) for r in rows
             if r.get("hostname", "").strip() and r.get("ip", "").strip()]
    skipped_no_data = len(rows) - len(valid)
    if skipped_no_data:
        print(f"Übersprungen (kein hostname/ip): {skipped_no_data}")

    # ── Dry-Run ──────────────────────────────────────────────────────────────
    if args.dry_run:
        print(f"\nDRY-RUN — würde {len(valid)} Hosts in Ordner '{args.folder}' anlegen:\n")
        for hostname, ip in valid[:20]:
            print(f"  {hostname:50s}  {ip}")
        if len(valid) > 20:
            print(f"  ... und {len(valid) - 20} weitere")
        return

    # ── Vorhandene Hosts ermitteln ────────────────────────────────────────────
    print(f"\nPrüfe vorhandene Hosts in Ordner '{args.folder}'...")
    existing = get_existing_hosts(base_url, args.username, args.password, verify)
    print(f"Bereits vorhanden: {len(existing)}")

    # ── Hosts anlegen ────────────────────────────────────────────────────────
    created = skipped = errors = 0

    for hostname, ip in valid:
        if hostname in existing:
            skipped += 1
            continue

        # Labels aus Inventory-Daten
        row = next(r for r in rows if r.get("hostname", "").strip() == hostname)
        labels = {}
        if row.get("model"):
            labels["xiq_model"] = row["model"]
        if row.get("managed_by"):
            labels["xiq_managed_by"] = row["managed_by"]
        if row.get("device_function"):
            labels["xiq_function"] = row["device_function"].lower()

        print(f"  Anlegen: {hostname:50s}  {ip}")
        result = create_host(base_url, args.username, args.password,
                             hostname, ip, args.folder, labels, verify)
        if result == "created":
            created += 1
        elif result == "exists":
            skipped += 1
        else:
            errors += 1

    # ── Zusammenfassung ───────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Ergebnis:")
    print(f"  Angelegt:    {created}")
    print(f"  Übersprungen (bereits vorhanden): {skipped}")
    print(f"  Fehler:      {errors}")
    print(f"{'='*60}")

    if created == 0:
        print("Keine neuen Hosts angelegt.")
        return

    if args.activate:
        print("\nAktiviere Changes...")
        if activate_changes(base_url, args.username, args.password, args.site, verify):
            print("Changes aktiviert.")
        else:
            print("Aktivierung fehlgeschlagen oder noch ausstehend — bitte in CMK-GUI prüfen.")
    else:
        print(f"\nHinweis: Changes noch nicht aktiviert.")
        print(f"  → CMK GUI: Setup → Activate pending changes")
        print(f"  → oder Script mit --activate erneut ausführen")


if __name__ == "__main__":
    main()

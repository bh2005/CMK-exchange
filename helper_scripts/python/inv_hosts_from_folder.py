#!/usr/bin/env python3
"""
CheckMK 2.4: HW/SW Inventory für alle Hosts eines Ordners
Kombination aus REST API (Ordner → Hosts) + host_inv_api (Inventory-Daten)
"""

import json
import urllib.request
import urllib.parse
import ssl

# ── Konfiguration ────────────────────────────────────────────────────────────
CMK_HOST   = "192.168.1.10"
CMK_SITE   = "mysite"
USERNAME   = "automation"
PASSWORD   = "your-automation-secret"
PROTO      = "https"   # oder "http"

# Ordnerpfad in CheckMK-Notation:
#   Root-Folder   → ""
#   /linux        → "linux"
#   /linux/debian → "linux~debian"
FOLDER_PATH = "linux~debian"

VERIFY_SSL = True  # False bei self-signed Zertifikaten

BASE_URL    = f"{PROTO}://{CMK_HOST}/{CMK_SITE}/check_mk"
REST_URL    = f"{BASE_URL}/api/1.0"
INV_URL     = f"{BASE_URL}/host_inv_api.py"
# ─────────────────────────────────────────────────────────────────────────────


def make_ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not VERIFY_SSL:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def rest_get(path: str, params: dict = None) -> dict:
    """GET gegen den CheckMK REST API Endpunkt."""
    url = f"{REST_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {USERNAME} {PASSWORD}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, context=make_ssl_ctx(), timeout=30) as r:
        return json.loads(r.read())


def get_hosts_in_folder(folder: str, recursive: bool = True) -> list[str]:
    """
    Alle Hostnamen aus einem CheckMK-Ordner per REST API holen.
    
    Endpoint: GET /domain-types/host_config/collections/all
    Parameter:
      - folder          : Ordnerpfad (~ als Trennzeichen, z.B. "linux~debian")
      - recurse         : auch Unterordner einschließen
      - effective_attrs : false — wir brauchen nur den Namen
    """
    params = {
        "folder": folder,
        "recurse": "true" if recursive else "false",
        "effective_attributes": "false",
    }
    data = rest_get("/domain-types/host_config/collections/all", params)
    return [h["id"] for h in data.get("value", [])]


def get_inventory(hostnames: list[str], paths: list[str] = None) -> dict:
    """
    HW/SW-Inventar für eine Liste von Hosts per host_inv_api holen.
    
    Die host_inv_api existiert seit CheckMK 1.x und ist auch in 2.4
    weiterhin verfügbar — sie ist NICHT die alte Web-API (die 2.2 entfernt
    wurde), sondern ein eigenständiger Endpunkt.
    
    Optional: paths filtert auf bestimmte Inventory-Pfade, z.B.:
      [".hardware.memory.*", ".software.os.*"]
    """
    payload = {"hosts": hostnames}
    if paths:
        payload["paths"] = paths

    body = json.dumps({"request": payload}).encode()
    # Alternativ als Query-Parameter (beide Varianten funktionieren):
    url = f"{INV_URL}?output_format=json&request={urllib.parse.quote(json.dumps(payload))}"

    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {USERNAME} {PASSWORD}",
    })
    with urllib.request.urlopen(req, context=make_ssl_ctx(), timeout=30) as r:
        result = json.loads(r.read())

    if result.get("result_code") != 0:
        raise RuntimeError(f"host_inv_api Fehler: {result.get('result')}")
    return result["result"]


def main():
    print(f"▶ Hole Hosts aus Ordner: '{FOLDER_PATH}'")
    hosts = get_hosts_in_folder(FOLDER_PATH, recursive=True)
    print(f"  → {len(hosts)} Host(s) gefunden: {hosts}")

    if not hosts:
        print("Keine Hosts gefunden. Ordnerpfad korrekt?")
        return

    # Inventory für alle gefundenen Hosts in einem API-Call
    # Optional: paths einschränken für bessere Performance
    inventory = get_inventory(
        hostnames=hosts,
        paths=[
            ".hardware.cpu.*",
            ".hardware.memory.*",
            ".software.os.*",
            ".software.packages:*",   # Tabellen mit : statt .
        ]
    )

    # Ausgabe / Weiterverarbeitung
    for hostname, inv_data in inventory.items():
        print(f"\n{'='*60}")
        print(f"  Host: {hostname}")
        print(f"{'='*60}")

        hw = inv_data.get("Nodes", {}).get("hardware", {})
        sw = inv_data.get("Nodes", {}).get("software", {})

        # CPU
        cpu = hw.get("Nodes", {}).get("cpu", {}).get("Attributes", {}).get("Pairs", {})
        if cpu:
            print(f"  CPU   : {cpu.get('model', 'n/a')} — {cpu.get('cpus', '?')} CPUs")

        # RAM
        mem = hw.get("Nodes", {}).get("memory", {}).get("Attributes", {}).get("Pairs", {})
        if mem:
            ram_gb = mem.get("total_ram_usable", 0) / 1024**3
            print(f"  RAM   : {ram_gb:.1f} GB")

        # OS
        os_info = sw.get("Nodes", {}).get("os", {}).get("Attributes", {}).get("Pairs", {})
        if os_info:
            print(f"  OS    : {os_info.get('name', 'n/a')} {os_info.get('version', '')}")

        # Pakete (Tabelle)
        pkgs = sw.get("Nodes", {}).get("packages", {}).get("Table", {}).get("Rows", [])
        if pkgs:
            print(f"  Pakete: {len(pkgs)} installiert")

    # Optional: Als JSON exportieren
    with open("inventory_export.json", "w") as f:
        json.dump(inventory, f, indent=2)
    print("\n✓ Export nach inventory_export.json")


if __name__ == "__main__":
    main()

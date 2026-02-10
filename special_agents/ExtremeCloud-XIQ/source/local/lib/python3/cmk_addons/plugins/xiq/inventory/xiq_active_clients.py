# -*- coding: utf-8 -*-
# ASCII-safe: no umlauts, comments plain ASCII

from cmk.agent_based.v2 import (
    InventoryPlugin,
    InventoryResult,
    Attributes,
    TableRow,
    register,
    get_value_store,
)

SECTION_NAME = "xiq_active_clients"

def parse_xiq_active_clients(string_table):
    # Section is JSON based; agent prints with :json, so Checkmk hands us a Python object.
    # In v2 API, the "string_table" is actually the parsed JSON object for :json sections.
    # We pass it through as dict.
    if isinstance(string_table, dict):
        return string_table
    return {}

def inventory_xiq_active_clients(section):
    """
    Build inventory tree under:
      ExtremeCloudIQ
        Clients (active)
          Summary
          Clients [table rows]
    """
    if not section or not isinstance(section, dict):
        return

    inv = InventoryResult(path=["ExtremeCloudIQ", "Clients (active)"])

    # Summary node
    summary = section.get("summary") or {}
    band = summary.get("band") or {}
    per_ssid = summary.get("per_ssid") or {}
    total = summary.get("total")

    inv.append(
        Attributes(
            path=["ExtremeCloudIQ", "Clients (active)", "Summary"],
            attributes={
                "total": total if isinstance(total, int) else 0,
                "2.4GHz": int(band.get("2.4GHz", 0)),
                "5GHz": int(band.get("5GHz", 0)),
                "6GHz": int(band.get("6GHz", 0)),
            },
        )
    )

    # Per SSID attributes (flat list as attributes; compact)
    # e.g., SSID: KplusS -> 2.4GHz, 5GHz, 6GHz
    for ssid, counts in sorted(per_ssid.items(), key=lambda x: x[0].lower()):
        try:
            inv.append(
                Attributes(
                    path=["ExtremeCloudIQ", "Clients (active)", "Summary", "SSID"],
                    key_columns={"name": ssid},
                    attributes={
                        "2.4GHz": int((counts or {}).get("2.4GHz", 0)),
                        "5GHz": int((counts or {}).get("5GHz", 0)),
                        "6GHz": int((counts or {}).get("6GHz", 0)),
                    },
                )
            )
        except Exception:
            continue

    # Clients table (optional, if agent delivered details)
    clients = section.get("clients") or []
    for c in clients:
        try:
            inv.append(
                TableRow(
                    path=["ExtremeCloudIQ", "Clients (active)", "Clients"],
                    key_columns={
                        "mac": c.get("mac") or "",
                    },
                    inventory_columns={
                        "hostname": c.get("hostname") or "",
                        "ip": c.get("ip") or "",
                        "ssid": c.get("ssid") or "",
                        "band": c.get("band") or "",
                        "bssid": c.get("bssid") or "",
                        "rssi": int(c.get("rssi") or 0),
                        "snr": int(c.get("snr") or 0),
                        "channel": int(c.get("channel") or 0),
                        "ap_name": c.get("ap_name") or "",
                        "ap_id": str(c.get("ap_id") or ""),
                        "os_type": c.get("os_type") or "",
                        "user_profile": c.get("user_profile") or "",
                        "connected": bool(c.get("connected", False)),
                    },
                )
            )
        except Exception:
            continue

    return inv

register.inventory_plugin(
    name=SECTION_NAME,
    sections=[SECTION_NAME],
    parse_function=parse_xiq_active_clients,
    inventory_function=inventory_xiq_active_clients,
)

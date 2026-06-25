#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : inventory_active_clients.py
#
# Description:
#   Checkmk Inventory plugin for ExtremeCloudIQ active client lists.
#   Creates one inventory table entry per active WiFi client, including
#   MAC, IP, SSID, band, RSSI, SNR, channel, BSSID, OS type, user profile
#   and connectivity state. Output is stored under inventory path:
#       extreme.clients
# =============================================================================

from typing import Mapping, Any, Iterable, Optional, List, Union
from cmk.agent_based.v2 import InventoryPlugin, TableRow


# ---------------------------------------------------------------------
# SAFE STRING CONVERSION
# ---------------------------------------------------------------------
def _to_str(x: Any) -> str:
    """Convert arbitrary value to string, safe for None."""
    return "" if x is None else str(x)


# ---------------------------------------------------------------------
# SECTION NORMALIZATION – ensure mapping or return empty
# ---------------------------------------------------------------------
def _as_mapping(
    section: Optional[Union[Mapping[str, Any], List[List[str]]]]
) -> Mapping[str, Any]:
    """
    Inventory plugins should ideally receive parsed dict sections
    (from sections.py). If anything else is passed, skip gracefully.
    """
    if not section:
        return {}
    return section if isinstance(section, Mapping) else {}


# ---------------------------------------------------------------------
# INVENTORY FUNCTION – enumerate active clients as inventory rows
# ---------------------------------------------------------------------
def inventory_xiq_active_clients(
    section: Optional[Union[Mapping[str, Any], List[List[str]]]]
) -> Iterable[TableRow]:
    """
    Expected parsed section structure (from <<<<xiq_active_clients>>>>):

    {
      "device_id": 9178...,
      "hostname": "AP-XYZ",
      "clients": [
         {
            "mac": "...", "hostname": "...", "ip": "...", "ssid": "...",
            "band": "...", "bssid": "...", "rssi": "...", "snr": "...",
            "channel": "...", "ap_name": "...", "ap_id": "...",
            "os_type": "...", "user_profile": "...", "connected": "..."
         },
         ...
      ]
    }
    """

    data = _as_mapping(section)
    if not data:
        return  # clean skip

    device_id = data.get("device_id")
    ap_name = _to_str(data.get("hostname"))

    # Clients: stable order → first by SSID, then by MAC
    clients: List[Mapping[str, Any]] = data.get("clients") or []

    def _client_sort_key(c: Mapping[str, Any]) -> str:
        mac = _to_str(c.get("mac")).lower()
        ssid = _to_str(c.get("ssid")).lower()
        return f"{ssid}__{mac}" if (mac or ssid) else "zzz"

    for idx, c in enumerate(sorted(clients, key=_client_sort_key)):
        mac = _to_str(c.get("mac")) or f"idx-{idx}"

        yield TableRow(
            path=["extreme", "clients"],
            key_columns={
                "device_id": _to_str(device_id),
                "mac": mac,
            },
            inventory_columns={
                "hostname":     _to_str(c.get("hostname")),
                "ip":           _to_str(c.get("ip")),
                "ssid":         _to_str(c.get("ssid")),
                "band":         _to_str(c.get("band")),
                "bssid":        _to_str(c.get("bssid")),
                "rssi":         _to_str(c.get("rssi")),
                "snr":          _to_str(c.get("snr")),
                "channel":      _to_str(c.get("channel")),
                "ap_name":      _to_str(c.get("ap_name") or ap_name),
                "ap_id":        _to_str(c.get("ap_id") or device_id),
                "os_type":      _to_str(c.get("os_type")),
                "user_profile": _to_str(c.get("user_profile")),
                "connected":    _to_str(c.get("connected")),
            },
        )


# ---------------------------------------------------------------------
# PLUGIN REGISTRATION
# ---------------------------------------------------------------------
inventory_plugin_xiq_active_clients = InventoryPlugin(
    name="xiq_inventory_active_clients",
    sections=["xiq_active_clients"],
    inventory_function=inventory_xiq_active_clients,
)
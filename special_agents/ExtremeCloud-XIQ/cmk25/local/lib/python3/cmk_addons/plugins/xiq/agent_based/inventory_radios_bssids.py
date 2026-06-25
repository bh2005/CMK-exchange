#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : inventory_radios_bssids.py
#
# Description:
#   Checkmk Inventory plugins for ExtremeCloudIQ radio details and BSSIDs.
#   Consumes the parsed section "xiq_radio_information" and creates
#   inventory entries under:
#     - extreme.ap_radios  (per-radio attributes)
#     - extreme.ap_bssids  (per-SSID/BSSID tuples with frequency)
# =============================================================================

from typing import Mapping, Any, Iterable, Optional, List
from cmk.agent_based.v2 import InventoryPlugin, TableRow

from .common import format_mac, _to_int_safe


# ---------------------------------------------------------------------
# INVENTORY: AP RADIOS – one row per radio with basic attributes
# ---------------------------------------------------------------------
def inventory_xiq_ap_radios(
    section: Optional[Mapping[str, Any]]
) -> Iterable[TableRow]:

    if not section:
        return

    radios = section.get("_radios") or section.get("radios") or []
    if not isinstance(radios, list):
        return

    device_id = section.get("device_id") or section.get("_device_id")
    hostname  = section.get("hostname") or section.get("_hostname", "")

    for r in radios:
        radio_name = (r.get("radio_name") or r.get("name") or "").strip()
        radio_mac  = format_mac(r.get("radio_mac") or r.get("mac_address") or "")
        frequency  = r.get("frequency", "")
        unique_key = f"{device_id}_{radio_name}"

        yield TableRow(
            path=["extreme", "ap_radios"],   # <-- correct inventory path
            key_columns={"radio_key": unique_key},
            inventory_columns={
                "radio_name":     radio_name,
                "radio_mac":      radio_mac,
                "frequency":      frequency,
                "channel_number": _to_int_safe(r.get("channel_number")),
                "channel_width":  _to_int_safe(r.get("channel_width")),
                "mode":           r.get("mode", ""),
                "power":          _to_int_safe(r.get("power")),
                "hostname":       hostname,
                "device_id":      device_id,
            },
        )


# ---------------------------------------------------------------------
# INVENTORY: AP BSSIDs – one row per SSID/BSSID/frequency tuple
# ---------------------------------------------------------------------
def inventory_xiq_ap_bssids(
    section: Optional[Mapping[str, Any]]
) -> Iterable[TableRow]:

    if not section:
        return

    radios = section.get("_radios") or section.get("radios") or []
    if not isinstance(radios, list):
        return

    device_id = section.get("device_id") or section.get("_device_id")
    hostname  = section.get("hostname") or section.get("_hostname", "")

    rows: List[Mapping[str, Any]] = []

    for r in radios:
        freq = r.get("frequency", "")
        radio_name = (r.get("radio_name") or r.get("name") or "").strip()

        for w in (r.get("wlans") or []):
            ssid  = (w.get("ssid") or "").strip()
            bssid = format_mac(w.get("bssid", ""))

            if not ssid or not bssid:
                continue

            rows.append({
                "ssid": ssid,
                "bssid": bssid,
                "frequency": freq,
                "device_id": device_id,
                "hostname": hostname,
                "radio_name": radio_name,
            })

    # stable order for inventory diffs
    rows.sort(key=lambda e: (e["ssid"], e["frequency"], e["bssid"]))

    for e in rows:
        unique_key = f"{e['device_id']}_{e['ssid']}_{e['bssid']}"

        yield TableRow(
            path=["extreme", "ap_bssids"],   # <-- correct inventory path
            key_columns={"bssid_key": unique_key},
            inventory_columns={
                "ssid":       e["ssid"],
                "bssid":      e["bssid"],
                "frequency":  e["frequency"],
                "device_id":  e["device_id"],
                "hostname":   e["hostname"],
                "radio_name": e["radio_name"],
            },
        )


# ---------------------------------------------------------------------
# REGISTRATION
# ---------------------------------------------------------------------
inventory_plugin_xiq_ap_radios_plugin = InventoryPlugin(
    name="xiq_inventory_ap_radios",
    sections=["xiq_radio_information"],
    inventory_function=inventory_xiq_ap_radios,
)

inventory_plugin_xiq_ap_bssids_plugin = InventoryPlugin(
    name="xiq_inventory_ap_bssids",
    sections=["xiq_radio_information"],
    inventory_function=inventory_xiq_ap_bssids,
)
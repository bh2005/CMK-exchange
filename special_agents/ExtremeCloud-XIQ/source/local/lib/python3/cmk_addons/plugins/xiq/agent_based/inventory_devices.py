#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : inventory_devices.py
#
# Description:
#   Checkmk Inventory plugin for ExtremeCloudIQ device inventory.
#   Consumes the H1 section "extreme_device_inventory" (table-like rows)
#   and populates inventory nodes under:
#       - extreme.ap     (for device_function containing "AP")
#       - extreme.sw     (for device_function containing "SW")
#       - extreme.misc   (for everything else)
#   Includes hostname, serial, MAC, IP, model, software, locations
#   (full and leaf), device function, manager, and connectivity flag.
# =============================================================================

from typing import Iterable, List
from cmk.agent_based.v2 import InventoryPlugin, TableRow

from .common import extract_location_leaf, norm_connected


# ---------------------------------------------------------------------
# HELPERS – safe column access
# ---------------------------------------------------------------------
def _col(row: List[str], idx: int, default: str = "") -> str:
    """Return row[idx] if present, else default (keeps inventory robust)."""
    return row[idx] if (0 <= idx < len(row)) else default


# ---------------------------------------------------------------------
# INVENTORY FUNCTION – map device rows to inventory entries
# ---------------------------------------------------------------------
def inventory_xiq_devices(section: List[List[str]]) -> Iterable[TableRow]:
    """
    Expected row layout (11 columns):
      0 id | 1 hostname | 2 serial | 3 mac | 4 ip | 5 model | 6 sw |
      7 location_full | 8 device_function | 9 managed_by | 10 connected

    Notes:
    - This plugin does not filter devices: ALL rows are inventoried.
    - Connectivity is normalized via common.norm_connected().
    """
    for row in section:
        dev_id      = _col(row, 0)
        hostname    = _col(row, 1)
        serial      = _col(row, 2)
        mac         = _col(row, 3)
        ip          = _col(row, 4)
        model       = _col(row, 5)
        sw          = _col(row, 6)
        loc_full    = _col(row, 7)
        dev_fun     = _col(row, 8)
        managed_by  = _col(row, 9)
        connected_v = _col(row, 10, None)  # may be missing

        dev_fun_u = (dev_fun or "").upper()
        if "AP" in dev_fun_u:
            path = ["extreme", "ap"]
        elif "SW" in dev_fun_u:
            path = ["extreme", "sw"]
        else:
            path = ["extreme", "misc"]

        attrs = {
            "hostname":        hostname,
            "serial":          serial,
            "mac":             mac,
            "ip":              ip,
            "model":           model,
            "software":        sw,
            "location_full":   loc_full,
            "location_leaf":   extract_location_leaf(loc_full),
            "device_function": dev_fun_u,
            "managed_by":      managed_by,
        }
        if connected_v is not None:
            attrs["connected"] = norm_connected(connected_v)

        yield TableRow(
            path=path,
            key_columns={"id": dev_id},
            inventory_columns=attrs,
        )


# ---------------------------------------------------------------------
# REGISTRATION
# ---------------------------------------------------------------------
inventory_plugin_xiq_devices = InventoryPlugin(
    name="xiq_inventory_devices",
    sections=["extreme_device_inventory"],
    inventory_function=inventory_xiq_devices,
)

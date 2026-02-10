#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : inventory_neighbors.py
#
# Description:
#   Checkmk Inventory plugin for ExtremeCloudIQ LLDP/CDP neighbors.
#   Consumes the section "extreme_device_neighbors" (parsed list of dicts)
#   and writes one inventory row per local-port neighbor under:
#       networking.lldp_infos
# =============================================================================

from cmk.agent_based.v2 import InventoryPlugin, TableRow


# ---------------------------------------------------------------------
# INVENTORY FUNCTION – one row per local-port neighbor
# ---------------------------------------------------------------------
def inventory_xiq_neighbors(section):
    """
    Expected element keys (as provided by the sections.py parser):
      - device_id, hostname, host_ip, local_port,
        management_ip, remote_port, port_description,
        mac_address, remote_device
    The key uses "<device_id>_<local_port>" for stable uniqueness.
    """
    for e in section:
        key = f"{e.get('device_id', '')}_{e.get('local_port', '')}"

        yield TableRow(
            path=["networking", "lldp_infos"],
            key_columns={"key": key},
            inventory_columns={
                "device_id":        e.get("device_id", ""),
                "hostname":         e.get("hostname", ""),
                "host_ip":          e.get("host_ip", ""),
                "local_port":       e.get("local_port", ""),
                "management_ip":    e.get("management_ip", ""),
                "remote_port":      e.get("remote_port", ""),
                "port_description": e.get("port_description", ""),
                "mac_address":      e.get("mac_address", ""),
                "remote_device":    e.get("remote_device", ""),
            },
        )


# ---------------------------------------------------------------------
# REGISTRATION
# ---------------------------------------------------------------------
inventory_plugin_xiq_neighbors = InventoryPlugin(
    name="xiq_inventory_neighbors",
    sections=["extreme_device_neighbors"],
    inventory_function=inventory_xiq_neighbors,
)
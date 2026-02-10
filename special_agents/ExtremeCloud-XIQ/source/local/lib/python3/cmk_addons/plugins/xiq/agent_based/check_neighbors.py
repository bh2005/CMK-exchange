#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author : Bernd Holzhauer
# Date   : 2026-02-04
# File   : check_neighbors.py
#
# Description:
#   Checkmk check plugin for ExtremeCloudIQ LLDP/CDP neighbor information.
#   Creates one service per AP (item = hostname) and provides a compact
#   summary plus a detailed list of all LLDP/CDP neighbors.
#
#   Consumes the section:
#       <<<<extreme_device_neighbors>>>>
#
#   Expected keys in each entry:
#       device_id, hostname, host_ip, local_port, management_ip,
#       remote_port, port_description, mac_address, remote_device
# =============================================================================

from __future__ import annotations

from typing import Iterable, Mapping, Any, List, Set
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)


# ---------------------------------------------------------------------
# DISCOVERY – one service per AP host name found in neighbor entries
# ---------------------------------------------------------------------
def discover_xiq_ap_neighbors(section) -> DiscoveryResult:
    """
    Creates exactly one neighbor service per AP hostname.
    """
    if not section:
        return

    seen: Set[str] = set()
    for entry in section:
        host = (entry.get("hostname") or "").strip()
        if not host or host in seen:
            continue
        seen.add(host)
        yield Service(item=host)


# ---------------------------------------------------------------------
# HELPER – return normalized MAC from the record
# ---------------------------------------------------------------------
def _norm_mac(entry: Mapping[str, Any]) -> str:
    mac = entry.get("mac_address")
    if mac:
        return str(mac)
    mac = entry.get("remote_mac")
    if mac:
        return str(mac)
    return "-"


# ---------------------------------------------------------------------
# CHECK – summary + long neighbor listing
# ---------------------------------------------------------------------
def check_xiq_ap_neighbors(
    item: str,
    params: Mapping[str, Any],
    section,
) -> Iterable[CheckResult]:
    """
    Provides:
      - Summary: <#neighbors>, first neighbor mapping
      - Notice: Detailed LLDP/CDP information in long output
    """
    if not section:
        yield Result(
            state=State.OK,
            summary=f"{item}: no neighbors reported",
        )
        return

    # Filter entries for this AP only
    rows = [
        entry for entry in section
        if ((entry.get("hostname") or "").strip() == item)
    ]

    if not rows:
        yield Result(
            state=State.OK,
            summary=f"{item}: no neighbors found",
        )
        return

    # Configurable fields for long output
    fields: List[str] = (params or {}).get("fields") or [
        "local_port",
        "remote_device",
        "remote_port",
        "management_ip",
        "mac_address",
        "port_description",
    ]

    labels = {
        "local_port": "Local Port",
        "remote_device": "Remote Device",
        "remote_name": "Remote Device",
        "remote_port": "Remote Port",
        "management_ip": "Management IP",
        "mac_address": "Remote MAC",
        "remote_mac": "Remote MAC",
        "port_description": "Port Description",
    }

    limit = int((params or {}).get("neighbor_limit", 0))  # 0 = unlimited

    # Stable sort: local_port, remote_device, remote_port
    rows.sort(
        key=lambda e: (
            e.get("local_port", "") or "",
            e.get("remote_device", "") or e.get("remote_name", "") or "",
            e.get("remote_port", "") or "",
        )
    )

    # -----------------------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------------------
    count = len(rows)
    first = rows[0]
    first_remote = first.get("remote_device") or first.get("remote_name") or "-"
    first_local = first.get("local_port") or "-"
    first_remote_port = first.get("remote_port") or "-"

    yield Result(
        state=State.OK,
        summary=f"LLDP/CDP: {count} neighbor(s), first: {first_local} -> {first_remote} ({first_remote_port})",
    )

    # -----------------------------------------------------------------
    # LONG OUTPUT (detailed)
    # -----------------------------------------------------------------
    out_lines: List[str] = ["**LLDP/CDP Neighbors**"]
    emitted = 0

    for e in rows:
        if limit and emitted >= limit:
            break

        for key in fields:
            if key in ("mac_address", "remote_mac"):
                v = _norm_mac(e)
            elif key == "remote_device":
                v = e.get("remote_device") or e.get("remote_name")
            else:
                v = e.get(key)

            if v not in (None, ""):
                out_lines.append(f"- {labels.get(key, key)}: {v}")

        out_lines.append("")  # spacing between neighbors
        emitted += 1

    details = "\n".join(out_lines).rstrip()

    yield Result(
        state=State.OK,
        notice="LLDP/CDP: detailed neighbor information available",
        details=details,
    )


# ---------------------------------------------------------------------
# REGISTRATION
# ---------------------------------------------------------------------
check_plugin_xiq_ap_neighbors = CheckPlugin(
    name="xiq_ap_neighbors",
    sections=["extreme_device_neighbors"],
    service_name="XIQ AP %s Neighbors",
    discovery_function=discover_xiq_ap_neighbors,
    check_function=check_xiq_ap_neighbors,
    check_default_parameters={
        "fields": [
            "local_port",
            "remote_device",
            "remote_port",
            "management_ip",
            "mac_address",
            "port_description",
        ],
        "neighbor_limit": 0,
    },
    check_ruleset_name="xiq_ap_neighbors_presentation",
)
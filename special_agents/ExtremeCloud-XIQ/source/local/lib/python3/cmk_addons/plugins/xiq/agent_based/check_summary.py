# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : check_summary.py
#
# Description:
#   Checkmk summary check for ExtremeCloudIQ global statistics. Uses two
#   agent sections (extreme_summary and extreme_device_inventory) to
#   compute AP counts, client totals, switching infrastructure, and
#   miscellaneous device counts. Emits perfdata and a consolidated,
#   human-readable summary.
# =============================================================================

from __future__ import annotations

from typing import Any, List, Optional, Tuple, Mapping, Iterable
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    Metric,
)

# ---------------------------------------------------------------------
# INT ? SAFE INT CONVERSION
# ---------------------------------------------------------------------
def _to_int(x: Any, default: int = 0) -> int:
    """Convert arbitrary input into int safely."""
    try:
        if x is None:
            return default
        if isinstance(x, (int, float)):
            return int(x)
        s = str(x).strip()
        if not s:
            return default
        return int(float(s))
    except Exception:
        return default


# ---------------------------------------------------------------------
# COUNT DEVICES BY FUNCTION (AP/SW/MISC)
# ---------------------------------------------------------------------
def _count_by_function(inv_rows: Optional[List[List[str]]]) -> Mapping[str, int]:
    """
    Count devices by 'device_function' column in the inventory section.
    AP / SW / MISC + TOTAL.
    """
    counts = {"AP": 0, "SW": 0, "MISC": 0, "TOTAL": 0}
    if not inv_rows:
        return counts

    for row in inv_rows:
        dev_fun = (row[8] if len(row) > 8 else "") or ""
        dev_fun_u = str(dev_fun).upper()
        if "AP" in dev_fun_u:
            counts["AP"] += 1
        elif "SW" in dev_fun_u:
            counts["SW"] += 1
        else:
            counts["MISC"] += 1
        counts["TOTAL"] += 1
    return counts


# ---------------------------------------------------------------------
# COUNT CONNECTED / DISCONNECTED APS FROM INVENTORY
# ---------------------------------------------------------------------
def _count_ap_connected(inv_rows: Optional[List[List[str]]]) -> Tuple[int, Optional[int]]:
    """
    Returns:
      (connected_APs, disconnected_APs or None if unknown)
    """
    if not inv_rows:
        return 0, None

    ap_total = 0
    ap_connected = 0
    any_conn_field = False

    for row in inv_rows:
        dev_fun = (row[8] if len(row) > 8 else "") or ""
        if "AP" not in str(dev_fun).upper():
            continue

        ap_total += 1

        if len(row) > 10:
            any_conn_field = True
            val = str(row[10]).strip().upper()
            if val in ("1", "TRUE", "YES", "Y", "CONNECTED", "ONLINE"):
                ap_connected += 1

    if ap_total == 0:
        return 0, None
    if not any_conn_field:
        return 0, None

    return ap_connected, ap_total - ap_connected


# ---------------------------------------------------------------------
# DISCOVERY – one global summary service
# ---------------------------------------------------------------------
def discover_xiq_summary(
    section_extreme_summary,
    section_extreme_device_inventory,
) -> DiscoveryResult:
    """
    Create exactly one summary service if the summary section exists.
    """
    if section_extreme_summary is not None:
        yield Service()


# ---------------------------------------------------------------------
# MAIN CHECK – build summary, perfdata, and detailed report
# ---------------------------------------------------------------------
def check_xiq_summary(
    section_extreme_summary,
    section_extreme_device_inventory,
) -> Iterable[CheckResult]:

    # No summary available
    if not section_extreme_summary:
        yield Result(
            state=State.UNKNOWN,
            summary="No XIQ summary data available",
        )
        return

    # Top-level counts from extreme_summary
    aps = _to_int(section_extreme_summary.get("access_points", 0))
    total_clients = _to_int(section_extreme_summary.get("total_clients", 0))
    c24 = _to_int(section_extreme_summary.get("clients_24", 0))
    c5  = _to_int(section_extreme_summary.get("clients_5", 0))
    c6  = _to_int(section_extreme_summary.get("clients_6", 0))

    # Optional connected/disconnected from agent summary (if present)
    aps_conn_sum = None
    aps_disc_sum = None
    for k_conn, k_disc in [
        ("aps_connected", "aps_disconnected"),
        ("access_points_connected", "access_points_disconnected"),
        ("ap_connected", "ap_disconnected"),
    ]:
        if k_conn in section_extreme_summary or k_disc in section_extreme_summary:
            aps_conn_sum = _to_int(section_extreme_summary.get(k_conn, 0))
            aps_disc_sum = _to_int(
                section_extreme_summary.get(
                    k_disc,
                    max(0, aps - aps_conn_sum),
                )
            )
            break

    # Inventory-based counts
    inv_counts = _count_by_function(section_extreme_device_inventory)
    inv_ap_total  = inv_counts.get("AP", 0)
    inv_sw_total  = inv_counts.get("SW", 0)
    inv_misc_total = inv_counts.get("MISC", 0)
    inv_total      = inv_counts.get("TOTAL", 0)

    inv_ap_conn, inv_ap_disc = _count_ap_connected(section_extreme_device_inventory)

    # ------------------------------------------------------------------
    # SUMMARY (short)
    # ------------------------------------------------------------------
    short = f"{aps} APs, {total_clients} Clients"
    yield Result(state=State.OK, summary=short)

    # Perfdata (for graphs and dashboards)
    yield Metric("xiq_aps_total", aps)
    yield Metric("xiq_clients_total", total_clients)
    yield Metric("xiq_clients_24", c24)
    yield Metric("xiq_clients_5",  c5)
    yield Metric("xiq_clients_6",  c6)

    # ------------------------------------------------------------------
    # DETAILED OUTPUT
    # ------------------------------------------------------------------
    lines: List[str] = []
    lines.append(short)

    if aps_conn_sum is not None and aps_disc_sum is not None:
        lines.append(
            f"APs in XIQ: {aps} (connected {aps_conn_sum} / disconnected {aps_disc_sum})"
        )
    elif inv_ap_disc is not None:
        lines.append(
            f"APs in XIQ: {inv_ap_total} (connected {inv_ap_conn} / disconnected {inv_ap_disc})"
        )
    else:
        lines.append(f"APs in XIQ: {inv_ap_total or aps}")

    if inv_sw_total or inv_misc_total or inv_total:
        lines.append(f"Switches in XIQ: {inv_sw_total}")
        lines.append(f"Misc devices in XIQ: {inv_misc_total}")
        lines.append(f"Total devices in XIQ: {inv_total}")

    yield Result(
        state=State.OK,
        notice="XIQ Summary details available in long output",
        details="\n".join(lines),
    )


# ---------------------------------------------------------------------
# REGISTRATION
# ---------------------------------------------------------------------
check_plugin_xiq_summary = CheckPlugin(
    name="xiq_summary",
    sections=["extreme_summary", "extreme_device_inventory"],
    service_name="XIQ Summary",
    discovery_function=discover_xiq_summary,
    check_function=check_xiq_summary,
)
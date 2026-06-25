#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : check_ap_status.py
#
# Description:
#   Checkmk check plugin for ExtremeCloudIQ AP status on piggyback hosts.
#   Summarizes connectivity, location, neighbors (LLDP/CDP), client counts,
#   and uptime. Emits perfdata for uptime and client totals per band.
# =============================================================================

from __future__ import annotations

from typing import Any, Iterable, List, Set, Tuple
import re

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    Metric,
)

from .common import _shorten_location_to_loc_leaf, _clean_text


# ---------------------------------------------------------------------
# STATE MAPPING – translate XIQ 'connected/state' into Checkmk states
# ---------------------------------------------------------------------
def _map_state(connected: bool, state_text: str) -> State:
    if connected:
        return State.OK
    st = (state_text or "").strip().lower()
    if st in {"provisioning", "configuring", "adopting"}:
        return State.WARN
    return State.CRIT


# ---------------------------------------------------------------------
# LLDP STRING CLEANUP – remove bracketed hints and reduce whitespace
# ---------------------------------------------------------------------
def _clean_lldp_short(lldp_str: str) -> str:
    if not lldp_str:
        return ""
    s = re.sub(r"\([^)]*\)", "", lldp_str).strip()
    s = _clean_text(s)
    s = re.sub(r"\s{2,}", " ", s)
    return s


# ---------------------------------------------------------------------
# FORMATTER – skip empty values
# ---------------------------------------------------------------------
def _fmt_kv(key: str, value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    return f"- {key}: {v}"


# ---------------------------------------------------------------------
# NEIGHBOR DETAILS
# ---------------------------------------------------------------------
def _neighbors_detailed_lines(nei: Any) -> List[str]:
    if not isinstance(nei, list):
        return []
    field_order = [
        ("local_port",       "Local Port"),
        ("remote_device",    "Remote Device"),
        ("management_ip",    "Remote Mgmt-IP"),
        ("remote_port",      "Remote Port"),
        ("port_description", "Port Desc"),
        ("mac_address",      "MAC"),
        ("device_id",        "Device-ID"),
    ]
    lines: List[str] = []
    for idx, entry in enumerate(nei, start=1):
        if not isinstance(entry, dict):
            continue
        lines.append(f"- Neighbor #{idx}:")
        for fkey, ftitle in field_order:
            val = entry.get(fkey)
            if val:
                lines.append(f"  - {ftitle}: {_clean_text(str(val))}")
    return lines


# ---------------------------------------------------------------------
# POLICY EXTRACTION
# ---------------------------------------------------------------------
def _extract_policies(radio_info: Any) -> List[str]:
    policies: Set[str] = set()
    if isinstance(radio_info, dict):
        for r in radio_info.get("_radios", []) or []:
            wlans = (r or {}).get("wlans") or []
            for w in wlans:
                p = (w or {}).get("policy")
                if p:
                    policies.add(str(p).strip())
    return sorted(policies)


# ---------------------------------------------------------------------
# UPTIME NORMALIZATION
# ---------------------------------------------------------------------
def _parse_uptime_to_seconds(raw: Any) -> int:
    if raw is None:
        return 0

    # Numeric (seconds or milliseconds)
    try:
        val = float(raw)
        if val <= 0:
            return 0
        if val > 315_360_000:  # >10 years -> ms
            return int(val / 1000)
        return int(val)
    except Exception:
        pass

    # Dict formats
    if isinstance(raw, dict):
        for key in ("uptime_seconds", "seconds", "value", "uptime"):
            if key in raw:
                return _parse_uptime_to_seconds(raw[key])
        if "uptime_ms" in raw:
            try:
                return int(float(raw["uptime_ms"]) / 1000)
            except Exception:
                return 0

    # String formats
    if isinstance(raw, str):
        s = raw.strip().lower()
        try:
            val = float(s)
            if val > 315_360_000:
                return int(val / 1000)
            return int(val)
        except Exception:
            pass

        total = 0
        num = ""
        for ch in s:
            if ch.isdigit():
                num += ch
                continue
            if num:
                v = int(num)
                if ch == "d":
                    total += v * 86400
                elif ch == "h":
                    total += v * 3600
                elif ch == "m":
                    total += v * 60
                elif ch == "s":
                    total += v
                num = ""
        if num:
            total += int(num)
        return total

    return 0


# ---------------------------------------------------------------------
# UPTIME FORMATTER
# ---------------------------------------------------------------------
def _fmt_dhms(sec: int) -> str:
    if sec <= 0:
        return "0s"
    d, r = divmod(sec, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s and not parts: parts.append(f"{s}s")
    return " ".join(parts) if parts else "0s"


# ---------------------------------------------------------------------
# CLIENT EXTRACTION
# ---------------------------------------------------------------------
def _extract_clients(sec: Any) -> Tuple[int, int, int, int]:
    if not isinstance(sec, dict):
        return 0, 0, 0, 0
    c24 = int(sec.get("2.4GHz", sec.get("clients_24", 0)) or 0)
    c5  = int(sec.get("5GHz",     sec.get("clients_5",  0)) or 0)
    c6  = int(sec.get("6GHz",     sec.get("clients_6",  0)) or 0)
    return c24 + c5 + c6, c24, c5, c6


# ---------------------------------------------------------------------
# DISCOVERY
# ---------------------------------------------------------------------
def discover_xiq_aps(
    section_extreme_ap_status,
    section_extreme_ap_neighbors,
    section_xiq_radio_information,
    section_extreme_ap_clients,
    section_extreme_ap_uptime,
) -> DiscoveryResult:
    if not section_extreme_ap_status:
        return
    ap_name = section_extreme_ap_status.get("ap_name")
    if ap_name:
        yield Service(item=ap_name)


# ---------------------------------------------------------------------
# CHECK
# ---------------------------------------------------------------------
def check_xiq_ap_status(
    item,
    params,
    section_extreme_ap_status,
    section_extreme_ap_neighbors,
    section_xiq_radio_information,
    section_extreme_ap_clients,
    section_extreme_ap_uptime,
) -> Iterable[CheckResult]:

    if not section_extreme_ap_status:
        yield Result(state=State.UNKNOWN, summary=f"{item}: no status data available")
        return

    s = section_extreme_ap_status

    connected  = bool(s.get("connected", False))
    model      = s.get("model", "")
    state_t    = s.get("state", "")
    sw         = s.get("sw_version", "")
    ip_addr    = s.get("ip", "")
    loc_full   = s.get("locations", "")
    lldp_short = _clean_lldp_short(s.get("lldp_cdp_short", ""))

    neighbors = section_extreme_ap_neighbors if isinstance(section_extreme_ap_neighbors, list) else []
    policies  = _extract_policies(section_xiq_radio_information)

    # Clients
    if section_extreme_ap_clients:
        total_clients, c24, c5, c6 = _extract_clients(section_extreme_ap_clients)
    else:
        total_clients, c24, c5, c6 = _extract_clients(s.get("clients") or {})

    # Uptime resolution
    ru = None
    if isinstance(section_extreme_ap_uptime, dict):
        ru = (
            section_extreme_ap_uptime.get("uptime_seconds")
            or section_extreme_ap_uptime.get("uptime")
            or section_extreme_ap_uptime.get("uptime_ms")
        )
    if ru is None:
        ru = (
            s.get("uptime_seconds")
            or s.get("uptime")
            or s.get("uptime_ms")
            or s.get("ap_uptime")
        )
    uptime_s = _parse_uptime_to_seconds(ru)

    loc_leaf = _shorten_location_to_loc_leaf(loc_full) if loc_full else ""

    # Build summary
    bits: List[str] = []
    if ip_addr: bits.append(f"IP: {ip_addr}")
    if loc_leaf: bits.append(f"Loc: {loc_leaf}")
    if lldp_short: bits.append(f"LLDP: {lldp_short}")
    bits.append(f"Clients: {total_clients}")
    if uptime_s > 0: bits.append(f"Uptime: {_fmt_dhms(uptime_s)}")

    suffix = " | " + " | ".join(bits)

    # Long output
    lines: List[str] = []
    lines.append("**Device**")
    lines.append(_fmt_kv("Name", item))
    if model: lines.append(_fmt_kv("Model", model))
    if sw:    lines.append(_fmt_kv("Firmware", sw))
    serial = s.get("serial", "")
    if serial: lines.append(_fmt_kv("Serial", serial))

    if loc_full and "/" in str(loc_full):
        lines.append(_fmt_kv("Location", loc_full))
        if loc_leaf:
            lines.append(_fmt_kv("Loc (short)", loc_leaf))
    elif loc_full:
        lines.append(_fmt_kv("Loc (short)", loc_full))

    if policies:
        lines.append(_fmt_kv("Policy", ", ".join(policies)))

    lines.append("------------------------------")
    lines.append("**Network**")
    if ip_addr:
        lines.append(_fmt_kv("IP", ip_addr))

    lines.append("------------------------------")
    lines.append("**Clients & Uptime**")
    lines.append(_fmt_kv("Clients total", str(total_clients)))
    lines.append(_fmt_kv("Clients 2.4GHz", str(c24)))
    lines.append(_fmt_kv("Clients 5GHz", str(c5)))
    lines.append(_fmt_kv("Clients 6GHz", str(c6)))
    lines.append(_fmt_kv("Uptime", _fmt_dhms(uptime_s)))

    if lldp_short or neighbors:
        lines.append("------------------------------")
        lines.append("**LLDP Info**")
        if lldp_short:
            lines.append(f"- {lldp_short}")
        det = _neighbors_detailed_lines(neighbors)
        lines.extend(det)

    yield Result(
        state=_map_state(connected, state_t),
        summary=f"{item}{suffix}",
        details="\n".join([x for x in lines if x]),
    )

    # Perfdata
    yield Metric("xiq_uptime_seconds", float(uptime_s))
    yield Metric("xiq_clients_total",  float(total_clients))
    yield Metric("xiq_clients_24",     float(c24))
    yield Metric("xiq_clients_5",      float(c5))
    yield Metric("xiq_clients_6",      float(c6))
    yield Metric("xiq_uptime_days",    int(uptime_s // 86400))


# ---------------------------------------------------------------------
# REGISTRATION – API v1 Ruleset compatible
# ---------------------------------------------------------------------
check_plugin_xiq_ap_status = CheckPlugin(
    name="xiq_ap_status",
    sections=[
        "extreme_ap_status",
        "extreme_ap_neighbors",
        "xiq_radio_information",
        "extreme_ap_clients",
        "extreme_ap_uptime",
    ],
    service_name="XIQ AP %s Status",
    discovery_function=discover_xiq_aps,
    check_function=check_xiq_ap_status,

    # Defaults match the v1 ruleset
    check_default_parameters={
        "min_uptime_warn": 6 * 3600,
        "min_uptime_crit": 1 * 3600,
        "client_warn": 100,
        "client_crit": 150,
        "treat_disconnected_as": 2,  # CRIT
        "enable_lldp_checks": False,
    },

    check_ruleset_name="xiq_ap_status_levels",
)
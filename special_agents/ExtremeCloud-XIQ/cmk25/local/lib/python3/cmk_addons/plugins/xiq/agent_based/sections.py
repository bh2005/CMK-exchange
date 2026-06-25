#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : sections.py
#
# Description:
#   AgentSection parsing logic for ExtremeCloudIQ in Checkmk.
#   Converts raw <<<<...>>>> data produced by agent_xiq into structured
#   Python dictionaries for all XIQ-related checks and inventory plugins.
#
#   Implements parsers for:
#       - Login                (extreme_cloud_iq_login)
#       - Summary              (extreme_summary)
#       - AP Status            (extreme_ap_status)
#       - AP Clients           (extreme_ap_clients)
#       - Rate Limits          (extreme_cloud_iq_rate_limits)
#       - Device Inventory     (extreme_device_inventory)
#       - Device Neighbors     (extreme_device_neighbors)
#       - Radio Information    (xiq_radio_information)
#       - Active Clients       (xiq_active_clients)
#
#   All parsers return None ? section skipped (Checkmk default behaviour).
# =============================================================================

from typing import Mapping, Any, Optional, List, Dict
import json
import time

from cmk.agent_based.v2 import (
    AgentSection,
    StringTable,
)

from .common import format_mac, _clean_text


# ---------------------------------------------------------------------
# LOGIN SECTION
# ---------------------------------------------------------------------
def parse_xiq_login(table: StringTable) -> Optional[Mapping[str, str]]:
    if not table:
        return None

    raw = " ".join(table[0]).strip()
    if not raw:
        return None

    result: Dict[str, str] = {"RAW": raw}

    def extract(tag: str) -> Optional[str]:
        pos = raw.find(tag)
        if pos == -1:
            return None
        pos += len(tag)
        ends = []
        for other in ("STATUS:", "CODE:", "RESPONSE:"):
            if other == tag:
                continue
            p = raw.find(other, pos)
            if p != -1:
                ends.append(p)
        end = min(ends) if ends else len(raw)
        return raw[pos:end].strip()

    status = extract("STATUS:")
    code = extract("CODE:")
    resp_pos = raw.find("RESPONSE:")
    response = raw[resp_pos + len("RESPONSE:"):].strip() if resp_pos != -1 else None

    if status:
        result["STATUS"] = status
    if code:
        result["CODE"] = code
    if response:
        result["RESPONSE"] = response

    return result


# ---------------------------------------------------------------------
# SUMMARY SECTION
# ---------------------------------------------------------------------
def parse_xiq_summary(table: StringTable) -> Optional[Mapping[str, Any]]:
    if not table:
        return None
    return {row[0]: row[1] for row in table if len(row) >= 2}


# ---------------------------------------------------------------------
# AP STATUS SECTION
# ---------------------------------------------------------------------
def parse_xiq_ap_status(table: StringTable) -> Optional[Mapping[str, Any]]:
    if not table:
        return None

    row = table[0]

    def s(i: int) -> str:
        return row[i] if len(row) > i else ""

    # Normalize uptime (seconds/ms/UNIX ts)
    up_raw = s(8).strip()
    uptime_seconds = 0
    uptime_ms = 0
    if up_raw:
        try:
            v = int(float(up_raw))
            now_s = int(time.time())
            now_ms = now_s * 1000

            # ms timestamp
            if v >= 10**11:
                uptime_ms = max(0, now_ms - v)
                uptime_seconds = int(uptime_ms / 1000)

            # s timestamp
            elif v >= 10**9:
                uptime_seconds = max(0, now_s - v)
                uptime_ms = uptime_seconds * 1000

            # direct seconds
            elif v > 10**7:
                uptime_seconds = v
                uptime_ms = v * 1000

            # direct ms uptime
            else:
                uptime_ms = v
                uptime_seconds = v // 1000

        except Exception:
            pass

    return {
        "ap_name": s(0),
        "serial": s(1),
        "mac": format_mac(s(2)),
        "ip": s(3),
        "model": s(4),
        "connected": s(5) == "1",
        "state": s(6),
        "sw_version": s(7),

        "uptime_seconds": uptime_seconds,
        "uptime_ms": uptime_ms,
        "uptime_s": uptime_seconds,

        "locations": s(9),
        "lldp_cdp_short": _clean_text(s(10)),
    }


# ---------------------------------------------------------------------
# LEGACY AP CLIENT COUNTS (2.4/5/6)
# ---------------------------------------------------------------------
def parse_xiq_ap_clients(table: StringTable) -> Optional[Mapping[str, int]]:
    if not table:
        return None
    row = table[0]

    def to(i: int) -> int:
        try:
            return int(row[i])
        except Exception:
            return 0

    return {"2.4GHz": to(0), "5GHz": to(1), "6GHz": to(2)}


# ---------------------------------------------------------------------
# RATE LIMITS
# ---------------------------------------------------------------------
def parse_xiq_rate_limits(table: StringTable) -> Optional[Mapping[str, Any]]:
    if not table:
        return None

    res: Dict[str, Any] = {}
    headers: List[str] = []
    in_headers = False

    for row in table:
        if len(row) != 2:
            continue

        key_raw, val_raw = row[0].strip(), (row[1] or "").strip()
        k = key_raw.lower()

        # Begin/end header block
        if k == "headers_begin":
            in_headers = True
            continue
        if k == "headers_end":
            in_headers = False
            continue

        # Copy raw header lines
        if in_headers and k == "header":
            if val_raw:
                headers.append(val_raw)
            continue

        # Standard fields
        if k == "state":
            res["state"] = val_raw or "OK"
            continue

        if k in ("limit", "ratelimit-limit"):
            main = val_raw.split(";", 1)[0]
            try:
                res["limit"] = int(main)
            except Exception:
                try:
                    res["limit"] = int(float(main))
                except Exception:
                    pass
            if ";w=" in val_raw:
                try:
                    res["window_s"] = int(val_raw.split(";w=", 1)[1])
                except Exception:
                    pass
            continue

        if k in ("remaining", "ratelimit-remaining"):
            try:
                res["remaining"] = int(val_raw)
            except Exception:
                try:
                    res["remaining"] = int(float(val_raw))
                except Exception:
                    pass
            continue

        if k in ("reset_in_seconds", "ratelimit-reset", "reset"):
            try:
                res["reset_in_seconds"] = int(val_raw)
            except Exception:
                try:
                    res["reset_in_seconds"] = int(float(val_raw))
                except Exception:
                    pass
            continue

        if k == "window_s":
            try:
                res["window_s"] = int(val_raw)
            except Exception:
                pass
            continue

    if headers:
        res["_headers"] = headers

    return res if res else None


# ---------------------------------------------------------------------
# DEVICE INVENTORY (table rows)
# ---------------------------------------------------------------------
def parse_xiq_device_inventory(table: StringTable) -> List[List[str]]:
    result: List[List[str]] = []
    for row in table:
        if len(row) >= 10:
            result.append(row)
    return result


# ---------------------------------------------------------------------
# DEVICE NEIGHBORS
# ---------------------------------------------------------------------
def parse_xiq_device_neighbors(table: StringTable) -> List[Mapping[str, str]]:
    result: List[Mapping[str, str]] = []
    for row in table:
        if len(row) < 9:
            continue
        result.append({
            "device_id":        _clean_text(row[0]),
            "hostname":         _clean_text(row[1]),
            "host_ip":          _clean_text(row[2]),
            "local_port":       _clean_text(row[3]),
            "management_ip":    _clean_text(row[4]),
            "remote_port":      _clean_text(row[5]),
            "port_description": _clean_text(row[6]),
            "mac_address":      format_mac(_clean_text(row[7])),
            "remote_device":    _clean_text(row[8]),
        })
    return result


# ---------------------------------------------------------------------
# RADIO INFORMATION (JSON, includes WLANs & policy info)
# ---------------------------------------------------------------------
def parse_xiq_radio_information(table: StringTable) -> Optional[Mapping[str, Any]]:
    if not table:
        return None

    raw = "".join("".join(row) for row in table).strip()
    if not raw.startswith("{"):
        return None

    try:
        data = json.loads(raw)
    except Exception:
        return None

    device_id = data.get("device_id")
    hostname = data.get("hostname") or ""
    radios_in = data.get("radios") or []
    ssid_freq_in = data.get("_ssid_freq") or {}

    out: Dict[str, Any] = {}
    out["_device_id"] = device_id
    out["_hostname"] = hostname
    out["_ssid_freq"] = ssid_freq_in
    out["radios"] = radios_in
    out["_radios"] = []

    freq_map: Dict[str, List[Dict[str, Any]]] = {"2.4GHz": [], "5GHz": [], "6GHz": []}

    for r in radios_in:
        freq = str(r.get("frequency", "")).strip()
        if freq not in ("2.4GHz", "5GHz", "6GHz"):
            mode = str(r.get("mode", "")).lower()
            if "5g" in mode:
                freq = "5GHz"
            elif "6g" in mode:
                freq = "6GHz"
            else:
                freq = "2.4GHz"

        wlans = r.get("wlans") or []
        wlans_out = []
        ssids = []
        bssids = []

        for w in wlans:
            ssid = str(w.get("ssid") or "").strip()
            policy = str(w.get("network_policy_name") or "").strip()
            bssid = format_mac(str(w.get("bssid") or ""))

            entry = {"ssid": ssid, "bssid": bssid, "policy": policy}
            wlans_out.append(entry)

            if ssid:
                ssids.append(ssid)
            if bssid:
                bssids.append(bssid)
            if ssid or bssid:
                freq_map[freq].append(entry)

        # Active clients per radio (rare in XIQ)
        client_count = 0
        for k in ("active_clients", "connected_clients", "client_count"):
            try:
                vc = int(r.get(k))
                if vc >= 0:
                    client_count = vc
                    break
            except Exception:
                pass

        out["_radios"].append({
            "device_id": device_id,
            "hostname": hostname,
            "radio_name": str(r.get("name") or ""),
            "radio_mac": format_mac(str(r.get("mac_address") or "")),
            "frequency": freq,
            "channel_number": int(r.get("channel_number") or 0),
            "channel_width": str(r.get("channel_width") or ""),
            "mode": str(r.get("mode") or ""),
            "power": int(r.get("power") or 0),
            "wlans": wlans_out,
            "ssid_list": ssids,
            "bssid_list": bssids,
            "client_count": client_count,
        })

    out.update(freq_map)
    return out


# ---------------------------------------------------------------------
# ACTIVE CLIENTS (JSON)
# ---------------------------------------------------------------------
def parse_xiq_active_clients(table: StringTable) -> Optional[Mapping[str, Any]]:
    """
    Active client parser for <<<<xiq_active_clients>>>>:
    Accepts 1) JSON object, 2) or JSON list (fallback).
    """
    if not table:
        return None

    raw = " ".join(cell for row in table for cell in row if cell is not None).strip()
    if not raw:
        return None

    try:
        data = json.loads(raw)
    except Exception:
        return None

    # preferred: dict
    if isinstance(data, dict):
        return data

    # fallback: list of clients
    if isinstance(data, list):
        return {
            "summary": {"total": len(data), "band": {}, "per_ssid": {}},
            "clients": data,
        }

    return None


# ---------------------------------------------------------------------
# SECTION REGISTRATION
# ---------------------------------------------------------------------
agent_section_xiq_login = AgentSection(
    name="extreme_cloud_iq_login",
    parse_function=parse_xiq_login,
)

agent_section_xiq_summary = AgentSection(
    name="extreme_summary",
    parse_function=parse_xiq_summary,
)

agent_section_xiq_ap_status = AgentSection(
    name="extreme_ap_status",
    parse_function=parse_xiq_ap_status,
)

agent_section_xiq_ap_clients = AgentSection(
    name="extreme_ap_clients",
    parse_function=parse_xiq_ap_clients,
)

agent_section_xiq_rate_limits = AgentSection(
    name="extreme_cloud_iq_rate_limits",
    parse_function=parse_xiq_rate_limits,
)

agent_section_xiq_device_inventory = AgentSection(
    name="extreme_device_inventory",
    parse_function=parse_xiq_device_inventory,
)

agent_section_xiq_device_neighbors = AgentSection(
    name="extreme_device_neighbors",
    parse_function=parse_xiq_device_neighbors,
)

agent_section_xiq_radios = AgentSection(
    name="xiq_radio_information",
    parse_function=parse_xiq_radio_information,
)

agent_section_xiq_ap_neighbors = AgentSection(
    name="extreme_ap_neighbors",
    parse_function=parse_xiq_device_neighbors,
)

agent_section_xiq_active_clients = AgentSection(
    name="xiq_active_clients",
    parse_function=parse_xiq_active_clients,
)
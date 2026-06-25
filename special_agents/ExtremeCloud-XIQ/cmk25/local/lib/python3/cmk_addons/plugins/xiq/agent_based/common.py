#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : common.py
#
# Description:
#   Shared utility functions for ExtremeCloudIQ agent-based plugins in Checkmk.
#   Includes normalization helpers for MAC addresses, text cleaning,
#   band selection, uptime calculations, integer safety, location parsing,
#   and connectivity flags.
# =============================================================================

from typing import Any
import time


# ---------------------------------------------------------------------
# TEXT CLEANING – remove LLDP/CDP decoration patterns
# ---------------------------------------------------------------------
def _clean_text(v: str) -> str:
    if not v:
        return ""
    return (
        str(v)
        .replace("(interface name)", "")
        .replace("(mac address)", "")
        .strip()
    )


# ---------------------------------------------------------------------
# MAC NORMALIZATION – robust fix-ups for API irregularities
# ---------------------------------------------------------------------
def format_mac(raw: str) -> str:
    """
    Normalize MAC addresses to AA:BB:CC:DD:EE:FF.

    Accepts formats:
        4C231A0403D5
        4c:23:1a:04:03:d5
        4C-23-1A-04-03-D5
        4C23.1A04.03D5
        (and broken 13+ hex variants from XIQ)

    Returns original string if not interpretable.
    """
    if not raw:
        return ""

    cleaned = "".join(c for c in raw.upper() if c in "0123456789ABCDEF")
    if len(cleaned) < 12:
        return raw
    cleaned = cleaned[:12]
    return ":".join(cleaned[i:i+2] for i in range(0, 12, 2))


# ---------------------------------------------------------------------
# BAND NORMALIZATION – map active client record to 2.4GHz/5GHz/6GHz
# ---------------------------------------------------------------------
def norm_band_from_active_client(c: Any) -> str:
    """
    Determine wireless band heuristically from active-client record.

    Priority:
      1) radio_type (1=2.4, 2=5, 4=6)
      2) mac_protocol text
      3) channel heuristics
    """
    try:
        rt = c.get("radio_type")
        if rt == 1:
            return "2.4GHz"
        if rt == 2:
            return "5GHz"
        if rt == 4:
            return "6GHz"
    except Exception:
        pass

    try:
        mp = str(c.get("mac_protocol") or "").lower()
        if "2.4" in mp:
            return "2.4GHz"
        if "5g" in mp:
            return "5GHz"
        if "6g" in mp:
            return "6GHz"
    except Exception:
        pass

    try:
        ch = int(c.get("channel") or 0)
        if 1 <= ch <= 13:
            return "2.4GHz"
        if 36 <= ch <= 165:
            return "5GHz"
    except Exception:
        pass

    # Default fallback
    return "2.4GHz"


# ---------------------------------------------------------------------
# UPTIME HELPERS – normalize seconds and format dhms
# ---------------------------------------------------------------------
def _fmt_uptime(seconds: int) -> str:
    s = max(0, int(seconds or 0))
    d, rem = divmod(s, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    return f"{d}d {h}h {m}m"


def _uptime_from_input(boot_ts_or_uptime) -> int:
    """
    Robustly normalize uptime:
    - milliseconds timestamp
    - seconds timestamp
    - pure uptime (ms or s)
    """
    try:
        v = int(boot_ts_or_uptime)
    except Exception:
        return 0

    if v <= 0:
        return 0

    now_s = time.time()

    # millisecond UNIX timestamp
    if v > 10_000_000_000:
        return max(0, int(now_s - (v / 1000)))

    # second UNIX timestamp
    if 1_000_000_000 <= v <= 4_000_000_000:
        return max(0, int(now_s - v))

    # direct seconds uptime
    if v < 5 * 365 * 24 * 3600:
        return v

    return v


# ---------------------------------------------------------------------
# SAFE INTEGER
# ---------------------------------------------------------------------
def _to_int_safe(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        if isinstance(v, (int, float)):
            return int(v)
        s = str(v).strip()
        if not s:
            return default
        digits = "".join(ch for ch in s if ch.isdigit() or ch == "-")
        if digits in ("", "-"):
            return default
        return int(digits)
    except Exception:
        return default


# ---------------------------------------------------------------------
# LOCATION HELPERS – compact leaf from location path
# ---------------------------------------------------------------------
def _shorten_location_to_loc_leaf(loc: str) -> str:
    if not loc:
        return ""
    parts = [p.strip() for p in loc.split("/") if p.strip()]
    for part in reversed(parts):
        up = part.upper()
        if "LOC" in up:
            idx = up.rfind("LOC")
            return up[idx:]
    return parts[-1] if parts else ""


def extract_location_leaf(loc: str) -> str:
    return _shorten_location_to_loc_leaf(loc)


# ---------------------------------------------------------------------
# CONNECTED NORMALIZATION – boolean from text/numbers
# ---------------------------------------------------------------------
def norm_connected(val: Any) -> bool:
    if val is None:
        return False
    v = str(val).strip().upper()
    if v in ("1", "TRUE", "YES", "Y", "CONNECTED", "ONLINE"):
        return True
    if v in ("0", "FALSE", "NO", "N", "DISCONNECTED", "OFFLINE"):
        return False
    try:
        return bool(int(v))
    except Exception:
        return False
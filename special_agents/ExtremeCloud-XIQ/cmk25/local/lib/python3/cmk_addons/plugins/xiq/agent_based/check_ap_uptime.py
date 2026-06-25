#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author : Bernd Holzhauer
# Date   : 2026-02-04
# File   : check_ap_uptime.py
#
# Description:
#   Checkmk check plugin for ExtremeCloudIQ AP uptime. Reads uptime values
#   from the section <<<<extreme_ap_status>>>> and normalizes them to seconds.
#   Supports various formats (seconds, ms, timestamps, or "Xd Yh Zm").
#   Emits summary, OK/WARN/CRIT depending on minimum uptime thresholds,
#   and provides a perfdata metric (xiq_uptime_seconds).
# =============================================================================

from __future__ import annotations

from typing import Mapping, Any, Iterable, Tuple
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
# DISCOVERY – create one uptime service per AP
# ---------------------------------------------------------------------
def discover_xiq_ap_uptime(section: Mapping[str, Any]) -> DiscoveryResult:
    if section:
        yield Service()


# ---------------------------------------------------------------------
# HELPER – normalize uptime to seconds (robust)
# ---------------------------------------------------------------------
def _parse_uptime_to_seconds(raw: Any) -> int:
    """Normalize uptime into seconds from many possible formats."""
    if raw is None:
        return 0

    # Numeric (seconds or milliseconds)
    try:
        val = float(raw)
        if val <= 0:
            return 0
        # >10 years in seconds → assume ms
        if val > 315_360_000:
            return int(val / 1000.0)
        return int(val)
    except Exception:
        pass

    # Dict-like forms
    if isinstance(raw, dict):
        for key in ("uptime_seconds", "seconds", "value", "uptime"):
            if key in raw:
                return _parse_uptime_to_seconds(raw[key])
        if "uptime_ms" in raw:
            try:
                return int(float(raw["uptime_ms"]) / 1000.0)
            except Exception:
                return 0

    # String formats, e.g. "1d 2h 3m 4s"
    if isinstance(raw, str):
        s = raw.strip().lower()
        if not s:
            return 0

        # numeric-like strings
        try:
            val = float(s)
            if val > 315_360_000:
                return int(val / 1000.0)
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
        # trailing number without unit → seconds
        if num:
            total += int(num)
        return total

    return 0


# ---------------------------------------------------------------------
# HELPER – human-readable formatting
# ---------------------------------------------------------------------
def _fmt_dhms(sec: int) -> str:
    if sec <= 0:
        return "0s"
    d, r = divmod(sec, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s and not parts:
        parts.append(f"{s}s")
    return " ".join(parts) if parts else "0s"


# ---------------------------------------------------------------------
# HELPER – threshold evaluation
# ---------------------------------------------------------------------
def _eval_levels(uptime: int, warn_min: int, crit_min: int) -> Tuple[State, str]:
    """Evaluate WARN/CRIT based on minimum uptime (fresh reboots = bad)."""
    if uptime <= 0:
        return State.UNKNOWN, "uptime data unavailable"
    if uptime < crit_min:
        return State.CRIT, f"uptime { _fmt_dhms(uptime) } < crit { _fmt_dhms(crit_min) }"
    if uptime < warn_min:
        return State.WARN, f"uptime { _fmt_dhms(uptime) } < warn { _fmt_dhms(warn_min) }"
    return State.OK, f"uptime { _fmt_dhms(uptime) }"


# ---------------------------------------------------------------------
# CHECK – evaluate uptime and thresholds, expose perfdata
# ---------------------------------------------------------------------
def check_xiq_ap_uptime(
    params: Mapping[str, Any],
    section: Mapping[str, Any],
) -> Iterable[CheckResult]:

    if not section:
        yield Result(state=State.UNKNOWN, summary="No uptime data available")
        return

    # Default thresholds: WARN < 6h, CRIT < 1h
    warn_min = int((params or {}).get("min_uptime_warn", 6 * 3600))
    crit_min = int((params or {}).get("min_uptime_crit", 1 * 3600))

    # Look for uptime fields in priority order
    raw = (
        section.get("uptime_seconds")
        or section.get("uptime")
        or section.get("uptime_ms")
        or section.get("ap_uptime")
    )

    uptime_s = _parse_uptime_to_seconds(raw)
    state, msg = _eval_levels(uptime_s, warn_min, crit_min)

    yield Result(state=state, summary=msg)

    # Perfdata metric
    yield Metric("xiq_uptime_seconds", float(uptime_s))


# ---------------------------------------------------------------------
# REGISTRATION
# ---------------------------------------------------------------------
check_plugin_xiq_ap_uptime = CheckPlugin(
    name="xiq_ap_uptime",
    sections=["extreme_ap_status"],
    service_name="XIQ AP Uptime",
    discovery_function=discover_xiq_ap_uptime,
    check_function=check_xiq_ap_uptime,
    check_default_parameters={
        "min_uptime_warn": 6 * 3600,  # 6 hours
        "min_uptime_crit": 1 * 3600,  # 1 hour
    },
    check_ruleset_name="xiq_ap_uptime_levels",
)
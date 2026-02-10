#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : xiq_ap_clients.py
#
# Description:
#   Checkmk check plugin for ExtremeCloudIQ AP client totals per band.
#   Consumes the agent section "extreme_ap_clients" which provides a
#   dictionary with keys "2.4GHz", "5GHz", and "6GHz" (or legacy
#   fallback keys "clients_24"/"clients_5"/"clients_6").
#   Emits perfdata for total and per-band client counts.
# =============================================================================
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
# DISCOVERY – single service for AP client summary
# ---------------------------------------------------------------------
def discover_xiq_ap_clients(section: Mapping[str, Any]) -> DiscoveryResult:
    if section:
        yield Service()

# ---------------------------------------------------------------------
# CHECK – evaluate totals and optional thresholds
# ---------------------------------------------------------------------
def _get_levels(params: Mapping[str, Any]) -> Tuple[int | None, int | None]:
    """Return (warn, crit) from parameters."""
    # Check if global_levels exists and has the warn/crit keys
    gl = params.get("global_levels")
    if gl and isinstance(gl, dict):
        warn = gl.get("warn")
        crit = gl.get("crit")
        return warn, crit
    return None, None

def check_xiq_ap_clients(
    params: Mapping[str, Any],
    section: Mapping[str, Any],
) -> Iterable[CheckResult]:
    c24 = int(section.get("2.4GHz", section.get("clients_24", 0)) or 0)
    c5  = int(section.get("5GHz",   section.get("clients_5",  0)) or 0)
    c6  = int(section.get("6GHz",   section.get("clients_6",  0)) or 0)
    
    total = c24 + c5 + c6
    
    warn, crit = _get_levels(params)
    
    state = State.OK
    if crit is not None and total >= crit:
        state = State.CRIT
    elif warn is not None and total >= warn:
        state = State.WARN
    
    # Summary
    yield Result(
        state=state,
        summary=f"AP clients: {total} (2.4GHz {c24}, 5GHz {c5}, 6GHz {c6})",
    )
    
    # Perfdata
    yield Metric("xiq_ap_clients_total", float(total))
    yield Metric("xiq_ap_clients_24",    float(c24))
    yield Metric("xiq_ap_clients_5",     float(c5))
    yield Metric("xiq_ap_clients_6",     float(c6))

# ---------------------------------------------------------------------
# REGISTRATION
# ---------------------------------------------------------------------
check_plugin_xiq_ap_clients = CheckPlugin(
    name="xiq_ap_clients",
    sections=["extreme_ap_clients"],
    service_name="XIQ AP Clients",
    discovery_function=discover_xiq_ap_clients,
    check_function=check_xiq_ap_clients,
    check_default_parameters={},  # Leeres Dict als Default
    check_ruleset_name="xiq_ap_clients_levels",
)
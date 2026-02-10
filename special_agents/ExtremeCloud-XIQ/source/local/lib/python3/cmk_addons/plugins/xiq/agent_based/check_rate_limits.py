#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : check_rate_limits.py
#
# Description:
#   Checkmk check plugin for ExtremeCloudIQ API rate-limit usage.
#   Evaluates remaining quota vs limit, returns WARN/CRIT based on ratios,
#   and exposes perfdata for remaining and total API quota. Compatible
#   with the section <<<<extreme_cloud_iq_rate_limits>>>> provided by
#   the Special Agent.
# =============================================================================

from typing import Mapping, Any, Iterable
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
# DISCOVERY – create a global service if rate-limit data exists
# ---------------------------------------------------------------------
def discover_rate_limits(section: Mapping[str, Any]) -> DiscoveryResult:
    if section:
        yield Service()


# ---------------------------------------------------------------------
# CHECK – evaluate remaining quota, thresholds, and details
# ---------------------------------------------------------------------
def check_xiq_rate_limits(section: Mapping[str, Any]) -> Iterable[CheckResult]:
    if not section:
        yield Result(state=State.UNKNOWN, summary="No API rate limit data available")
        return

    state_flag = (section.get("state") or "").upper()

    # Explicit state handling
    if state_flag == "UNLIMITED":
        yield Result(state=State.OK, summary="API reports no rate limits")
        return

    if state_flag == "NO_RESPONSE":
        yield Result(state=State.CRIT, summary="No HTTP response from XIQ API")
        return

    # Extract numeric fields
    limit    = int(section.get("limit") or 0)
    rem      = int(section.get("remaining") or 0)
    reset    = int(section.get("reset_in_seconds") or 0)
    window_s = int(section.get("window_s") or 0)
    http_sc  = section.get("status_code")

    # Default thresholds:
    #   WARN <10%
    #   CRIT <5%
    state = State.OK
    try:
        if limit > 0:
            ratio = rem / float(limit)
            if ratio < 0.05:
                state = State.CRIT
            elif ratio < 0.10:
                state = State.WARN
    except Exception:
        pass

    # Summary
    summary = f"Remaining {rem}/{limit}, window {window_s}s"
    yield Result(state=state, summary=summary)

    # Long output (optional details)
    details_lines = []

    if http_sc is not None:
        details_lines.append(f"- HTTP status code: {http_sc}")
    if reset > 0:
        details_lines.append(f"- Reset in: {reset}s")
    if window_s > 0:
        details_lines.append(f"- Rate-limit window: {window_s}s")

    if details_lines:
        yield Result(
            state=state,
            notice="Rate-limit details available",
            details="\n".join(details_lines),
        )

    # Metrics
    yield Metric("xiq_api_remaining", rem)
    yield Metric("xiq_api_limit", limit)


# ---------------------------------------------------------------------
# REGISTRATION
# ---------------------------------------------------------------------
check_plugin_xiq_rate_limits = CheckPlugin(
    name="xiq_rate_limits",
    sections=["extreme_cloud_iq_rate_limits"],
    service_name="XIQ API Rate Limits",
    discovery_function=discover_rate_limits,
    check_function=check_xiq_rate_limits,
)

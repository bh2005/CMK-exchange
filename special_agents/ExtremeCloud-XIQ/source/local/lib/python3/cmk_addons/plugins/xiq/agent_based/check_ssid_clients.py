#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Checkmk Agent-based API v2 – XIQ SSID Clients (per SSID on AP piggyback host)
#
# Provides:
#   - One service per SSID visible on the AP piggyback host
#   - Band-distributed client counts (2.4 / 5 / 6 GHz) from <<<xiq_radio_information>>>
#   - Optional augmentation with AP status (hostname) for nicer summaries
#   - Threshold evaluation: total clients per SSID (warn/crit)
#   - Perfdata: total + per-band client metrics (Graphing API v1 compatible)
#
# Compatible with Checkmk 2.4 (new Check API / agent_based.v2)
# =============================================================================

from typing import Mapping, Any, Iterable, Optional, Set
from cmk.agent_based.v2 import (
    CheckPlugin,
    DiscoveryResult,
    CheckResult,
    Result,
    Service,
    State,
    Metric,
)

# If you have a helper to pretty-print MACs, import it here.
# Otherwise, you can replace 'format_mac' with a no-op or remove it.
try:
    from cmk_addons.plugins.xiq.agent_based.common import format_mac
except Exception:
    def format_mac(value: str) -> str:
        # Fallback: return input unmodified if helper is not available.
        return value or ""


# -----------------------------------------------------------------------------
# DISCOVERY – one service per SSID visible on the AP
# -----------------------------------------------------------------------------
def discover_xiq_ssids(
    section_xiq_radio_information: Optional[Mapping[str, Any]],
    section_extreme_ap_status: Optional[Mapping[str, Any]],
    section_extreme_ap_clients: Optional[Mapping[str, int]],
) -> DiscoveryResult:
    """Discover one service per SSID that is present on this AP piggyback host.

    Sources:
      - Summary map _ssid_freq from xiq_radio_information (includes active SSIDs)
      - Per-radio 'wlans' (includes SSIDs with zero clients)
    """
    if not section_xiq_radio_information:
        return

    ssids: Set[str] = set()

    # 1) SSIDs from summarized active-client frequency map
    ssid_freq_map = section_xiq_radio_information.get("_ssid_freq") or {}
    for ssid in ssid_freq_map.keys():
        if ssid:
            ssids.add(str(ssid))

    # 2) SSIDs from per-radio WLANs (to also include SSIDs with zero clients)
    radios = (
        section_xiq_radio_information.get("radios")
        or section_xiq_radio_information.get("_radios")
        or []
    )
    for r in radios:
        for wlan in r.get("wlans", []):
            name = (wlan.get("ssid") or "").strip()
            if name:
                ssids.add(name)

    # Emit one service per SSID (sorted for stability)
    for ssid in sorted(ssids):
        yield Service(item=ssid)


# -----------------------------------------------------------------------------
# CHECK – compute SSID client totals, apply thresholds, expose metrics
# -----------------------------------------------------------------------------
def check_xiq_ssid_clients(
    item: str,
    params: Mapping[str, Any],
    section_xiq_radio_information: Optional[Mapping[str, Any]],
    section_extreme_ap_status: Optional[Mapping[str, Any]],
    section_extreme_ap_clients: Optional[Mapping[str, int]],
) -> Iterable[CheckResult]:
    """Check logic for a single SSID.

    Thresholds:
      - params["global_levels"] may be a dict {"warn": int, "crit": int}
        or (for backward compatibility) a 2-tuple/list (warn, crit).
    """
    if not section_xiq_radio_information:
        return

    ssid = item

    # Optional AP name (improves readability in the summary)
    ap_name = ""
    if section_extreme_ap_status:
        ap_name = (
            section_extreme_ap_status.get("ap_name", "")
            or section_extreme_ap_status.get("hostname", "")
            or ""
        ).strip()

    # -------------------------------------------------------------------------
    # Client counts per band from summary map (_ssid_freq)
    # -------------------------------------------------------------------------
    ssid_freq_map = section_xiq_radio_information.get("_ssid_freq") or {}
    raw_counts = ssid_freq_map.get(ssid, {})
    counts = {
        "2.4GHz": int(raw_counts.get("2.4GHz", 0) or 0),
        "5GHz":  int(raw_counts.get("5GHz",  0) or 0),
        "6GHz":  int(raw_counts.get("6GHz",  0) or 0),
    }
    total = counts["2.4GHz"] + counts["5GHz"] + counts["6GHz"]

    # -------------------------------------------------------------------------
    # Threshold evaluation
    # -------------------------------------------------------------------------
    warn = crit = None
    gl = (params or {}).get("global_levels")

    if isinstance(gl, dict):
        warn = gl.get("warn")
        crit = gl.get("crit")
    elif isinstance(gl, (list, tuple)) and len(gl) >= 2:
        warn, crit = gl[0], gl[1]

    state = State.OK
    if crit is not None and total >= int(crit):
        state = State.CRIT
    elif warn is not None and total >= int(warn):
        state = State.WARN

    # Summary
    prefix = f"AP {ap_name}: " if ap_name else ""
    summary = (
        f"{prefix}SSID {ssid}: {total} Clients "
        f"(2.4GHz {counts['2.4GHz']}, 5GHz {counts['5GHz']}, 6GHz {counts['6GHz']})"
    )
    yield Result(state=state, summary=summary)

    # -------------------------------------------------------------------------
    # Details: collect BSSIDs and policy per band from per-radio 'wlans'
    # -------------------------------------------------------------------------
    radios = (
        section_xiq_radio_information.get("radios")
        or section_xiq_radio_information.get("_radios")
        or []
    )

    bssids = {"2.4GHz": "", "5GHz": "", "6GHz": ""}
    policy = ""

    for r in radios:
        freq = r.get("frequency", "")
        if freq not in bssids:
            continue

        for wlan in r.get("wlans", []):
            if (wlan.get("ssid") or "").strip() == ssid:
                bssids[freq] = format_mac(wlan.get("bssid", ""))
                # Use the first policy we find for this SSID
                if not policy:
                    policy = (
                        wlan.get("network_policy_name", "")
                        or wlan.get("policy", "")
                        or ""
                    )

    details = (
        "**Radios**\n"
        f"- 2.4 GHz : {bssids['2.4GHz'] or '-'}\n"
        f"- 5   GHz : {bssids['5GHz'] or '-'}\n"
        f"- 6   GHz : {bssids['6GHz'] or '-'}\n"
        "\n**Policy**\n"
        f"- Network Policy: {policy or '-'}"
    )
    yield Result(state=State.OK, notice=details)

    # -------------------------------------------------------------------------
    # Metrics (Graphing API v1 compatible)
    #   - xiq_ssid_clients_total  (suffix "Clients" can be defined in metrics.py)
    #   - xiq_ssid_clients_24 / _5 / _6
    # -------------------------------------------------------------------------
    yield Metric("xiq_ssid_clients_total", float(total))
    yield Metric("xiq_ssid_clients_24",   float(counts["2.4GHz"]))
    yield Metric("xiq_ssid_clients_5",    float(counts["5GHz"]))
    yield Metric("xiq_ssid_clients_6",    float(counts["6GHz"]))


# -----------------------------------------------------------------------------
# REGISTRATION – bind to ruleset via check_ruleset_name="xiq_ssid_clients"
# -----------------------------------------------------------------------------
check_plugin_xiq_ssid_clients = CheckPlugin(
    name="xiq_ssid_clients",
    service_name="XIQ SSID %s",
    sections=[
        "xiq_radio_information",  # provides _ssid_freq and per-radio 'wlans'
        "extreme_ap_status",      # optional: AP hostname
        "extreme_ap_clients",     # optional: not used directly, but kept for future extension
    ],
    discovery_function=discover_xiq_ssids,
    check_function=check_xiq_ssid_clients,
    # Provide sane defaults if no rule applies:
    check_default_parameters={"global_levels": {"warn": 100, "crit": 150}},
    # Must match the ruleset "name" in your ruleset file:
    check_ruleset_name="xiq_ssid_clients",
)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Checkmk Agent-based API v2 – XIQ Radios (per band)
#
# Provides:
#   - Client counts per band (2.4/5/6 GHz)
#   - Channel and TX power aggregation
#   - Thresholds: clients (>= warn/crit) and power (<= warn/crit)
#   - Perfdata only for clients and power
#
# Compatible with Checkmk 2.4
# =============================================================================

from typing import Mapping, Any, Iterable
from cmk.agent_based.v2 import (
    CheckPlugin,
    DiscoveryResult,
    CheckResult,
    Result,
    Service,
    Metric,
    State,
)

# ---------------------------------------------------------------------
# DISCOVERY – one service per detected band
# ---------------------------------------------------------------------
def discover_xiq_radios(section: Mapping[str, Any]) -> DiscoveryResult:
    if not section:
        return

    radios = section.get("radios") or section.get("_radios") or []
    bands = set()

    for r in radios:
        freq = r.get("frequency")
        if freq in ("2.4GHz", "5GHz", "6GHz"):
            bands.add(freq)

    ordering = ("2.4GHz", "5GHz", "6GHz")
    for band in sorted(bands, key=lambda b: ordering.index(b)):
        yield Service(item=band)


# ---------------------------------------------------------------------
# CHECK – apply thresholds & provide metrics
# ---------------------------------------------------------------------
def check_xiq_radios(item: str,
                     params: Mapping[str, Any],
                     section: Mapping[str, Any]) -> Iterable[CheckResult]:

    if not section:
        yield Result(state=State.UNKNOWN, summary="No radio data")
        return

    # Thresholds
    warn_clients = int(params.get("warn_clients", 100))
    crit_clients = int(params.get("crit_clients", 150))
    warn_power   = int(params.get("warn_power", 10))
    crit_power   = int(params.get("crit_power", 5))

    ssid_freq = section.get("_ssid_freq", {})
    radios = section.get("radios") or section.get("_radios") or []

    # -----------------------------------------------------------------
    # Clients per band
    # -----------------------------------------------------------------
    total_clients = 0
    for _ssid, band_counts in ssid_freq.items():
        if isinstance(band_counts, dict):
            try:
                total_clients += int(band_counts.get(item, 0))
            except Exception:
                pass

    # -----------------------------------------------------------------
    # Channels + TX Power collection (ignore zeros / disabled radios)
    # -----------------------------------------------------------------
    channels_raw = []
    powers_raw = []

    for r in radios:
        if r.get("frequency") == item:
            ch = r.get("channel_number")
            if ch not in (None, "", "null"):
                try:
                    channels_raw.append(int(ch))
                except Exception:
                    pass

            pw = r.get("power")
            if pw not in (None, "", "null"):
                try:
                    powers_raw.append(int(pw))
                except Exception:
                    pass

    channels = [c for c in channels_raw if c > 0]
    powers   = [p for p in powers_raw if p > 0]

    channels_str = ", ".join(str(c) for c in sorted(set(channels))) if channels else "-"
    powers_str   = ", ".join(str(p) for p in sorted(set(powers)))   if powers   else "-"

    # -----------------------------------------------------------------
    # STATE HANDLING (Clients high → bad, Power low → bad)
    # -----------------------------------------------------------------
    state = State.OK
    problems = []

    if total_clients >= crit_clients:
        state = State.CRIT
        problems.append(f"clients={total_clients} ≥ crit({crit_clients})")
    elif total_clients >= warn_clients:
        state = State.WARN
        problems.append(f"clients={total_clients} ≥ warn({warn_clients})")

    if powers:
        min_power = min(powers)
        if min_power <= crit_power:
            state = State.CRIT
            problems.append(f"power={min_power} dBm ≤ crit({crit_power})")
        elif min_power <= warn_power and state != State.CRIT:
            state = State.WARN
            problems.append(f"power={min_power} dBm ≤ warn({warn_power})")

    suffix = f" ({'; '.join(problems)})" if problems else ""

    summary = (
        f"Radio {item}: {total_clients} clients • "
        f"Channels: {channels_str} • "
        f"Power: {powers_str} dBm{suffix}"
    )

    yield Result(state=state, summary=summary)

    # -----------------------------------------------------------------
    # PERF-DATA (ONLY CLIENTS + POWER)
    # -----------------------------------------------------------------
    if item == "2.4GHz":
        yield Metric("xiq_radio_clients_24", float(total_clients))
    elif item == "5GHz":
        yield Metric("xiq_radio_clients_5", float(total_clients))
    elif item == "6GHz":
        yield Metric("xiq_radio_clients_6", float(total_clients))

    yield Metric("xiq_radio_clients_total", float(total_clients))

    if powers:
        avg_power = sum(powers) / len(powers)
        min_power = min(powers)
        yield Metric("xiq_radio_power_avg_dbm", float(avg_power))
        yield Metric("xiq_radio_power_min_dbm", float(min_power))


# ---------------------------------------------------------------------
# REGISTRATION
# ---------------------------------------------------------------------
check_plugin_xiq_radios = CheckPlugin(
    name="xiq_radios",
    service_name="XIQ Radio %s",
    sections=["xiq_radio_information"],
    discovery_function=discover_xiq_radios,
    check_function=check_xiq_radios,
    check_default_parameters={
        "warn_clients": 100,
        "crit_clients": 150,
        "warn_power": 10,
        "crit_power": 5,
    },
    check_ruleset_name="xiq_radio_levels",
)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Checkmk 2.4 Agent-based Check: Tank-Spion LX-NET
Item = Tank-Nummer, Schwellwerte pro Tank konfigurierbar
"""

from typing import Any, Mapping
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    Metric,
    render,
)


def discover_tank_spion(section: Mapping[int, tuple[float, float]]) -> DiscoveryResult:
    """Erzeugt einen Service pro Tank-Nummer."""
    for tank_nr in sorted(section):
        yield Service(item=str(tank_nr))


def check_tank_spion(item: str, params: Mapping[str, Any], section: Mapping[int, tuple[float, float]]) -> CheckResult:
    try:
        tank_nr = int(item)
    except ValueError:
        yield Result(state=State.UNKNOWN, summary=f"Ungültige Tank-Nummer: {item}")
        return

    if tank_nr not in section:
        yield Result(state=State.UNKNOWN, summary=f"Tank {tank_nr} nicht in Agent-Daten gefunden")
        return

    bestand_l, tanksize_l = section[tank_nr]

    if tanksize_l <= 0:
        yield Result(state=State.CRIT, summary=f"Tank {tank_nr}: Ungültige Tankgröße")
        return

    percent = round((bestand_l / tanksize_l) * 100, 1)

    # Schwellwerte pro Tank aus Regel
    warn_perc = params.get("warn_perc", 40.0)
    crit_perc = params.get("crit_perc", 25.0)

    # Status
    state = State.OK
    if percent <= crit_perc:
        state = State.CRIT
    elif percent <= warn_perc:
        state = State.WARN

    # Umrechnung (optional)
    umkg = params.get("umrechnung_kg", 0.0)
    bestand_kg = bestand_l * umkg if umkg > 0 else None
    tanksize_kg = tanksize_l * umkg if umkg > 0 else None

    umrechnung_text = ""
    if bestand_kg is not None:
        umrechnung_text = f" ({bestand_kg:.2f} kg / {tanksize_kg:.2f} kg)"

    yield Result(
        state=state,
        summary=f"Tank {tank_nr}: {percent}% – {bestand_l:.0f} L von {tanksize_l:.0f} L{umrechnung_text}",
        details=f"Warn bei ≤{warn_perc}%, Crit bei ≤{crit_perc}%"
    )

    # Perfdata
    yield Metric("fuellstand_l", bestand_l, boundaries=(0, tanksize_l))
    yield Metric("fuellstand_perc", percent, levels=(crit_perc, warn_perc), boundaries=(0, 100))
    yield Metric("tanksize_l", tanksize_l)

    if umkg > 0:
        yield Metric("fuellstand_kg", bestand_kg, boundaries=(0, tanksize_kg))
        yield Metric("tanksize_kg", tanksize_kg)


check_plugin_tank_spion = CheckPlugin(
    name="tank_spion",
    service_name="Tank Füllstand %s",
    discovery_function=discover_tank_spion,
    check_function=check_tank_spion,
    check_default_parameters={},
    check_ruleset_name="tank_spion",  # Regeln pro Item
)
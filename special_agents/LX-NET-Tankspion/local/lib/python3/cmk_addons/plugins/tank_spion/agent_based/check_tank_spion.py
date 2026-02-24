#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# CheckMK 2.4 – Agent-based Check: Tank-Spion LX-NET
# ====================================================
# Item = Tank-Nummer, Schwellwerte pro Tank konfigurierbar
#
# Erwartet Agent-Output im Format (eine Zeile pro Tank):
#   <<<tank_spion>>>
#   1 2345 3480
#   2 890 2000
#
# Felder: <tank_nr> <bestand_liter> <tankgroesse_liter>
#
# Installation:
#   local/lib/python3/cmk_addons/plugins/tank_spion/agent_based/tank_spion.py

from __future__ import annotations

from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)


# ── Datentyp ──────────────────────────────────────────────────────────────────

# section: {tank_nr: (bestand_l, tanksize_l)}
TankSection = dict[int, tuple[float, float]]


# ── Parse ─────────────────────────────────────────────────────────────────────

def parse_tank_spion(string_table: StringTable) -> TankSection:
    """
    Parst den Agent-Output.

    Erwartet pro Zeile: <tank_nr> <bestand_l> <tanksize_l>
    Zeilen mit Fehlern werden uebersprungen.
    """
    section: TankSection = {}
    for row in string_table:
        if len(row) < 3:
            continue
        try:
            tank_nr   = int(row[0])
            bestand   = float(row[1])
            tanksize  = float(row[2])
        except ValueError:
            continue
        section[tank_nr] = (bestand, tanksize)
    return section


# AgentSection MUSS definiert sein — ohne sie liefert CMK dem CheckPlugin
# immer None als section und Discovery/Check laufen niemals.
agent_section_tank_spion = AgentSection(
    name="tank_spion",
    parse_function=parse_tank_spion,
)


# ── Discovery ─────────────────────────────────────────────────────────────────

def discover_tank_spion(section: TankSection) -> DiscoveryResult:
    """Erzeugt einen Service pro Tank-Nummer."""
    for tank_nr in sorted(section):
        yield Service(item=str(tank_nr))


# ── Check ─────────────────────────────────────────────────────────────────────

def check_tank_spion(
    item: str,
    params: dict[str, Any],
    section: TankSection,
) -> CheckResult:
    try:
        tank_nr = int(item)
    except ValueError:
        yield Result(state=State.UNKNOWN, summary=f"Ungueltige Tank-Nummer: {item}")
        return

    if tank_nr not in section:
        yield Result(state=State.UNKNOWN, summary=f"Tank {tank_nr} nicht in Agent-Daten gefunden")
        return

    bestand_l, tanksize_l = section[tank_nr]

    if tanksize_l <= 0:
        yield Result(state=State.CRIT, summary=f"Tank {tank_nr}: Ungueltige Tankgröße ({tanksize_l})")
        return

    percent = round((bestand_l / tanksize_l) * 100, 1)

    # Schwellwerte aus Regel (Fuellstand-UNTERSCHREITUNG = Problem)
    warn_perc = params.get("warn_perc", 40.0)
    crit_perc = params.get("crit_perc", 25.0)

    if percent <= crit_perc:
        state = State.CRIT
    elif percent <= warn_perc:
        state = State.WARN
    else:
        state = State.OK

    # Optionale Liter→kg-Umrechnung
    umkg = params.get("umrechnung_kg", 0.0)
    umrechnung_text = ""
    if umkg > 0:
        bestand_kg  = bestand_l  * umkg
        tanksize_kg = tanksize_l * umkg
        umrechnung_text = f" ({bestand_kg:.1f} kg von {tanksize_kg:.1f} kg)"

    yield Result(
        state=state,
        summary=f"{percent}% – {bestand_l:.0f} L von {tanksize_l:.0f} L{umrechnung_text}",
        details=f"Warning ≤ {warn_perc}%,  Critical ≤ {crit_perc}%",
    )

    # ── Performance-Daten ─────────────────────────────────────────────────────
    # Metric levels werden hier NICHT gesetzt, da "niedrig = schlecht"
    # (CMK-Konvention: levels sind obere Schwellen).
    # Der Status wird korrekt im Result gesetzt.
    yield Metric("fuellstand_l",    bestand_l,   boundaries=(0.0, tanksize_l))
    yield Metric("fuellstand_perc", percent,      boundaries=(0.0, 100.0))
    yield Metric("tanksize_l",      tanksize_l)

    if umkg > 0:
        bestand_kg  = bestand_l  * umkg
        tanksize_kg = tanksize_l * umkg
        yield Metric("fuellstand_kg", bestand_kg,  boundaries=(0.0, tanksize_kg))
        yield Metric("tanksize_kg",   tanksize_kg)


# ── CheckPlugin ───────────────────────────────────────────────────────────────

check_plugin_tank_spion = CheckPlugin(
    name="tank_spion",
    service_name="Tank Fuellstand %s",
    discovery_function=discover_tank_spion,
    check_function=check_tank_spion,
    check_default_parameters={
        "warn_perc": 40.0,
        "crit_perc": 25.0,
        "umrechnung_kg": 0.0,
    },
    check_ruleset_name="tank_spion",   # muss mit rule_spec name= uebereinstimmen
)

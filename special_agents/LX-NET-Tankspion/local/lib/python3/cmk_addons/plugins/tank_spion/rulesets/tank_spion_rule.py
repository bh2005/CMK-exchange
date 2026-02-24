#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tank-Spion LX-NET – Item-spezifische Schwellwerte & Umrechnung
Checkmk 2.4 – Rulesets v2
"""

from cmk.rulesets.v2 import (
    HostRuleset,
    RulesetType,
)
from cmk.rulesets.v2.parameters import (
    Dict,
    Float,
    String,
    DefaultValue,
)
from cmk.rulesets.v2 import Help, Title


def _parameter_form_tank_spion():
    return Dict(
        title="Tank-Spion LX-NET Parameter (pro Tank)",
        help_text="Individuelle Schwellwerte und Umrechnung pro Tank-Nummer (Item).",
        elements={
            "warn_perc": Float(
                title=Title("Warning bei Restfüllstand ≤"),
                unit="%",
                default_value=40.0,
            ),
            "crit_perc": Float(
                title=Title("Critical bei Restfüllstand ≤"),
                unit="%",
                default_value=25.0,
            ),
            "umrechnung_kg": Float(
                title=Title("Umrechnungsfaktor Liter → kg"),
                help_text="0 = keine Umrechnung (nur Liter). "
                          "Beispiel: Diesel ≈ 0.82 kg/L",
                default_value=0.0,
            ),
        },
    )


ruleset_tank_spion = HostRuleset(
    name="tank_spion",
    topic="Applications",
    parameter_form=_parameter_form_tank_spion,
    ruleset_type=RulesetType.ITEM,  # ← Wichtig: Item-spezifisch!
)
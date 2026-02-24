#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# CheckMK 2.4 – Ruleset: Tank-Spion Special Agent (Datasource)
# =============================================================
#
# Aktiviert den Special Agent für Hosts die ein Tank-Spion LX-NET sind.
# Erscheint im GUI unter:
#   Setup → Agents → VM, cloud, container → Tank-Spion LX-NET
#   (oder über Setup-Suche: "Tank-Spion")
#
# ZWEI Rulesets in dieser Datei:
#   1. rule_spec_tank_spion_datasource  → aktiviert den Special Agent
#   2. rule_spec_tank_spion             → Schwellwerte pro Tank (Item)
#
# Installation:
#   local/lib/python3/cmk_addons/plugins/tank_spion/rulesets/tank_spion_rule.py

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    validators,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    HostCondition,
    SpecialAgent,
    Topic,
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Special Agent Datasource Rule
#    Aktiviert den Special Agent für den Host.
#    Keine Parameter noetig — IP kommt direkt vom CMK-Host.
# ══════════════════════════════════════════════════════════════════════════════

rule_spec_tank_spion_datasource = SpecialAgent(
    name="tank_spion",
    title=Title("Tank-Spion LX-NET (Oeltank-Fuellstand)"),
    topic=Topic.APPLICATIONS,
    help_text=Help(
        "Aktiviert den Special Agent für TECSON Tank-Spion LX-NET Geräte. "
        "Der Agent ruft das Webinterface des Geraets direkt per HTTP ab. "
        "Die IP-Adresse des Hosts wird als Zieladresse verwendet. "
        "Schwellwerte werden pro Tank über die Regel "
        "'Tank-Spion LX-NET Fuellstand' konfiguriert."
    ),
    parameter_form=lambda: Dictionary(
        elements={},   # keine Parameter nötig
    ),
    condition=HostCondition(),
)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Check-Parameter Rule (Schwellwerte pro Tank)
#    Konfiguriert warn/crit und optionale kg-Umrechnung pro Tank-Nummer.
# ══════════════════════════════════════════════════════════════════════════════

def _parameter_form_tank_spion() -> Dictionary:
    return Dictionary(
        title=Title("Tank-Spion LX-NET Parameter (pro Tank)"),
        help_text=Help(
            "Individuelle Schwellwerte und optionale Liter→kg-Umrechnung "
            "pro Tank-Nummer (Item). WARN/CRIT werden ausgelöst wenn der "
            "Füllstand UNTER die konfigurierte Schwelle fällt."
        ),
        elements={
            "warn_perc": DictElement(
                required=False,
                parameter_form=Float(
                    title=Title("Warning bei Restfüllstand ≤"),
                    unit_symbol="%",
                    prefill=DefaultValue(40.0),
                    custom_validate=(
                        validators.NumberInRange(min_value=0.0, max_value=100.0),
                    ),
                ),
            ),
            "crit_perc": DictElement(
                required=False,
                parameter_form=Float(
                    title=Title("Critical bei Restfüllstand ≤"),
                    unit_symbol="%",
                    prefill=DefaultValue(25.0),
                    custom_validate=(
                        validators.NumberInRange(min_value=0.0, max_value=100.0),
                    ),
                ),
            ),
            "umrechnung_kg": DictElement(
                required=False,
                parameter_form=Float(
                    title=Title("Umrechnungsfaktor Liter → kg"),
                    help_text=Help(
                        "0.0 = keine Umrechnung (nur Liter). "
                        "Beispiel: Diesel ≈ 0.82 kg/L, Heizöl ≈ 0.84 kg/L."
                    ),
                    prefill=DefaultValue(0.0),
                    custom_validate=(
                        validators.NumberInRange(min_value=0.0),
                    ),
                ),
            ),
        },
    )


rule_spec_tank_spion = CheckParameters(
    name="tank_spion",
    title=Title("Tank-Spion LX-NET Füllstand"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_tank_spion,
    condition=HostAndItemCondition(item_title=Title("Tank-Nummer")),
)

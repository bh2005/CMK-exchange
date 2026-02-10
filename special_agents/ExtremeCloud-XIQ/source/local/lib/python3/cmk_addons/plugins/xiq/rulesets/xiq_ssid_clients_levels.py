#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Checkmk Rulesets API v1 – XIQ SSID Clients (global levels)
#
# Provides:
#   - global client thresholds (warn/crit) per SSID service
#   - parameters linked to the check plugin via check_ruleset_name
#
# Compatible with Checkmk 2.4
# =============================================================================

from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    EnforcedService,
    HostAndItemCondition,
    Topic,
)
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    Integer,
    DefaultValue,
)

def _topic() -> Topic:
    return Topic.NETWORKING

def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("XIQ SSID Clients – global thresholds"),
        help_text=Help(
            "Thresholds for wireless client counts per SSID on an AP (piggyback host). "
            "WARNING when total clients ≥ warning; CRITICAL when total clients ≥ critical."
        ),
        elements={
            "global_levels": DictElement(
                required=True,
                parameter_form=Dictionary(
                    title=Title("Client thresholds (total per SSID)"),
                    elements={
                        "warn": DictElement(
                            required=True,
                            parameter_form=Integer(
                                title=Title("Warning at"),
                                help_text=Help("Raise WARNING when total clients ≥ this value"),
                                unit_symbol="Clients",
                                prefill=DefaultValue(100),
                            ),
                        ),
                        "crit": DictElement(
                            required=True,
                            parameter_form=Integer(
                                title=Title("Critical at"),
                                help_text=Help("Raise CRITICAL when total clients ≥ this value"),
                                unit_symbol="Clients",
                                prefill=DefaultValue(150),
                            ),
                        ),
                    },
                ),
            ),
        },
    )

# --- Parameter-Ruleset (bindet an check_ruleset_name="xiq_ssid_clients")
rule_spec_xiq_ssid_clients = CheckParameters(
    name="xiq_ssid_clients",
    title=Title("XIQ SSID Clients – thresholds (per SSID)"),
    topic=_topic(),
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(item_title=Title("SSID")),
    # Wir registrieren das Enforced-Service-Ruleset unten EXPLIZIT:
    create_enforced_service=False,
)

# --- Enforced-Service-Ruleset (liefert 'static_checks:xiq_ssid_clients')
rule_spec_xiq_ssid_clients_enforced = EnforcedService(
    name="xiq_ssid_clients",
    title=Title("XIQ SSID Clients (enforced service)"),
    topic=_topic(),
    # Für statische Services ist hier i. d. R. keine Extra-Form nötig:
    parameter_form=None,
    condition=HostAndItemCondition(item_title=Title("SSID")),
)
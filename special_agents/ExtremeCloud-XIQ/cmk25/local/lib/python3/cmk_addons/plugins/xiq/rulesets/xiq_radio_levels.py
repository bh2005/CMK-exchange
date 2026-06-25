#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Checkmk Rulesets API v1 – XIQ Radio Levels (Clients & Power)
#
# Provides:
#   - client thresholds (warn/crit) per band
#   - minimum TX power thresholds (warn/crit) per band
#   - parameters linked to check plugin via check_ruleset_name
#
# Compatible with Checkmk 2.4
# =============================================================================

from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    Topic,
)
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    Integer,
    DefaultValue,
)

# --------------------------------------------------------------------
# TOPIC
# --------------------------------------------------------------------
def _topic() -> Topic:
    return Topic.NETWORKING

# --------------------------------------------------------------------
# PARAMETER FORM
# --------------------------------------------------------------------
def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("XIQ Radio Levels (Clients & Power)"),
        help_text=Help(
            "Thresholds for ExtremeCloudIQ radio checks per band (2.4 / 5 / 6 GHz). "
            "Client thresholds trigger on high values (>=), TX power thresholds trigger on low values (<=)."
        ),
        elements={
            "warn_clients": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Warning at client count"),
                    help_text=Help("Trigger WARNING when client count >= this value"),
                    prefill=DefaultValue(100),
                    unit_symbol="clients",
                ),
            ),
            "crit_clients": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Critical at client count"),
                    help_text=Help("Trigger CRITICAL when client count >= this value"),
                    prefill=DefaultValue(150),
                    unit_symbol="clients",
                ),
            ),
            "warn_power": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Warning when TX power ≤ (dBm)"),
                    help_text=Help("Trigger WARNING when minimum TX power <= this value"),
                    prefill=DefaultValue(10),
                    unit_symbol="dBm",
                ),
            ),
            "crit_power": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Critical when TX power ≤ (dBm)"),
                    help_text=Help("Trigger CRITICAL when minimum TX power <= this value"),
                    prefill=DefaultValue(5),
                    unit_symbol="dBm",
                ),
            ),
        },
    )

# --------------------------------------------------------------------
# REGISTRATION
# --------------------------------------------------------------------
rule_spec_xiq_radio_levels = CheckParameters(
    name="xiq_radio_levels",                    # MUST MATCH check_ruleset_name
    title=Title("XIQ Radio Levels – clients and power thresholds"),
    topic=_topic(),
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(item_title=Title("Radio Band")),
)
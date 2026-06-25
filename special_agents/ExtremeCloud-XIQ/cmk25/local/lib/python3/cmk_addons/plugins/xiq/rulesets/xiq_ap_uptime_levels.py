#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Checkmk Rulesets API v1 – XIQ AP Uptime thresholds

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
        title=Title("Thresholds for XIQ AP Uptime"),
        help_text=Help(
            "Minimum uptime thresholds before WARN or CRIT are raised. "
            "Useful to detect AP reboots or flapping."
        ),
        elements={
            "min_uptime_warn": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Warning below (seconds)"),
                    help_text=Help("WARN if AP uptime is below this value."),
                    prefill=DefaultValue(6 * 3600),  # 6 hours
                    unit_symbol="s",
                ),
            ),
            "min_uptime_crit": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Critical below (seconds)"),
                    help_text=Help("CRIT if AP uptime is below this value."),
                    prefill=DefaultValue(1 * 3600),  # 1 hour
                    unit_symbol="s",
                ),
            ),
        },
    )


# --------------------------------------------------------------------
# REGISTRATION
# --------------------------------------------------------------------
rule_spec_xiq_ap_uptime_levels = CheckParameters(
    name="xiq_ap_uptime_levels",                # MUST MATCH check_ruleset_name
    title=Title("XIQ AP Uptime – minimum uptime thresholds"),
    topic=_topic(),
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(item_title=Title("Service")),
)

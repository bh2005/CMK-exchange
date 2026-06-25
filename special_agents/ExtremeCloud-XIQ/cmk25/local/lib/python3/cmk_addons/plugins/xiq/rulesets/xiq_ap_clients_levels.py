#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Checkmk Rulesets API v1 – XIQ AP Clients thresholds

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
# TOPIC DEFINITION
# --------------------------------------------------------------------
def _topic() -> Topic:
    return Topic.NETWORKING

# --------------------------------------------------------------------
# FORM DEFINITION
# --------------------------------------------------------------------
def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Thresholds for XIQ AP client totals"),
        help_text=Help(
            "Set warning and critical thresholds for the total number of connected clients "
            "across all WiFi bands (2.4GHz, 5GHz, 6GHz)."
        ),
        elements={
            "global_levels": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Total client thresholds"),
                    help_text=Help(
                        "Define upper levels for the total client count. "
                        "Leave empty to disable thresholds."
                    ),
                    elements={
                        "warn": DictElement(
                            required=True,
                            parameter_form=Integer(
                                title=Title("Warning at"),
                                help_text=Help("Warning threshold for total connected clients."),
                                prefill=DefaultValue(100),
                                unit_symbol="clients",
                            ),
                        ),
                        "crit": DictElement(
                            required=True,
                            parameter_form=Integer(
                                title=Title("Critical at"),
                                help_text=Help("Critical threshold for total connected clients."),
                                prefill=DefaultValue(150),
                                unit_symbol="clients",
                            ),
                        ),
                    },
                ),
            ),
        },
    )

# --------------------------------------------------------------------
# RULESET REGISTRATION
# --------------------------------------------------------------------
rule_spec_xiq_ap_clients_levels = CheckParameters(
    name="xiq_ap_clients_levels",
    title=Title("XIQ AP Clients – total thresholds"),
    topic=_topic(),
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(item_title=Title("Service")),
)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Checkmk Rulesets API v1 – XIQ AP Status parameters
#
# Provides thresholds for:
#   - minimum uptime (warn/crit)
#   - client count thresholds (warn/crit)
#   - treat disconnected APs as WARN/CRIT/UNKNOWN
#   - optional LLDP checks
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
    BooleanChoice,
    DefaultValue,
)


# --------------------------------------------------------------------
# TOPIC — groups the rule under Networking → Parameters
# --------------------------------------------------------------------
def _topic() -> Topic:
    return Topic.NETWORKING


# --------------------------------------------------------------------
# PARAMETER FORM — defines editable config fields in Setup
# --------------------------------------------------------------------
def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Parameters for XIQ AP Status"),
        help_text=Help(
            "Configure thresholds and behavior for the combined XIQ AP Status check. "
            "This includes uptime thresholds, client thresholds, LLDP/CDP checks "
            "and handling of disconnected APs."
        ),
        elements={
            # ------------------------------------------------------------
            # MIN UPTIME THRESHOLDS
            # ------------------------------------------------------------
            "min_uptime_warn": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Warning below (seconds)"),
                    help_text=Help("WARN if AP uptime is below this number of seconds."),
                    prefill=DefaultValue(6 * 3600),  # 6 hours
                    unit_symbol="s",
                ),
            ),
            "min_uptime_crit": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Critical below (seconds)"),
                    help_text=Help("CRIT if AP uptime is below this number of seconds."),
                    prefill=DefaultValue(1 * 3600),  # 1 hour
                    unit_symbol="s",
                ),
            ),

            # ------------------------------------------------------------
            # CLIENT COUNT THRESHOLDS
            # ------------------------------------------------------------
            "client_warn": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Warning at total clients"),
                    help_text=Help(
                        "WARN when the total number of connected clients "
                        "exceeds this value. Leave empty to disable."
                    ),
                ),
            ),
            "client_crit": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Critical at total clients"),
                    help_text=Help(
                        "CRIT when the total number of connected clients "
                        "exceeds this value. Leave empty to disable."
                    ),
                ),
            ),

            # ------------------------------------------------------------
            # CONNECTIVITY HANDLING
            # ------------------------------------------------------------
            "treat_disconnected_as": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("State for disconnected APs (0=OK,1=WARN,2=CRIT,3=UNKNOWN)"),
                    help_text=Help(
                        "How to treat APs that report 'connected = false' in XIQ. "
                        "Default = CRIT."
                    ),
                    prefill=DefaultValue(2),  # CRIT by default
                ),
            ),

            # ------------------------------------------------------------
            # OPTIONAL LLDP CHECKING
            # ------------------------------------------------------------
            "enable_lldp_checks": DictElement(
                required=False,
                parameter_form=BooleanChoice(
                    title=Title("Enable LLDP/CDP information"),
                    help_text=Help(
                        "If enabled, LLDP/CDP neighbor presence will be included in long output. "
                        "Does not affect state unless extended rules are implemented later."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
        },
    )


# --------------------------------------------------------------------
# RULE REGISTRATION — MUST match check_ruleset_name in CheckPlugin
# --------------------------------------------------------------------
rule_spec_xiq_ap_status_levels = CheckParameters(
    name="xiq_ap_status_levels",
    title=Title("XIQ AP Status – parameters"),
    topic=_topic(),
    parameter_form=_parameter_form,
    condition=HostAndItemCondition(item_title=Title("AP Name")),
)
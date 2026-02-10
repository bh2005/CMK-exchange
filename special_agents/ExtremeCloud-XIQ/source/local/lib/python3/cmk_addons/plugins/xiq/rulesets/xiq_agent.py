# -*- coding: utf-8 -*-
# =============================================================================
# License: GNU General Public License v2
#
# Author: Bernd Holzhauer
# Date  : 2026-02-04
# File  : xiq.py
#
# Description:
#   WATO ruleset for the ExtremeCloudIQ (XIQ) Special Agent.
#   Provides a parameter form to configure API connectivity:
#   base URL, credentials, TLS verification, timeout, and optional proxy.
# =============================================================================

from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    migrate_to_password,
    Password,
    String,
    BooleanChoice,
    Integer,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


# ---------------------------------------------------------------------
# PARAMETER FORM – fields exposed in the WATO/Setup rule
# ---------------------------------------------------------------------
def _parameter_form_xiq():
    return Dictionary(
        title=Title("ExtremeCloudIQ (XIQ) – API Integration"),
        help_text=Help(
            "This Special Agent queries the ExtremeCloudIQ REST API and returns "
            "device inventory, radios/BSSIDs, neighbors (LLDP/CDP), active clients, "
            "uptime and API rate-limit usage (API cost)."
        ),
        elements={
            "url": DictElement(
                parameter_form=String(
                    title=Title("API base URL"),
                    prefill=DefaultValue("https://api.extremecloudiq.com"),
                ),
            ),
            "username": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                ),
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password"),
                    migrate=migrate_to_password,
                ),
            ),
            "verify_tls": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Verify TLS certificates"),
                    prefill=DefaultValue(True),
                ),
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("Timeout (seconds)"),
                    prefill=DefaultValue(30),
                ),
            ),
            "proxy_url": DictElement(
                parameter_form=String(
                    title=Title("Proxy (optional)"),
                    help_text=Help(
                        "HTTP/HTTPS proxy URL, e.g. http://user:pass@proxy:3128 "
                        "or http://proxy:3128. Leave empty if no proxy is required."
                    ),
                ),
            ),
        },
    )


# ---------------------------------------------------------------------
# RULE SPEC – register the Special Agent "xiq"
# ---------------------------------------------------------------------
rule_spec_special_agent_xiq = SpecialAgent(
    name="xiq",
    title=Title("ExtremeCloudIQ (XIQ) – Special Agent"),
    topic=Topic.GENERAL,
    parameter_form=_parameter_form_xiq,
)
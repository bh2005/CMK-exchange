# Dateipfad: ~/local/lib/python3/cmk_addons/plugins/logincheck/rulesets/special_agent.py

from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    migrate_to_password,
    Password,
    String,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form_logincheck():
    return Dictionary(
        title=Title("Login Check (HTTP POST)"),
        help_text=Help(
            "Dieser Spezialagent fuehrt einen HTTP-POST-Login-Versuch durch. "
            "Erwartet HTTP 200 als Erfolg. "
            "Bei Erfolg wird die Response (gekuerzt) in den Details angezeigt, "
            "bei Fehlern der Status-Code und die Fehlermeldung."
        ),
        elements={
            "url": DictElement(
                parameter_form=String(
                    title=Title("Login-Endpoint URL"),
                    help_text=Help(
                        "Die vollstaendige URL, an die der POST-Request gesendet wird. "
                        "Beispiel: https://api.example.com/login"
                    ),
                    prefill=DefaultValue("https://"),
                ),
            ),
            "username": DictElement(
                parameter_form=String(
                    title=Title("Benutzername"),
                    help_text=Help("Der Benutzername fuer den POST-Request."),
                ),
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Passwort"),
                    help_text=Help("Das Passwort (wird verschluesselt gespeichert)."),
                    migrate=migrate_to_password,
                ),
            ),
        },
    )


rule_spec_special_agent_logincheck = SpecialAgent(
    name="logincheck",
    title=Title("Login Check (HTTP POST)"),
    topic=Topic.GENERAL,
    parameter_form=_parameter_form_logincheck,
)
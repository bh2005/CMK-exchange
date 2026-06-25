from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
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
            "Performs an HTTP POST login request and reports success (HTTP 200) or failure. "
            "The credentials are sent as JSON payload to the specified endpoint."
        ),
        elements={
            "url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Login endpoint URL"),
                    help_text=Help("Full URL for the POST request, e.g. https://api.example.com/login"),
                    prefill=DefaultValue("https://"),
                ),
            ),
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                ),
            ),
            "password": DictElement(
                required=True,
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
            "proxy_url": DictElement(
                parameter_form=String(
                    title=Title("Proxy URL (optional)"),
                    help_text=Help(
                        "HTTP/HTTPS proxy, e.g. http://proxy:3128. Leave empty for no proxy."
                    ),
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

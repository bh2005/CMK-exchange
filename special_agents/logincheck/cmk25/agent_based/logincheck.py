# Dateipfad: ~/local/lib/python3/cmk_addons/plugins/logincheck/agent_based/logincheck.py

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def parse_logincheck(string_table: StringTable) -> dict | None:
    if not string_table:
        return None

    line = " ".join(string_table[0]).strip()

    try:
        parts = line.split(" RESPONSE:", 1)
        status_part = parts[0]
        response = parts[1].strip() if len(parts) > 1 else ""

        code_parts = status_part.split(" CODE:", 1)
        status_line = code_parts[0]
        code = code_parts[1].strip() if len(code_parts) > 1 else "?"

        status = status_line.split("STATUS:")[1].strip()

        return {
            "status": status,
            "code": code,
            "response": response,
        }
    except Exception:
        return None


def discovery_logincheck(section: dict | None) -> DiscoveryResult:
    if section is not None:
        yield Service()


def check_logincheck(section: dict | None):
    if section is None:
        yield Result(state=State.UNKNOWN, summary="Keine Daten vom Agent erhalten")
        return

    if section["status"] == "OK":
        yield Result(
            state=State.OK,
            summary="Login erfolgreich (HTTP 200)",
            details=f"Response (gekuerzt): {section['response']}"
        )
    else:
        yield Result(
            state=State.CRIT,
            summary=f"Login fehlgeschlagen (Code: {section['code']})",
            details=f"Response: {section['response']}"
        )


agent_section_logincheck = AgentSection(
    name="logincheck",
    parse_function=parse_logincheck,
)

check_plugin_logincheck = CheckPlugin(
    name="logincheck",
    service_name="HTTP Login Check",
    sections=["logincheck"],
    discovery_function=discovery_logincheck,
    check_function=check_logincheck,
)
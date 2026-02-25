#!/usr/bin/env bash
# =============================================================================
# Create Checkmk 2.4 Special Agent Skeleton (with Authentication Template)
# =============================================================================
# Usage:
#   ./mk_special_agent_skeleton.sh <plugin_family> [<site_user>] [--with-checks]
#
# Example:
#   ./mk_special_agent_skeleton.sh myapi              # minimal (agent + ruleset + call)
#   ./mk_special_agent_skeleton.sh myapi test --with-checks  # includes check plugin
#
# Template based on logincheck agent showing:
# - Username/Password handling (encrypted storage)
# - HTTP requests with requests library
# - SSL verification option
# - Proper error handling
# - Response parsing
#
# References:
# - https://docs.checkmk.com/latest/en/devel_intro.html (Introduction to developing extensions)
# - https://docs.checkmk.com/latest/en/devel_special_agents.html (Special agents development)
# - https://docs.checkmk.com/latest/en/devel_check_plugins.html (Agent-based check plug-ins)
# - https://docs.checkmk.com/latest/en/devel_check_plugins_rulesets.html (Rulesets API)
# - Help > Developer resources > Plug-in API references (in Checkmk GUI)
# =============================================================================

set -euo pipefail

# ----- Parse arguments --------------------------------------------------------
PLUGIN_FAMILY=""
SITE_USER=""
WITH_CHECKS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-checks) WITH_CHECKS=true; shift ;;
    *)
      if [[ -z "$PLUGIN_FAMILY" ]]; then
        PLUGIN_FAMILY="$1"
      elif [[ -z "$SITE_USER" ]]; then
        SITE_USER="$1"
      else
        echo "Unknown argument: $1" >&2
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ -z "$PLUGIN_FAMILY" ]]; then
  echo "Usage: $0 <plugin_family> [<site_user>] [--with-checks]"
  exit 1
fi

# Validate plugin family name
if [[ ! "$PLUGIN_FAMILY" =~ ^[a-zA-Z0-9_][-a-zA-Z0-9_]*$ ]]; then
  echo "Error: <plugin_family> must match [a-zA-Z0-9_][-_a-zA-Z0-9_]*"
  exit 2
fi

# Base directory
BASE_DIR="${HOME}/local/lib/python3/cmk_addons/plugins/${PLUGIN_FAMILY}"
AGENT_BASENAME="${PLUGIN_FAMILY}"
AGENT_EXEC="agent_${AGENT_BASENAME}"

# Create directories
mkdir -p "${BASE_DIR}/libexec"
mkdir -p "${BASE_DIR}/rulesets"
mkdir -p "${BASE_DIR}/server_side_calls"

if [[ "$WITH_CHECKS" == true ]]; then
  mkdir -p "${BASE_DIR}/agent_based"
fi

# =============================================================================
# SPECIAL AGENT EXECUTABLE (with authentication)
# =============================================================================
AGENT_PATH="${BASE_DIR}/libexec/${AGENT_EXEC}"
if [[ ! -e "${AGENT_PATH}" ]]; then
  cat > "${AGENT_PATH}" <<'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Special Agent for PLUGIN_FAMILY
Connects to API with authentication and retrieves monitoring data.
"""

import argparse
import json
import sys
from typing import Any

import requests


def fetch_api_data(
    url: str,
    username: str,
    password: str,
    insecure: bool = False,
    timeout: int = 60,
) -> dict[str, Any]:
    """
    Fetch data from API endpoint with authentication.
    
    Args:
        url: API endpoint URL
        username: Authentication username
        password: Authentication password
        insecure: Disable SSL verification
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with API response data
        
    Raises:
        requests.RequestException: On connection/request errors
    """
    session = requests.Session()
    
    if insecure:
        session.verify = False
        # Suppress InsecureRequestWarning
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Configure authentication - adjust based on your API
    # Option 1: Basic Auth
    # session.auth = (username, password)
    
    # Option 2: Token-based (login first)
    payload = {
        "username": username,
        "password": password,
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    # Login request (adjust endpoint and method as needed)
    try:
        login_resp = session.post(
            url,
            json=payload,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
        )
        login_resp.raise_for_status()
    except requests.RequestException as e:
        raise requests.RequestException(f"Login failed: {e}")
    
    # Extract token or session cookie (adjust based on your API)
    # token = login_resp.json().get("token")
    # session.headers.update({"Authorization": f"Bearer {token}"})
    
    # Fetch actual data (replace with your API endpoints)
    # Example: Get system status
    try:
        status_resp = session.get(
            f"{url}/status",  # Adjust endpoint
            timeout=timeout,
        )
        status_resp.raise_for_status()
        data = status_resp.json()
    except requests.RequestException as e:
        raise requests.RequestException(f"Data fetch failed: {e}")
    
    return data


def output_section(name: str, data: Any) -> None:
    """
    Output a Checkmk agent section.
    
    For JSON data, output on a single line so the check plugin
    can parse it correctly with itertools + json.loads().
    
    See: https://docs.checkmk.com/latest/en/devel_special_agents.html
    """
    print(f"<<<{name}>>>")
    
    if isinstance(data, (dict, list)):
        # Output JSON on a single line
        print(json.dumps(data))
    elif isinstance(data, str):
        print(data)
    else:
        print(str(data))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Checkmk special agent: PLUGIN_FAMILY"
    )
    parser.add_argument("--url", required=True, help="API endpoint URL")
    parser.add_argument("--username", required=True, help="Authentication username")
    parser.add_argument("--password", required=True, help="Authentication password")
    parser.add_argument("--insecure", action="store_true", help="Disable SSL verification")
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout (seconds)")
    
    args = parser.parse_args()
    
    try:
        # Fetch data from API
        data = fetch_api_data(
            url=args.url,
            username=args.username,
            password=args.password,
            insecure=args.insecure,
            timeout=args.timeout,
        )
        
        # Output section(s) - adjust based on your data structure
        # Example: Main status section
        output_section("PLUGIN_FAMILY_status", {
            "status": data.get("status", "UNKNOWN"),
            "code": data.get("code", "N/A"),
            "message": data.get("message", "No message"),
        })
        
        # Example: Additional data section (if available)
        if "items" in data:
            output_section("PLUGIN_FAMILY_items", data["items"])
        
        return 0
        
    except requests.RequestException as e:
        # Output error section so check plugin can handle it
        output_section("PLUGIN_FAMILY_status", {
            "status": "FAILED",
            "code": "EXCEPTION",
            "message": str(e)[:500],  # Limit error message length
        })
        return 0  # Return 0 to allow check plugin to process error
    
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
EOF

  sed -i "s/PLUGIN_FAMILY/${PLUGIN_FAMILY}/g" "${AGENT_PATH}"
  chmod +x "${AGENT_PATH}"
fi

# =============================================================================
# SPECIAL AGENT RULESET (with Password field)
# =============================================================================
RULESET_PATH="${BASE_DIR}/rulesets/special_agent.py"
if [[ ! -e "${RULESET_PATH}" ]]; then
  cat > "${RULESET_PATH}" <<'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Special Agent Ruleset for PLUGIN_FAMILY"""

from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    migrate_to_password,
    Password,
    String,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form_PLUGIN_FAMILY():
    return Dictionary(
        title=Title("PLUGIN_FAMILY_UPPER API Connection"),
        help_text=Help(
            "This special agent connects to the PLUGIN_FAMILY_UPPER API "
            "using username/password authentication and retrieves monitoring data."
        ),
        elements={
            "url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("API Endpoint URL"),
                    help_text=Help(
                        "The full URL of the API endpoint. "
                        "Example: https://api.example.com or https://192.168.1.100:8443"
                    ),
                    prefill=DefaultValue("https://"),
                ),
            ),
            "username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help("Username for API authentication"),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    help_text=Help("Password (stored encrypted)"),
                    migrate=migrate_to_password,
                ),
            ),
            "insecure": DictElement(
                required=False,
                parameter_form=SingleChoice(
                    title=Title("SSL Certificate Verification"),
                    help_text=Help(
                        "Choose whether to verify SSL certificates. "
                        "Disabling verification should only be used for testing!"
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="verify",
                            title=Title("Verify SSL certificates (recommended)"),
                        ),
                        SingleChoiceElement(
                            name="insecure",
                            title=Title("Disable SSL verification (insecure!)"),
                        ),
                    ],
                    prefill=DefaultValue("verify"),
                ),
            ),
        },
    )


rule_spec_special_agent_PLUGIN_FAMILY = SpecialAgent(
    name="PLUGIN_FAMILY",
    title=Title("PLUGIN_FAMILY_UPPER"),
    topic=Topic.CLOUD,  # Adjust: CLOUD, GENERAL, SERVER_HARDWARE, etc.
    parameter_form=_parameter_form_PLUGIN_FAMILY,
)
EOF

  sed -i "s/PLUGIN_FAMILY/${AGENT_BASENAME}/g" "${RULESET_PATH}"
  sed -i "s/PLUGIN_FAMILY_UPPER/${PLUGIN_FAMILY^^}/g" "${RULESET_PATH}"
  chmod 0644 "${RULESET_PATH}"
fi

# =============================================================================
# SERVER-SIDE CALL (with password handling)
# =============================================================================
CALL_PATH="${BASE_DIR}/server_side_calls/special_agent.py"
if [[ ! -e "${CALL_PATH}" ]]; then
  cat > "${CALL_PATH}" <<'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server-side call registration for PLUGIN_FAMILY"""

from cmk.server_side_calls.v1 import (
    SpecialAgentCommand,
    SpecialAgentConfig,
    noop_parser,
)


def _agent_arguments(params, host_config):
    """Generate command line arguments for the special agent."""
    args = []
    
    # Required parameters
    args.extend(["--url", params["url"]])
    args.extend(["--username", params["username"]])
    args.extend(["--password", params["password"].unsafe()])
    
    # Optional: SSL verification
    if params.get("insecure") == "insecure":
        args.append("--insecure")
    
    yield SpecialAgentCommand(command_arguments=args)


special_agent_PLUGIN_FAMILY = SpecialAgentConfig(
    name="PLUGIN_FAMILY",
    parameter_parser=noop_parser,
    commands_function=_agent_arguments,
)
EOF

  sed -i "s/PLUGIN_FAMILY/${AGENT_BASENAME}/g" "${CALL_PATH}"
  chmod 0644 "${CALL_PATH}"
fi

# =============================================================================
# AGENT-BASED CHECK PLUGIN (optional)
# =============================================================================
if [[ "$WITH_CHECKS" == true ]]; then

  CHECK_PATH="${BASE_DIR}/agent_based/${AGENT_BASENAME}.py"
  if [[ ! -e "${CHECK_PATH}" ]]; then
    cat > "${CHECK_PATH}" <<'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent-based check plugin for PLUGIN_FAMILY"""

import itertools
import json

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def parse_PLUGIN_FAMILY_status(string_table: StringTable) -> dict | None:
    """
    Parse the <<<PLUGIN_FAMILY_status>>> section.
    
    The check plug-in receives the agent section as a two-dimensional 
    list ('list of lists') of strings. We convert this to a flat list,
    concatenate with spaces, and parse as JSON.
    
    See: https://docs.checkmk.com/latest/en/devel_special_agents.html
    """
    if not string_table:
        return None
    
    try:
        # Flatten two-dimensional list to one-dimensional
        flatlist = list(itertools.chain.from_iterable(string_table))
        # Concatenate array with spaces and parse JSON
        parsed = json.loads(" ".join(flatlist))
        return parsed
    except (json.JSONDecodeError, ValueError):
        return None


def discover_PLUGIN_FAMILY_status(section: dict | None) -> DiscoveryResult:
    """Discover the PLUGIN_FAMILY status service."""
    if section is not None:
        yield Service()


def check_PLUGIN_FAMILY_status(section: dict | None) -> CheckResult:
    """Check the PLUGIN_FAMILY status."""
    if section is None:
        yield Result(
            state=State.UNKNOWN,
            summary="No data received from agent"
        )
        return
    
    status = section.get("status", "UNKNOWN")
    code = section.get("code", "N/A")
    message = section.get("message", "No message")
    
    # Determine check state based on status
    if status == "OK" or code == "200":
        state = State.OK
        summary = f"API connection successful (Code: {code})"
    elif status == "FAILED" or status == "EXCEPTION":
        state = State.CRIT
        summary = f"API connection failed (Code: {code})"
    else:
        state = State.WARN
        summary = f"Unknown status: {status} (Code: {code})"
    
    yield Result(
        state=state,
        summary=summary,
        details=f"Status: {status}\nCode: {code}\nMessage: {message}"
    )


# Section registration
agent_section_PLUGIN_FAMILY_status = AgentSection(
    name="PLUGIN_FAMILY_status",
    parse_function=parse_PLUGIN_FAMILY_status,
)

# Check plugin registration
check_plugin_PLUGIN_FAMILY_status = CheckPlugin(
    name="PLUGIN_FAMILY_status",
    service_name="PLUGIN_FAMILY_UPPER Status",
    sections=["PLUGIN_FAMILY_status"],
    discovery_function=discover_PLUGIN_FAMILY_status,
    check_function=check_PLUGIN_FAMILY_status,
)
EOF

    sed -i "s/PLUGIN_FAMILY/${AGENT_BASENAME}/g" "${CHECK_PATH}"
    sed -i "s/PLUGIN_FAMILY_UPPER/${PLUGIN_FAMILY^^}/g" "${CHECK_PATH}"
    chmod 0644 "${CHECK_PATH}"
  fi

fi

# =============================================================================
# README
# =============================================================================
README_PATH="${BASE_DIR}/README.md"
if [[ ! -e "${README_PATH}" ]]; then
  cat > "${README_PATH}" <<EOF
# ${PLUGIN_FAMILY} – Checkmk Special Agent

Special agent for monitoring ${PLUGIN_FAMILY^^} via API with authentication.

## Features

- Username/Password authentication
- SSL certificate verification (optional disable)
- Encrypted password storage
- HTTP request error handling
- Structured agent output

## Quick Start

### 1. Customize the Agent

Edit \`libexec/agent_${AGENT_BASENAME}\`:

\`\`\`python
# Adjust authentication method (Basic Auth, Token, etc.)
# Modify API endpoints
# Add custom data parsing
\`\`\`

### 2. Activate Plugin

\`\`\`bash
cmk -R
\`\`\`

### 3. Configure in GUI

**Setup → Agents → VM, Cloud, Container → ${PLUGIN_FAMILY^^}**

- Enter API URL
- Provide username/password
- Optional: Disable SSL verification

### 4. Test

\`\`\`bash
# See generated command
cmk -D <HOSTNAME>

# Test agent manually
~/local/lib/python3/cmk_addons/plugins/${PLUGIN_FAMILY}/libexec/agent_${AGENT_BASENAME} \\
  --url "https://api.example.com" \\
  --username "myuser" \\
  --password "mypass"

# Run discovery
cmk -I <HOSTNAME>
\`\`\`

## Authentication Methods

The template supports multiple authentication patterns:

### Basic Auth
\`\`\`python
session.auth = (username, password)
\`\`\`

### Token-based (Login + Bearer)
\`\`\`python
# Login to get token
resp = session.post(url, json={"username": username, "password": password})
token = resp.json()["token"]

# Use token in headers
session.headers.update({"Authorization": f"Bearer {token}"})
\`\`\`

### API Key
\`\`\`python
session.headers.update({"X-API-Key": api_key})
\`\`\`

## Directory Structure

\`\`\`
${PLUGIN_FAMILY}/
├── libexec/agent_${AGENT_BASENAME}           # Special agent (Python)
├── rulesets/special_agent.py                 # GUI configuration
├── server_side_calls/special_agent.py        # Command generation
EOF

  if [[ "$WITH_CHECKS" == true ]]; then
    cat >> "${README_PATH}" <<EOF
├── agent_based/${AGENT_BASENAME}.py          # Check plugin
EOF
  fi

  cat >> "${README_PATH}" <<EOF
└── README.md
\`\`\`

## Password Security

- Passwords are stored encrypted in Checkmk
- Use \`params["password"].unsafe()\` to access in server_side_calls
- Never log passwords in plain text

## References

- [Introduction to Developing Extensions](https://docs.checkmk.com/latest/en/devel_intro.html)
- [Developing Special Agents](https://docs.checkmk.com/latest/en/devel_special_agents.html)
- [Developing Agent-based Check Plug-ins](https://docs.checkmk.com/latest/en/devel_check_plugins.html)
- [Rulesets API](https://docs.checkmk.com/latest/en/devel_check_plugins_rulesets.html)
- [Password Handling in Rulesets](https://docs.checkmk.com/latest/en/devel_check_plugins_rulesets.html#passwords)
- **In Checkmk GUI:** Help > Developer resources > Plug-in API references
EOF
fi

# =============================================================================
# OWNERSHIP
# =============================================================================
if [[ -n "${SITE_USER}" ]]; then
  chown -R "${SITE_USER}:${SITE_USER}" "${BASE_DIR}"
fi

# =============================================================================
# SUMMARY
# =============================================================================
echo "========================================="
echo "Special Agent Skeleton Created!"
echo "========================================="
echo "Plugin: ${PLUGIN_FAMILY}"
echo "Location: ${BASE_DIR}"
echo ""
echo "Files created:"
echo "  ✓ ${AGENT_PATH}"
echo "  ✓ ${RULESET_PATH}"
echo "  ✓ ${CALL_PATH}"

if [[ "$WITH_CHECKS" == true ]]; then
  echo "  ✓ ${CHECK_PATH}"
fi

echo "  ✓ ${README_PATH}"
echo ""
echo "Features:"
echo "  ✓ Username/Password authentication"
echo "  ✓ Encrypted password storage"
echo "  ✓ SSL verification (configurable)"
echo "  ✓ HTTP requests with error handling"
echo ""
echo "Next steps:"
echo "  1. Edit libexec/agent_${AGENT_BASENAME} - customize API calls"
echo "  2. Run: cmk -R"
echo "  3. Configure in Setup → Agents → VM, Cloud, Container"
echo "  4. Test with: cmk -D <HOSTNAME>"
echo ""
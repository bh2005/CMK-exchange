Hier ist eine **aktuelle Guideline für die Entwicklung von Special Agents** in Checkmk (Stand Februar 2026, Checkmk 2.3.x und 2.4.x).

Die Guideline basiert auf:

- aktuellem Quellcode (https://github.com/Checkmk/checkmk/tree/master/cmk/special_agents)
- offizieller (spärlicher) Dokumentation
- bewährten Community-Patterns (XIQ, AWS, Azure, VMware, Nutanix, …)
- MKP-Best-Practices 2025/2026

### 1. Warum Python-Special-Agent statt alter ASCII-Scripts?

| Methode                     | Checkmk-Version | MKP-fähig | UI-Parameter | Async/Bulk | Empfohlen 2026? |
|-----------------------------|------------------|-----------|--------------|------------|-----------------|
| ASCII-Shell-Script          | alle             | Nein      | Nein         | Nein       | Nein            |
| Python-Special-Agent (SSC)  | 2.1.0+ (gut ab 2.3) | Ja     | Ja           | Ja         | **Ja**          |

→ Seit 2.3/2.4 ist der **Python-Weg mit Server-Side-Calls (SSC)** der einzige ernsthaft empfohlene Weg für neue, professionelle Agents.

### 2. Verzeichnisstruktur (MKP-kompatibel)

Empfohlene Struktur (wie bei XIQ, AWS, Azure, …):

```
cmk_addons/plugins/<pluginname>/
├── libexec/
│   └── agent_<pluginname>                    # ← der eigentliche Agent (ausführbar, kein .py!)
├── server_side_calls/
│   └── <pluginname>_ssc.py                   # ← Command-Generierung + Parameter-Form
├── rulesets/
│   ├── <pluginname>_agent.py                 # ← Agent-Regel (WATO/Setup)
│   ├── <pluginname>_status_levels.py         # Check-Parameter-Regeln
│   ├── <pluginname>_clients_levels.py
│   └── ...
├── agent_based/
│   ├── sections.py                           # ← alle Section-Parser
│   ├── check_status.py                       # ← Check-Plugins
│   ├── check_clients.py
│   ├── check_uptime.py
│   ├── inventory_devices.py                  # ← Inventory-Plugins
│   └── common.py                             # ← Shared Utils
├── graphing/
│   ├── <pluginname>_metrics.py
│   ├── <pluginname>_graphs.py
│   └── <pluginname>_perfometers.py
├── checkman/                                 # ← Manpages (plain text, KEIN .py!)
│   ├── <pluginname>_status
│   ├── <pluginname>_clients
│   └── ...
└── README.md
```

### 3. Naming Conventions – sehr wichtig!

| Komponente                  | Dateiname                              | Python-Variablenname                       | Beispiel (XIQ)                     |
|-----------------------------|----------------------------------------|--------------------------------------------|------------------------------------|
| Special Agent Executable    | `agent_<pluginname>`                   | —                                          | `agent_xiq`                        |
| Server-Side-Call            | `<pluginname>_ssc.py`                  | `special_agent_<pluginname>`               | `special_agent_xiq`                |
| Agent-Regel (WATO)          | `<pluginname>_agent.py`                | `rule_spec_special_agent_<pluginname>`     | `rule_spec_special_agent_xiq`      |
| Check-Plugin                | `check_<checkname>.py`                 | `check_plugin_<checkname>`                 | `check_plugin_xiq_radio`           |
| Check-Parameter-Regel       | `<pluginname>_<checkname>_levels.py`   | `rule_spec_<pluginname>_<checkname>_levels`| `rule_spec_xiq_radio_levels`       |
| Section Parser              | `sections.py` oder `sections_*.py`     | `agent_section_<sectionname>`              | `agent_section_xiq_summary`        |
| Inventory-Plugin            | `inventory_<name>.py`                  | `inventory_plugin_<name>`                  | `inventory_plugin_xiq_devices`     |
| Manpage                     | `<pluginname>_<checkname>`             | — (plain text)                             | `xiq_radio`                        |

### 4. Minimalbeispiel – Server-Side-Call + Agent (Checkmk 2.4)

#### 4.1 agent_myapi (ausführbar, **keine** .py-Endung!)

```bash
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# agent_myapi

import sys
import argparse
import requests
import json
from pathlib import Path

CACHE_DIR = Path("/tmp/checkmk_myapi_cache")
CACHE_DIR.mkdir(exist_ok=True)

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--api-key", required=True)
    p.add_argument("--no-cert-check", action="store_true")
    p.add_argument("--timeout", type=int, default=30)
    return p.parse_args()

def get_token(args):
    cache_file = CACHE_DIR / "token.json"
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        if data.get("expires") > time.time():
            return data["token"]

    # Token holen (Beispiel OAuth2 Client Credentials)
    r = requests.post(
        f"{args.url}/auth/token",
        data={"grant_type": "client_credentials"},
        auth=(args.api_key, ""),
        timeout=args.timeout,
        verify=not args.no_cert_check,
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    cache_file.write_text(json.dumps({"token": token, "expires": time.time() + 3600}))
    return token

def main():
    args = parse_args()
    token = get_token(args)

    headers = {"Authorization": f"Bearer {token}"}

    try:
        r = requests.get(f"{args.url}/api/v1/devices", headers=headers, timeout=args.timeout)
        r.raise_for_status()
        devices = r.json()

        print("<<<myapi_summary:sep(124)>>>")
        print(f"total|{len(devices)}")

        for dev in devices:
            hostname = dev["serial"]  # oder dev["hostname"]
            print(f"<<<<{hostname}>>>>")
            print("<<<myapi_device:sep(124)>>>")
            print(f"status|{dev['status']}")
            print(f"model|{dev['model']}")
            print(f"<<<<>>>>")

        print("<<<myapi_login>>>")
        print("STATUS:OK")
    except Exception as e:
        print("<<<myapi_login>>>")
        print(f"STATUS:FAILED ERROR:{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

#### 4.2 server_side_calls/myapi_ssc.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# myapi_ssc.py

from typing import Iterator
from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import (
    SpecialAgentConfig,
    SpecialAgentCommand,
    HostConfig,
    Secret,
    HostSettings,
)

class MyApiParams(BaseModel):
    url: str = Field(..., description="API Base URL")
    api_key: Secret = Field(..., description="API Key / Client Secret")
    verify_tls: bool = Field(True, description="Verify TLS certificates")
    timeout: int = Field(30, description="Timeout in seconds")

def _commands(
    params: MyApiParams,
    host_config: HostConfig,
    _host_settings: HostSettings,
) -> Iterator[SpecialAgentCommand]:
    args = [
        "--url", params.url,
        "--api-key", params.api_key.unsafe(),
        "--timeout", str(params.timeout),
    ]
    if not params.verify_tls:
        args.append("--no-cert-check")

    yield SpecialAgentCommand(
        command_arguments=args,
        stdin=None,
    )

special_agent_myapi = SpecialAgentConfig(
    name="myapi",
    parameter_parser=MyApiParams.model_validate,
    commands_function=_commands,
)
```

#### 4.3 rulesets/myapi_agent.py (WATO-Regel)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# myapi_agent.py

from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.form_specs import (
    Dictionary, DictElement, String, Password,
    migrate_to_password, BooleanChoice, Integer, DefaultValue
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic

def _parameter_form_myapi():
    return Dictionary(
        title=Title("MyAPI Integration"),
        help_text=Help("Connect to MyAPI monitoring endpoint"),
        elements={
            "url": DictElement(
                parameter_form=String(
                    title=Title("API Base URL"),
                    prefill=DefaultValue("https://api.mycompany.com"),
                ),
            ),
            "api_key": DictElement(
                parameter_form=Password(
                    title=Title("API Key"),
                    migrate=migrate_to_password,
                ),
            ),
            "verify_tls": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Verify TLS certificate"),
                    prefill=DefaultValue(True),
                ),
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("Timeout (seconds)"),
                    prefill=DefaultValue(30),
                ),
            ),
        },
    )

rule_spec_special_agent_myapi = SpecialAgent(
    name="myapi",
    title=Title("MyAPI Special Agent"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form_myapi,
)
```

### 5. Best Practices & Lessons Learned 2026

1. **Immer** `--no-cert-check` und `--timeout` als Parameter anbieten
2. **Token-Caching** → mindestens 1 h (pickle oder file-based)
3. **Rate-Limit** → 429 erkennen → exponential backoff (3–5 Versuche)
4. **Paging** → alle großen Listen seitenweise abrufen
5. **Piggyback** → pro Device/AP/VM ein Piggyback-Host
6. **Sections** → mindestens eine Status-Section (`<<<myapi_login>>>`) immer ausgeben
7. **Error Handling** → niemals sys.exit(1) bei API-Fehlern – immer Sections schreiben
8. **MKP-Packaging** → Pflicht für saubere Updates
9. **Checkmk-Versionen** → mindestens 2.3.0 erforderlich angeben
10. **Manpages** → pro Check eine Datei (plain text)

### 6. Schnell-Checkliste – fertig?

- [ ] agent_myapi ausführbar + shebang
- [ ] myapi_ssc.py registriert `special_agent_myapi`
- [ ] myapi_agent.py registriert `rule_spec_special_agent_myapi`
- [ ] mindestens 1 Section + 1 Check-Plugin
- [ ] Manpage vorhanden
- [ ] README.md mit Install-Anleitung

Viel Erfolg beim nächsten Special Agent!  

Hier ist eine aktuelle **Entwickler-Guideline** für neue **Notification-Plugins** (Notification Methods) in Checkmk 2.3 und 2.4 (Stand Februar 2026).

Die offizielle Dokumentation behandelt das Thema immer noch sehr knapp (meist nur das alte ASCII-Script-Format). Die moderne, empfohlene Art mit **MKPs + Python + Parameter-Registrierung** ist vor allem aus Community-Beiträgen, Werken, YouTube-Sessions (z. B. Checkmk Conference) und dem Quellcode ersichtlich.

### Zwei parallele Wege existieren (2024–2026)

| Methode                        | Typ                  | Checkmk-Versionen     | Empfohlen für Neuentwicklungen? | MKP-fähig? | UI-Parameter möglich? | Async / Bulk-fähig? |
|-------------------------------|----------------------|------------------------|----------------------------------|------------|-------------------------|----------------------|
| ASCII-Shell-Script            | „Custom notification script“ | alle (auch 2.4)       | Nein – nur für sehr einfache Fälle | Nein       | Nein                    | Nein                 |
| Python-Notification-Plugin    | „Notification method plugin“ | 2.1.0+ (gut ab 2.3)   | **Ja**                           | Ja         | Ja (Valuespec)          | Ja (seit ~2.3)       |

→ Seit Checkmk 2.3/2.4 solltest du **ausschließlich** den Python-Weg nutzen, wenn du eine saubere, update-sichere, übersetzbare und UI-konfigurierbare Lösung willst.

### 1. Datei-Ort & Namenskonvention (Python-Plugin)

```text
~/local/share/check_mk/notifications/
   └── my_company_teams_notify.py      # oder .sh bei altem Stil
```

- Dateiname frei wählbar, aber sprechend und klein geschrieben
- Muss ausführbar sein → `chmod +x`
- Bei Python: Shebang `#!/usr/bin/env python3`

### 2. Minimales Python-Notification-Script (ohne UI-Parameter)

```python
#!/usr/bin/env python3
# encoding: utf-8
# my_company_teams_notify.py

import sys
import json
from cmk.notification_plugins import utils

context = utils.collect_context()

# ────────────────────────────────────────────────
# Typische Context-Variablen (Auswahl)
# ────────────────────────────────────────────────
WHAT          = context.get("WHAT",          "SERVICE")          # SERVICE / HOST
HOSTNAME      = context.get("HOSTNAME",      "?")
SERVICEDESC   = context.get("SERVICEDESC",   "-")
SERVICESTATE  = context.get("SERVICESTATE",  "OK")
OUTPUT        = context.get("SERVICEOUTPUT", context.get("HOSTOUTPUT", "?"))
NOTIFICATIONTYPE = context.get("NOTIFICATIONTYPE", "PROBLEM")

# Beispiel: Nur bei PROBLEM senden
if NOTIFICATIONTYPE not in ["PROBLEM", "RECOVERY"]:
    sys.exit(0)

# Hier deine Logik (z. B. Microsoft Teams Webhook)
payload = {
    "text": f"**{WHAT} {NOTIFICATIONTYPE}** – {HOSTNAME} / {SERVICEDESC}\n"
            f"State: **{SERVICESTATE}**\n"
            f"Output: {OUTPUT}"
}

# requests.post("https://your-teams-webhook", json=payload)
# Fehlerbehandlung nicht vergessen!

utils.notify_spoolfile_success()   # oder utils.notify_spoolfile_error(msg)
```

### 3. Empfohlene moderne Variante mit **UI-Parametern** (Check API Style, 2.3+ / 2.4)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# my_company_teams_notify.py

import sys
import json
import requests
from typing import Any

from cmk.notification_plugins import utils
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    HTTPUrl,
    IndividualOrStoredPassword,
    TextInput,
    Tuple,
)

# ────────────────────────────────────────────────
# 1. Valuespec → UI-Formular in Notification Rule
# ────────────────────────────────────────────────
def _vs_parameters():
    return Dictionary(
        title = _("Microsoft Teams Notification"),
        elements = [
            ("webhook_url", HTTPUrl(
                title = _("Teams Webhook URL"),
                allow_port = True,
                size = 80,
            )),
            ("channel", TextInput(
                title = _("Channel / Team Name (optional)"),
                size = 40,
            )),
            ("priority", Tuple(
                title = _("Priority mapping"),
                elements = [
                    TextInput(title=_("OK / UP")),
                    TextInput(title=_("WARN / DOWN")),
                    TextInput(title=_("CRIT / UNREACH")),
                ],
                default_value = ("good", "warning", "danger"),
            )),
        ],
        optional_keys = ["channel"],
    )

# Registrierung – wird automatisch erkannt (seit ~2.3)
parameters = _vs_parameters()

# ────────────────────────────────────────────────
# 2. Eigentliche Notification-Logik
# ────────────────────────────────────────────────
def process_by_status(context: dict[str, str]) -> int:
    params = context.get("PARAMETERS", {})
    webhook = params.get("webhook_url")

    if not webhook:
        utils.write_to_spoolfile("ERROR: No webhook URL configured")
        return 2

    # Farbe / Emoji je nach Status
    state = context.get("SERVICESTATE", context.get("HOSTSTATE", "OK"))
    color_map = dict(params.get("priority", ["good", "warning", "danger"]))
    color = color_map.get(state, "gray")

    payload = {
        "@type": "MessageCard",
        "themeColor": color,
        "title": f"{context.get('WHAT')} {context.get('NOTIFICATIONTYPE')} - {context.get('HOSTNAME')}",
        "text": context.get("SERVICEOUTPUT") or context.get("HOSTOUTPUT"),
        # weitere Felder: facts, potentialActions, etc.
    }

    try:
        r = requests.post(webhook, json=payload, timeout=10)
        r.raise_for_status()
        utils.notify_spoolfile_success()
        return 0
    except Exception as e:
        utils.write_to_spoolfile(f"ERROR: {e}")
        return 2

if __name__ == "__main__":
    sys.exit(process_by_status(utils.collect_context()))
```

### 4. Wichtige Dateien & Verzeichnisse (2024–2026)

```text
~/local/share/check_mk/notifications/           ← Custom Notification-Scripts (alle Typen)
~/local/lib/python3/cmk/gui/plugins/watolib/    ← falls du die Regel-Seite erweitern willst (selten)
```

### 5. Empfohlene Best Practices (2.4)

- Immer `utils.collect_context()` verwenden
- Fehler → `utils.write_to_spoolfile("ERROR: …")` + `return 2`
- Erfolg → `utils.notify_spoolfile_success()` + `return 0`
- UI → Dictionary + Valuespec (siehe `cmk.gui.valuespec`)
- Bulk-fähig machen → `WHAT == "SERVICE"` und `NOTIFICATIONTYPE == "BULK"` unterscheiden
- MKP-Packung → sehr empfohlen (siehe `mkp create`, `mkp find`)

### 6. Wo weitere Beispiele & Inspiration finden?

- Offizielles Repo: `notifications/` Verzeichnis (z. B. `mail.py`, `ascii_mail.py`)
- Community-Repos (suche GitHub nach „checkmk notification”):
  - SIGNL4
  - Matrix
  - Telegram
  - ntfy.sh
  - Teams (mehrere Varianten)
- YouTube → „Checkmk Conference notification plugin” (Ron Czachara – SIGNL4 Session 2024/25)

---

## CMK 2.5 – Breaking Changes & Migration

### 1. Neue `NotificationPlugin`-API (empfohlen ab 2.5)

CMK 2.5 führt eine neue deklarative API für Notification-Plugins ein, analog zu den anderen Plugin-Typen. Das alte Script-Format (`~/local/share/check_mk/notifications/`) funktioniert weiterhin, die neue API ist aber der empfohlene Weg für neue Plugins.

```python
# CMK 2.5 – neue NotificationPlugin-API
# Datei: ~/local/lib/python3/cmk_addons/plugins/<name>/notification_scripts/<name>.py

from cmk.notification_plugins.v1 import (
    NotificationPlugin,
    NotificationContext,
    notification_plugin_registry,
)

def notify(context: NotificationContext) -> int:
    “””
    context enthält alle Notification-Variablen als typisiertes Objekt.
    Rückgabe: 0 = Erfolg, 2 = Fehler
    “””
    hostname = context.host_name
    service  = context.service_description or “”
    state    = context.service_state or context.host_state
    output   = context.service_output or context.host_output

    # Deine Benachrichtigungs-Logik hier
    # z. B. Teams-Webhook, Telegram, etc.

    return 0


notification_plugin_registry.register(
    NotificationPlugin(
        name=”my_notifier”,
        notify_function=notify,
    )
)
```

### 2. Altes Script-Format bleibt gültig

Das klassische Script-Format (`utils.collect_context()`) funktioniert in CMK 2.5 **unverändert weiter**. Bestehende Notification-Scripts müssen nicht migriert werden.

```text
Pfad weiterhin gültig:
~/local/share/check_mk/notifications/my_script.py
```

### 3. Edition-Umbenennung beachten

| CMK 2.4 Edition | CMK 2.5 Edition |
|---|---|
| CEE (Commercial Edition) | **Pro** |
| CCE (Cloud Edition) | **Ultimate** |
| CME (Managed Services Edition) | **Ultimate MT** |
| CRE (Raw Edition) | CRE (unverändert) |

Notification-Plugins mit UI-Parametern (`IndividualOrStoredPassword`, `Valuespec`) benötigen weiterhin mindestens die **Pro**-Edition (früher CEE).

### 4. `IndividualOrStoredPassword` → `cmk.rulesets.v1` in 2.5

Wenn ein Notification-Plugin UI-Parameter mit Passwort-Feldern definiert, empfiehlt sich in 2.5 die neue Rulesets-API:

```python
# CMK 2.4 (Valuespec – weiterhin funktionsfähig):
from cmk.gui.valuespec import Dictionary, HTTPUrl, IndividualOrStoredPassword

# CMK 2.5 (neue Rulesets-API – empfohlen):
from cmk.rulesets.v1.form_specs import Dictionary, DictElement, String, Password
from cmk.rulesets.v1 import Title
```

### 5. MKP-Pfad für neue 2.5-Notification-Plugins

```text
CMK 2.5 MKP-Struktur:
cmk_addons/plugins/<pluginname>/
└── notification_scripts/
    └── my_notifier.py
```

### Schnell-Checkliste Migration 2.4 → 2.5

- [ ] Bestehende Scripts unter `notifications/`: keine Änderung nötig
- [ ] Neue Plugins: `NotificationPlugin`-API aus `cmk.notification_plugins.v1` verwenden
- [ ] UI-Parameter: Valuespec bleibt gültig; für neue Plugins `cmk.rulesets.v1` bevorzugen
- [ ] Editionsbezeichnungen in Dokumentation: CEE → Pro, CCE → Ultimate
- [ ] MKP: `version.min_required` auf `”2.5.0p1”` setzen

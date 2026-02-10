
# SNMP-basierte Checks entwickeln – Guideline & Template  
**(Checkmk 2.3+ / 2.4 – Stand Februar 2026)**

Dieses Dokument ist eine praxisorientierte Anleitung, um **moderne, saubere SNMP-Checks** nach der **agent-based API** zu schreiben.  
Es enthält das aktuelle Minimal-Template, Best Practices, häufige Stolpersteine und ein vollständiges kleines Beispiel.

## 1. Warum dieses Template?

Das hier gezeigte Muster entspricht dem Stand 2024–2026 und wird von fast allen aktuellen SNMP-Checks in Checkmk (und in der Community) so oder sehr ähnlich verwendet.

**Vorteile gegenüber älteren Ansätzen:**

- saubere Trennung: Parser → Discovery → Check
- get_rate() korrekt genutzt (keine manuellen Zeitstempel mehr)
- robust gegen fehlende OIDs / unvollständige Tabellen
- MKP-fähig & update-sicher
- leicht erweiterbar (Metriken, Schwellwerte, Multi-Item)

## 2. Datei-Ort & Namenskonvention

```text
~/local/lib/python3/cmk/gui/plugins/agent_based/
   └── mein_snmp_check.py
```

**Empfohlener Dateiname-Schema:**

- `snmp_<hersteller>_<funktion>.py`    → z. B. `snmp_cisco_cpu.py`, `snmp_extreme_poe.py`
- `snmp_<mib-name>.py`                 → z. B. `snmp_if64.py`, `snmp_entity.py`
- Für sehr spezifische Checks: `snmp_<hersteller>_<modell>_<funktion>.py`

## 3. Vollständiges Minimal-Template (2024–2026 Standard)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SNMP Check: Mein Gerät – Beispiel-Template
"""

from cmk.agent_based.v1 import (
    register,
    SNMPTree,
    contains,
    Service,
    Result,
    State,
    Metric,
    render,
    get_rate,
    GetRateError,
)


# ────────────────────────────────────────────────
# 1. PARSER – Rohdaten in sauberes Dictionary umwandeln
# ────────────────────────────────────────────────
def parse_my_device_stats(string_table):
    """
    string_table ist eine Liste von Listen (Zeilen aus dem SNMP-Walk).
    Wir mappen sie in ein {item → daten}-Dictionary.
    """
    parsed = {}
    for line in string_table:
        if len(line) < 3:
            continue
        item, value_str, counter_str = line
        try:
            parsed[item.strip()] = {
                "value": float(value_str),
                "counter": int(counter_str),
            }
        except (ValueError, TypeError):
            continue  # ungültige Zeile ignorieren
    return parsed


# ────────────────────────────────────────────────
# 2. DISCOVERY – Services erzeugen
# ────────────────────────────────────────────────
def discover_my_device_stats(section):
    """
    Für jedes Item im geparsten Dictionary einen Service anlegen.
    """
    for item in section:
        yield Service(item=item)


# ────────────────────────────────────────────────
# 3. CHECK – eigentliche Logik
# ────────────────────────────────────────────────
def check_my_device_stats(item, params, section):
    """
    params: Dictionary mit Schwellwerten aus der Regel (z. B. {"levels": (80, 90)})
    section: das geparste Dictionary vom Parser
    """
    data = section.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary="No data received")
        return

    # A) Absoluter Wert (Gauge) mit Schwellwerten
    value = data["value"]
    warn, crit = params.get("levels", (None, None))

    if crit is not None and value >= crit:
        state = State.CRIT
    elif warn is not None and value >= warn:
        state = State.WARN
    else:
        state = State.OK

    yield Result(
        state=state,
        summary=f"Value: {render.percent(value)}",
    )
    yield Metric("usage_percent", value, levels=(warn, crit))


    # B) Rate-Berechnung (z. B. Fehler pro Sekunde)
    try:
        # Wichtig: eindeutiger Cache-Key pro Host + Item
        rate = get_rate(
            section_name="my_device_stats",
            key=f"{item}_counter",
            this_time=time.time(),
            this_val=data["counter"],
        )
        yield Result(state=State.OK, summary=f"Rate: {rate:.2f}/s")
        yield Metric("error_rate", rate, levels=params.get("rate_levels"))
    except GetRateError:
        # Beim ersten Check fehlt noch der Referenzwert → OK, aber kein Wert
        yield Result(state=State.OK, summary="Rate calculation initializing...")


# ────────────────────────────────────────────────
# 4. SNMP SECTION – Welche OIDs holen wir?
# ────────────────────────────────────────────────
register.snmp_section(
    name="my_device_stats",
    parse_function=parse_my_device_stats,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12345.1.2.3",           # Beispiel Enterprise-OID
        oids=[
            "1",   # Spalte 1 → Item-Name / Index
            "2",   # Spalte 2 → Gauge-Wert (z. B. CPU %)
            "3",   # Spalte 3 → Counter (z. B. Fehler seit Boot)
        ],
    ),
    detect=contains(".1.3.6.1.2.1.1.1.0", "MyDevice"),  # sysDescr-Check
)


# ────────────────────────────────────────────────
# 5. CHECK PLUGIN – Verknüpfung Discovery + Check
# ────────────────────────────────────────────────
register.check_plugin(
    name="my_device_stats",
    service_name="Device Stats %s",
    discovery_function=discover_my_device_stats,
    check_function=check_my_device_stats,
    check_default_parameters={"levels": (80.0, 90.0)},  # Default-Schwellwerte
    check_ruleset_name="my_device_stats_levels",        # Verweis auf WATO-Regel
)
```

## 4. Schnell-Übersicht: Wichtigste Funktionen

| Funktion / Konzept           | Bedeutung                                                                 | Häufiger Fehler |
|------------------------------|---------------------------------------------------------------------------|-----------------|
| `parse_…(string_table)`      | Wandelt SNMP-Tabelle in Python-Dict um                                    | Zu wenig Fehlerbehandlung |
| `discover_…(section)`        | Erzeugt Services (meist `yield Service(item=…)`)                         | Keine Filterung |
| `check_…(item, params, section)` | Kern-Logik: Zustand + Metriken berechnen                               | `get_rate` falscher Key |
| `get_rate(…)`                | Berechnet pro-Sekunde-Rate (benötigt eindeutigen Cache-Key)              | Key nicht item-spezifisch |
| `register.snmp_section`      | Definiert OIDs + Detection + Parser                                       | Falsche Base-OID |
| `register.check_plugin`      | Verknüpft Namen, Discovery & Check                                        | `name=` ohne Präfix |
| `Metric(…)`                  | Erzeugt PNP4Nagios-kompatible Metrik                                      | Keine `levels=` |

## 5. Erweitertes Beispiel – mit Schwellwert-Regel (WATO)

**Datei:** `rulesets/my_device_stats_levels.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    Dictionary,
    DictElement,
    Float,
    DefaultValue,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

def _parameter_valuespec_my_device_stats():
    return Dictionary(
        title=Title("My Device Stats Thresholds"),
        elements={
            "levels": DictElement(
                parameter_form=Float(
                    title=Title("Usage levels (percent)"),
                    prefill=DefaultValue((80.0, 90.0)),
                ),
            ),
            "rate_levels": DictElement(
                parameter_form=Float(
                    title=Title("Rate warning/critical (per second)"),
                    prefill=DefaultValue((5.0, 10.0)),
                ),
            ),
        },
    )

rule_spec_my_device_stats_levels = CheckParameters(
    name="my_device_stats_levels",
    title=Title("My Device Stats Levels"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_valuespec_my_device_stats,
    condition=HostAndItemCondition(item_title=Title("Statistic")),
)
```

## 6. Best Practices & häufige Fehler (2026)

| #  | Empfehlung / Fehler vermeiden                                                                 | Warum wichtig? |
|----|-----------------------------------------------------------------------------------------------|----------------|
| 1  | Immer `if not data:` oder `if item not in section` prüfen                                    | Verhindert KeyError bei fehlenden OIDs |
| 2  | `get_rate`-Key **immer** item-spezifisch machen: `f"{check_name}.{item}.counter"`            | Sonst Rate-Fehler bei Multi-Item-Checks |
| 3  | Detection mit `contains(…)` oder `all_of(…)` statt nur OID-Existenz                          | Verhindert Fehlalarme auf falschen Geräten |
| 4  | Metriken-Namen sprechend & konsistent: `usage_percent`, `errors_rate`, `clients_count`       | Bessere Graphen & PNP4Nagios |
| 5  | `render.percent()`, `render.bytes()` etc. im Summary nutzen                                  | Automatische Einheiten in GUI |
| 6  | Default-Parameter sinnvoll setzen (`check_default_parameters=…`)                             | Neugeräte funktionieren sofort |
| 7  | Ruleset-Name mit Präfix: `my_device_stats_levels` (nicht nur `device_stats_levels`)          | Verhindert Namenskonflikte |

## 7. Schnell-Start-Checkliste

1. Datei in `agent_based/` ablegen
2. `omd reload apache` oder `cmk -R`
3. Host mit SNMPv2/3 konfigurieren
4. Service Discovery (`cmk -I hostname`)
5. Prüfen: `cmk -n hostname | grep mein_snmp_check`


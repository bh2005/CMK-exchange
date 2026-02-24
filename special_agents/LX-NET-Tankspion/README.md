# Tank-Spion LX-NET – CheckMK 2.4 Plugin

Überwacht den Öltank-Füllstand von **TECSON Tank-Spion LX-NET** und **LX-Q-NET** Geräten über deren HTTP-Webinterface.

Das Plugin läuft als **Special Agent** direkt auf dem CheckMK-Server — es wird kein zusätzlicher Agent auf dem Gerät benötigt.

---

## Unterstützte Geräte

| Modell | Tanks | Getestet |
|--------|-------|----------|
| Tank-Spion LX-NET | 1 | ✓ |
| Tank-Spion Quadro LX-Q-NET | bis 4 | ✓ |

---

## Voraussetzungen

- CheckMK 2.4.x (Raw, Standard, Enterprise oder Cloud)
- Tank-Spion LX-NET / LX-Q-NET mit aktiviertem Webinterface (Port 80)
- Netzwerkverbindung vom CheckMK-Server zum Tank-Spion

---

## Dateistruktur

```
lib/python3/cmk_addons/plugins/tank_spion/
├── libexec/
│   └── agent_tank_spion          # Special Agent – HTTP-Abruf (läuft auf CMK-Server)
├── agent_based/
│   └── tank_spion.py             # Parse-Funktion + Discovery + Check-Logik
├── server_side_calls/
│   └── tank_spion_cmc.py         # Verbindet Ruleset → Agent-Kommando
└── rulesets/
    └── tank_spion_rule.py        # GUI-Rulesets (Special Agent + Schwellwerte)
```

---

## Installation

### Per MKP (empfohlen)

```bash
# Als Site-User:
mkp install tank_spion_complete.zip

# Apache neu laden damit Rulesets sichtbar werden:
omd reload apache
```

### Manuell

```bash
PLUGIN_DIR=~/local/lib/python3/cmk_addons/plugins/tank_spion

mkdir -p $PLUGIN_DIR/{libexec,agent_based,server_side_calls,rulesets}

cp agent_tank_spion        $PLUGIN_DIR/libexec/
cp tank_spion.py           $PLUGIN_DIR/agent_based/
cp tank_spion_cmc.py       $PLUGIN_DIR/server_side_calls/
cp tank_spion_rule.py      $PLUGIN_DIR/rulesets/

chmod +x $PLUGIN_DIR/libexec/agent_tank_spion

omd reload apache
```

---

## Konfiguration in CheckMK

### Schritt 1 – Host anlegen

Den Tank-Spion als Host in CheckMK eintragen. Die **IP-Adresse** des Geräts wird direkt als Zieladresse für den HTTP-Abruf verwendet.

```
Setup → Hosts → Add host
  Hostname:   tankspion-keller
  IP-Adresse: 192.168.1.50
```

> **Tipp:** "No IP" oder "SNMP only" deaktivieren — das Gerät wird per HTTP abgefragt.

---

### Schritt 2 – Special Agent aktivieren

```
Setup → Agents → VM, cloud, container
  → Suche: "Tank-Spion"
  → Regel hinzufügen
  → Condition: Hosts → tankspion-keller
  → Speichern
```

Damit weiß CheckMK, dass es für diesen Host den Special Agent `agent_tank_spion` aufrufen soll statt eines normalen CMK-Agents.

---

### Schritt 3 – Service Discovery

```
Setup → Hosts → tankspion-keller → Service Discovery
```

CheckMK findet automatisch einen Service pro Tank:

```
Tank Fuellstand 1    OK    67.4% – 2345 L von 3480 L
Tank Fuellstand 2    OK    44.5% – 890 L von 2000 L
```

---

### Schritt 4 – Schwellwerte konfigurieren (optional)

Standardmäßig gilt: **WARN ≤ 40%**, **CRIT ≤ 25%**.

Für individuelle Schwellwerte pro Tank:

```
Setup → Service Monitoring Rules
  → Suche: "Tank-Spion LX-NET Füllstand"
  → Regel hinzufügen
```

**Beispiel: Tank 1 mit strengeren Schwellen**
```
Condition:
  Hosts:    tankspion-keller
  Services: Tank Fuellstand 1

Parameter:
  Warning bei Restfüllstand ≤:   50 %
  Critical bei Restfüllstand ≤:  30 %
  Umrechnungsfaktor Liter → kg:  0.84   (Heizöl)
```

**Beispiel: Diesel-Tank mit kg-Anzeige**
```
Parameter:
  Warning:              35 %
  Critical:             20 %
  Umrechnung Liter→kg:  0.82   (Diesel ≈ 0.82 kg/L)
```

Mit aktivierter Umrechnung erscheint in der Service-Ausgabe zusätzlich:
```
Tank Fuellstand 1    OK    67.4% – 2345 L von 3480 L (1970.3 kg von 2923.2 kg)
```

---

## Service-Ausgabe

### Normaler Betrieb (OK)

```
Tank Fuellstand 1    OK
  Summary: 67.4% – 2345 L von 3480 L
  Details:  Warning ≤ 40.0%,  Critical ≤ 25.0%
```

### Füllstand niedrig (WARN)

```
Tank Fuellstand 1    WARN
  Summary: 32.1% – 1117 L von 3480 L
```

### Füllstand kritisch (CRIT)

```
Tank Fuellstand 1    CRIT
  Summary: 18.5% – 644 L von 3480 L
```

---

## Performance-Daten (Graphen)

Pro Tank werden folgende Metriken geliefert:

| Metrik | Bedeutung | Einheit |
|--------|-----------|---------|
| `fuellstand_l` | Aktueller Bestand | Liter |
| `fuellstand_perc` | Füllstand in Prozent | % |
| `tanksize_l` | Tankgröße | Liter |
| `fuellstand_kg` | Bestand in kg *(nur mit Umrechnung)* | kg |
| `tanksize_kg` | Tankgröße in kg *(nur mit Umrechnung)* | kg |

---

## Manueller Test

### Agent-Output prüfen (ohne CheckMK)

```bash
# Als Site-User:
~/local/lib/python3/cmk_addons/plugins/tank_spion/libexec/agent_tank_spion \
    --host 192.168.1.50

# Erwartete Ausgabe:
<<<tank_spion:sep(32)>>>
1 2345 3480
2 890 2000
```

### Via CheckMK

```bash
# Agent-Daten abrufen wie CheckMK es tut:
cmk -d tankspion-keller | grep -A5 "tank_spion"

# Service-Check simulieren:
cmk -nv tankspion-keller

# Nur Discovery testen:
cmk -vI --detect-plugins=tank_spion tankspion-keller
```

---

## Troubleshooting

### Keine Services gefunden nach Discovery

**Ursache 1:** Special Agent Regel fehlt oder greift nicht.
```bash
# Prüfen ob der Agent aufgerufen wird:
cmk -d tankspion-keller
# → muss <<<tank_spion>>> Section enthalten
```

**Ursache 2:** HTTP-Verbindung schlägt fehl.
```bash
# Webinterface direkt testen:
curl -s http://192.168.1.50 | grep -o '[0-9.]* L</td>'
# → sollte Liter-Werte ausgeben
```

**Ursache 3:** Apache nicht neu geladen nach Installation.
```bash
omd reload apache
```

---

### Service zeigt UNKNOWN – "nicht in Agent-Daten gefunden"

Der Tank-Spion hat weniger Tanks als erwartet, oder die HTML-Struktur weicht ab. Agent-Output prüfen:

```bash
~/local/lib/python3/cmk_addons/plugins/tank_spion/libexec/agent_tank_spion \
    --host 192.168.1.50
```

---

### Verbindungstimeout

Standard-Timeout: **10 Sekunden**. Wenn das Gerät langsam antwortet:
```bash
# Erreichbarkeit prüfen:
ping 192.168.1.50
curl -v --max-time 15 http://192.168.1.50
```

---

## Architektur

```
Tank-Spion LX-NET Gerät
        │  HTTP Port 80
        ▼
libexec/agent_tank_spion          ← läuft auf CMK-Server, HTTP-Abruf
        │  stdout: <<<tank_spion:sep(32)>>>
        │          1 2345 3480
        │          2 890 2000
        ▼
agent_based/tank_spion.py
  ├── parse_tank_spion()           ← Text → dict{tank_nr: (bestand, größe)}
  ├── discover_tank_spion()        ← 1 Service pro Tank-Nummer
  └── check_tank_spion()          ← Füllstand prüfen, Metriken ausgeben
        │
        │  Schwellwerte pro Tank (Item)
        ▼
rulesets/tank_spion_rule.py
  ├── rule_spec_tank_spion_datasource   → SpecialAgent (aktiviert den Agenten)
  └── rule_spec_tank_spion              → CheckParameters (warn/crit/kg pro Tank)
        ▲
server_side_calls/tank_spion_cmc.py
  └── special_agent_tank_spion    ← übersetzt Ruleset → CLI-Aufruf des Agents
```

---

## Changelog

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.0.0 | 2026-02-24 | Initiale Version für CheckMK 2.4 (Special Agent, rulesets.v1, agent_based.v2) |

---

## Lizenz

GNU General Public License v2
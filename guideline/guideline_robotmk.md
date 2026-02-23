# Synthetic Monitoring mit Robotmk - Web Portal Ueberwachung
## Checkmk 2.4 CEE | Linux Agent | Robot Framework Browser Library

---

## Inhaltsverzeichnis

1. [Architektur und Voraussetzungen](#1-architektur-und-voraussetzungen)
2. [Linux Test-Host vorbereiten](#2-linux-test-host-vorbereiten)
3. [Robot Framework Projekt anlegen](#3-robot-framework-projekt-anlegen)
4. [Test Suites schreiben](#4-test-suites-schreiben)
5. [Checkmk Agent und Bakery konfigurieren](#5-checkmk-agent-und-bakery-konfigurieren)
6. [Robotmk Scheduler Regel anlegen](#6-robotmk-scheduler-regel-anlegen)
7. [Services discovern und konfigurieren](#7-services-discovern-und-konfigurieren)
8. [Schwellwerte und Alarme](#8-schwellwerte-und-alarme)
9. [KPI Monitoring (Keywords)](#9-kpi-monitoring-keywords)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Architektur und Voraussetzungen

### Wie Robotmk funktioniert

```
+------------------+        Agent Output        +------------------+
|  Checkmk 2.4 CEE |<---------------------------|  Linux Test-Host |
|                  |                            |                  |
|  Bakery Rule     |------ Agent Paket -------->|  CMK Agent       |
|  Scheduler Rule  |                            |  RMK Scheduler   |
|  Plan/Test Rules |                            |  RCC             |
|                  |                            |  Robot Framework |
|  Services:       |                            |  Playwright      |
|  - RMK Scheduler |                            |                  |
|  - RMK Plan      |        Browser             |                  |
|  - RMK Test      |                            +-------+----------+
+------------------+                                    |
                                                        v
                                              +------------------+
                                              |   Web Portal     |
                                              |  (zu ueberwachen)|
                                              +------------------+
```

### Komponenten

| Komponente | Rolle |
|---|---|
| **Checkmk 2.4 CEE** | Konfiguration, Auswertung, Alerting |
| **Robotmk Scheduler** | Wird per Bakery auf dem Linux-Host deployed, fuehrt Plans aus |
| **RCC** | Baut isolierte Python-Umgebungen (kein manuelles pip install noetig) |
| **Robot Framework** | Fuehrt die `.robot` Test-Suites aus |
| **Browser Library** | Playwright-basiert, steuert Chromium/Firefox headless |

### Voraussetzungen

**Checkmk Server:**
- Checkmk 2.4 CEE mit aktivierter Synthetic Monitoring Subscription
  (bis 3 Test-Services kostenlos und zeitlich unbegrenzt testbar)
- Agent Bakery aktiviert (CEE-Feature)

**Linux Test-Host:**
- Debian 13 (Pflicht fuer Playwright/Browser Library! Debian 12/13 und Ubuntu 22.04/24.04)
- Mindestens 2 CPU-Kerne, 4 GB RAM empfohlen
- Internetzugang fuer RCC Environment-Build (oder offline via RCC holotree)
- Checkmk Linux Agent installiert

> **Wichtig:** Die Robot Framework Browser Library basiert auf Playwright.
> Playwright wird von Checkmk/RCC nur auf Debian 12/13 und Ubuntu 22.04/24.04
> unterstuetzt. CentOS/RHEL/SLES sind fuer Browser-Tests nicht geeignet.
> Hinweis Debian 13: Das Paket `libasound2` wurde in `libasound2t64` umbenannt
> (bereits in Schritt 2.1 beruecksichtigt).

---

## 2. Linux Test-Host vorbereiten

### 2.1 Systemabhangigkeiten installieren

```bash
# Debian 13 (Trixie)
sudo apt-get update
sudo apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2t64
```

> RCC installiert Python, Node.js und Playwright selbst in einem isolierten
> Environment. Die obigen Pakete sind System-Libraries die Playwright benoetigt.

### 2.2 Checkmk Agent installieren

Den Agent aus der Bakery herunterladen und installieren:

```bash
# Agent von Checkmk Server holen (URL anpassen)
# Debian 13 verwendet das .deb Paket (amd64)
wget https://<CMK-SERVER>/<SITE>/check_mk/agents/check-mk-agent_2.4.0-1_amd64.deb

sudo dpkg -i check-mk-agent_2.4.0-1_amd64.deb
```

### 2.3 Basisverzeichnis fuer Robot Suites anlegen

```bash
# Standardpfad fuer Robot Framework Projekte auf Linux
sudo mkdir -p /opt/robots
sudo chown cmk-agent:cmk-agent /opt/robots

# Verzeichnisstruktur (ein Unterordner pro Suite/Plan)
/opt/robots/
    webportal/
        robot.yaml
        conda.yaml
        tests/
            01_login.robot
            02_performance.robot
            03_content.robot
```

---

## 3. Robot Framework Projekt anlegen

Ein RCC Automation Package besteht aus drei Kerndateien.

### 3.1 `robot.yaml` - Paket-Konfiguration

```yaml
# /opt/robots/webportal/robot.yaml
tasks:
  Web Portal Tests:
    command:
      - python
      - -m
      - robot
      - --outputdir
      - output
      - tests/

artifactsDir: output

condaConfigFile: conda.yaml
```

### 3.2 `conda.yaml` - Python-Umgebung

```yaml
# /opt/robots/webportal/conda.yaml
channels:
  - conda-forge

dependencies:
  - python=3.11
  - pip=23.2
  - nodejs=18
  - pip:
      - robotframework==7.0
      - robotframework-browser==18.0.0

rccEnabled: true
```

> Nach dem ersten Deployment baut RCC das Environment automatisch.
> Das dauert beim ersten Mal ca. 5-10 Minuten (Playwright-Browser-Download).
> Danach wird der gecachte Build wiederverwendet.

### 3.3 Verzeichnisstruktur auf dem Host anlegen

```bash
mkdir -p /opt/robots/webportal/tests
mkdir -p /opt/robots/webportal/output

# Konfigurationsdateien anlegen (Inhalt aus Schritt 3.1 und 3.2)
nano /opt/robots/webportal/robot.yaml
nano /opt/robots/webportal/conda.yaml
```

---

## 4. Test Suites schreiben

### 4.1 Login / Authentifizierung

```robotframework
# /opt/robots/webportal/tests/01_login.robot
*** Settings ***
Library     Browser
Library     OperatingSystem

Suite Setup     New Browser    chromium    headless=True
Suite Teardown  Close Browser

*** Variables ***
${PORTAL_URL}       https://portal.example.com
${LOGIN_USER}       monitor_user
${LOGIN_PASS}       %{PORTAL_PASSWORD}    # aus Umgebungsvariable
${TIMEOUT}          10s

*** Test Cases ***
Login Page Erreichbar
    [Documentation]    Prueft ob die Login-Seite geladen wird
    New Page            ${PORTAL_URL}/login
    Wait For Elements State    css=form    visible    timeout=${TIMEOUT}
    Get Title           contains    Portal

Login Mit Gueltigen Zugangsdaten
    [Documentation]    Prueft erfolgreichen Login
    New Page            ${PORTAL_URL}/login
    Fill Text           id=username    ${LOGIN_USER}
    Fill Text           id=password    ${LOGIN_PASS}
    Click               css=button[type=submit]
    Wait For URL        ${PORTAL_URL}/dashboard    timeout=${TIMEOUT}
    Get Text            css=.user-info    contains    ${LOGIN_USER}

Login Mit Falschen Zugangsdaten
    [Documentation]    Prueft korrekte Fehlerbehandlung
    New Page            ${PORTAL_URL}/login
    Fill Text           id=username    wrong_user
    Fill Text           id=password    wrong_pass
    Click               css=button[type=submit]
    Wait For Elements State    css=.error-message    visible    timeout=${TIMEOUT}

Logout Funktioniert
    [Documentation]    Prueft den Logout-Prozess
    New Page            ${PORTAL_URL}/login
    Fill Text           id=username    ${LOGIN_USER}
    Fill Text           id=password    ${LOGIN_PASS}
    Click               css=button[type=submit]
    Wait For URL        ${PORTAL_URL}/dashboard    timeout=${TIMEOUT}
    Click               css=.logout-button
    Wait For URL        ${PORTAL_URL}/login    timeout=${TIMEOUT}
```

### 4.2 Seitenaufbau und Performance

```robotframework
# /opt/robots/webportal/tests/02_performance.robot
*** Settings ***
Library     Browser
Library     DateTime

Suite Setup     New Browser    chromium    headless=True
Suite Teardown  Close Browser

*** Variables ***
${PORTAL_URL}       https://portal.example.com
${MAX_LOAD_TIME}    3000    # Millisekunden

*** Test Cases ***
Startseite Ladezeit
    [Documentation]    Misst die Ladezeit der Startseite
    New Page            ${PORTAL_URL}
    ${metrics}=         Get Page Source
    # Navigationstiming via JavaScript
    ${timing}=          Evaluate JavaScript
    ...    None
    ...    () => JSON.stringify(window.performance.timing)
    Log                 ${timing}

Startseite Laedt Unter 3 Sekunden
    [Documentation]    Prueft ob Startseite schnell genug laedt
    ${start}=           Get Current Date    result_format=epoch
    New Page            ${PORTAL_URL}
    Wait For Load State    networkidle
    ${end}=             Get Current Date    result_format=epoch
    ${duration_ms}=     Evaluate    (${end} - ${start}) * 1000
    Should Be True      ${duration_ms} < ${MAX_LOAD_TIME}
    ...    Startseite brauchte ${duration_ms}ms (Limit: ${MAX_LOAD_TIME}ms)

Dashboard Nach Login Laedt
    [Documentation]    Prueft Ladezeit nach Authentifizierung
    New Page            ${PORTAL_URL}/login
    Fill Text           id=username    %{PORTAL_USER}
    Fill Text           id=password    %{PORTAL_PASSWORD}
    ${start}=           Get Current Date    result_format=epoch
    Click               css=button[type=submit]
    Wait For URL        ${PORTAL_URL}/dashboard
    Wait For Load State    networkidle
    ${end}=             Get Current Date    result_format=epoch
    ${duration_ms}=     Evaluate    (${end} - ${start}) * 1000
    Should Be True      ${duration_ms} < ${MAX_LOAD_TIME}
    ...    Dashboard-Load: ${duration_ms}ms (Limit: ${MAX_LOAD_TIME}ms)

Wichtige Seitenelemente Vorhanden
    [Documentation]    Prueft ob alle kritischen UI-Elemente geladen sind
    New Page            ${PORTAL_URL}/login
    Fill Text           id=username    %{PORTAL_USER}
    Fill Text           id=password    %{PORTAL_PASSWORD}
    Click               css=button[type=submit]
    Wait For URL        ${PORTAL_URL}/dashboard
    Wait For Elements State    css=.navigation    visible
    Wait For Elements State    css=.main-content   visible
    Wait For Elements State    css=.footer         visible
```

### 4.3 Content-Pruefung

```robotframework
# /opt/robots/webportal/tests/03_content.robot
*** Settings ***
Library     Browser
Library     String

Suite Setup     New Browser    chromium    headless=True    args=["--lang=de"]
Suite Teardown  Close Browser

*** Variables ***
${PORTAL_URL}       https://portal.example.com

*** Test Cases ***
Pflichtinhalte Startseite
    [Documentation]    Prueft ob kritische Inhalte auf der Startseite vorhanden sind
    New Page            ${PORTAL_URL}
    Wait For Load State    networkidle
    Get Text            css=body    contains    Willkommen
    Wait For Elements State    css=.logo       visible
    Wait For Elements State    css=nav         visible

Keine Javascript-Fehler
    [Documentation]    Prueft auf JS-Konsolenfehler
    New Page            ${PORTAL_URL}
    ${logs}=            Get Console Log
    FOR    ${log}    IN    @{logs}
        Should Not Contain    ${log}[type]    error
    END

SSL-Zertifikat Gueltig
    [Documentation]    Prueft ob Seite ohne SSL-Fehler erreichbar ist
    # Browser Library schlaegt bei SSL-Fehlern fehl (Playwright-Default)
    New Page            ${PORTAL_URL}
    Get Title           validate    len(value) > 0

Impressum Erreichbar
    [Documentation]    Prueft ob rechtlich notwendige Seiten erreichbar sind
    New Page            ${PORTAL_URL}/impressum
    Wait For Load State    networkidle
    Get Title           contains    Impressum

Datenschutz Erreichbar
    New Page            ${PORTAL_URL}/datenschutz
    Wait For Load State    networkidle
    Wait For Elements State    css=h1    visible
```

### 4.4 Credentials sicher verwalten

Passwort nie in `.robot`-Dateien! Stattdessen Umgebungsvariablen nutzen:

```bash
# Auf dem Linux Test-Host (als root oder cmk-agent)
# Datei wird vom Robotmk Scheduler geladen
cat > /etc/robotmk/secrets.env << EOF
PORTAL_USER=monitor_user
PORTAL_PASSWORD=geheimes_passwort
EOF

chmod 600 /etc/robotmk/secrets.env
chown cmk-agent:cmk-agent /etc/robotmk/secrets.env
```

Alternativ: Checkmk Password Store verwenden und in der Scheduler-Regel
als Umgebungsvariable uebergeben (empfohlen ab Checkmk 2.4).

---

## 5. Checkmk Agent und Bakery konfigurieren

### 5.1 Robotmk Scheduler Bakery Regel

In Checkmk:

```
Setup > Agents > Windows, Linux, Solaris, AIX > Agent rules
Suche: "Robotmk"
Oeffne: "Robotmk Scheduler (Linux)"
```

Klicke **"Add rule"** und konfiguriere:

| Parameter | Wert |
|---|---|
| **Execution interval** | 60-300 Sekunden je nach Testlaufzeit |
| **Base directory** | `/opt/robots` |
| **Grace period** | 30 Sekunden |

### 5.2 Plan konfigurieren

Unter "Plans" einen neuen Plan hinzufuegen:

| Parameter | Wert | Erklaerung |
|---|---|---|
| **Plan ID** | `webportal` | Eindeutiger Name, wird Teil des Service-Namens |
| **Suite path** | `webportal` | Relativ zum Base Directory |
| **Execution interval** | `300` | Alle 5 Minuten |
| **RCC profile** | `default` | Standard RCC Profil |
| **Timeout** | `120` | Maximale Laufzeit in Sekunden |

### 5.3 Agent Bakery backen und deployen

```
Setup > Agents > Agent Bakery
Klicke: "Bake and sign agents"
```

Danach den neuen Agenten auf dem Linux Test-Host einspielen:

```bash
# Automatisch via Agent Deployment (empfohlen)
# oder manuell:
wget https://<CMK-SERVER>/<SITE>/check_mk/agents/check-mk-agent_2.4.0-1_amd64.deb
sudo dpkg -i check-mk-agent_2.4.0-1_amd64.deb

# Scheduler-Status pruefen
sudo systemctl status cmk-robotmk-scheduler
```

---

## 6. Robotmk Scheduler Regel anlegen

### 6.1 Managed Robot (neu in 2.4)

Checkmk 2.4 CEE bietet "Managed Robots": Das Robot-Paket wird im Checkmk
Server hochgeladen und automatisch per Bakery auf den Test-Host verteilt.

```
Setup > Synthetic Monitoring > Managed Robots
Klicke: "Upload Robot"
```

ZIP-Archiv des Robot-Pakets hochladen:
```bash
cd /opt/robots
zip -r webportal.zip webportal/
```

Im Checkmk UI das ZIP hochladen und den Plan zuordnen.

### 6.2 Manuelle Verteilung (Alternative)

Das Robot-Paket direkt auf dem Test-Host ablegen (wie in Schritt 3 beschrieben).
In der Bakery-Regel dann "Use existing robot on host" auswaehlen.

---

## 7. Services discovern und konfigurieren

### 7.1 Service Discovery ausfuehren

```
Setup > Hosts > <Test-Host> > Run service discovery
```

Nach dem ersten Scheduler-Lauf erscheinen folgende Services:

| Service-Name | Beschreibung |
|---|---|
| `RMK Scheduler Status` | Gesamtstatus des Schedulers |
| `RMK webportal Plan` | Status des gesamten Plans |
| `RMK webportal Login Page Erreichbar` | Einzelner Test-Case |
| `RMK webportal Login Mit Gueltigen Zugangsdaten` | Einzelner Test-Case |
| `RMK webportal Startseite Laedt Unter 3 Sekunden` | Einzelner Test-Case |
| `RMK webportal Pflichtinhalte Startseite` | Einzelner Test-Case |
| ... | Alle weiteren Test-Cases |

### 7.2 Ersten Lauf manuell ausloesen

```bash
# Auf dem Test-Host (fuer schnelles Testen)
sudo systemctl restart cmk-robotmk-scheduler

# Logs verfolgen
sudo journalctl -fu cmk-robotmk-scheduler
```

### 7.3 Robot Framework Log abrufen

In der Checkmk UI auf einen RMK Test-Service klicken:
- Tab "Details" zeigt den Robot Framework HTML-Report eingebettet
- Vollstaendige Log-Details mit Screenshots bei Fehlern

---

## 8. Schwellwerte und Alarme

### 8.1 Plan-Laufzeit Schwellwerte

```
Setup > Services > Service monitoring rules
Suche: "Robotmk plan"
Oeffne: "Robotmk plan"
```

| Parameter | Empfehlung |
|---|---|
| **WARN if runtime exceeds** | 90 Sekunden |
| **CRIT if runtime exceeds** | 110 Sekunden |
| **WARN if last successful run** | 10 Minuten |
| **CRIT if last successful run** | 20 Minuten |

### 8.2 Test-Laufzeit Schwellwerte

```
Setup > Services > Service monitoring rules
Suche: "Robotmk test"
Oeffne: "Robotmk test"
```

Pro Test-Case konfigurierbar (per Item-Filter auf Service-Name):

| Test-Case | WARN | CRIT |
|---|---|---|
| Login Page Erreichbar | 2s | 5s |
| Startseite Laedt Unter 3 Sekunden | 3s | 6s |
| Login Mit Gueltigen Zugangsdaten | 5s | 10s |

### 8.3 Notifications konfigurieren

```
Setup > Events > Notifications
Neue Regel anlegen:
  - Match service labels: robotmk
  - Notify: Team Web / On-Call
  - Method: E-Mail / PagerDuty / Teams
```

---

## 9. KPI Monitoring (Keywords)

Mit KPI Monitoring koennen einzelne Robot Framework Keywords als eigene
Checkmk-Services erscheinen. Besonders nuetzlich fuer Performance-Metriken.

### 9.1 KPI Discovery Rule

```
Setup > Services > Service monitoring rules
Suche: "Robotmk KPI"
Oeffne: "Robotmk KPI discovery"
```

Konfiguriere welche Keywords als KPI-Services erscheinen sollen:

```
Plan: webportal
Test: Startseite Laedt Unter 3 Sekunden
Keyword: Should Be True    (das Keyword mit der Ladezeit-Pruefung)
```

### 9.2 KPI Schwellwerte

```
Setup > Services > Service monitoring rules
Suche: "Robotmk KPI monitoring"
```

Hier werden dann Laufzeit-Schwellwerte fuer einzelne Keywords gesetzt.

---

## 10. Troubleshooting

### Scheduler startet nicht

```bash
# Status pruefen
sudo systemctl status cmk-robotmk-scheduler

# Detailliertes Log
sudo journalctl -fu cmk-robotmk-scheduler --since "10 minutes ago"

# Konfiguration validieren
cat /etc/check_mk/robotmk_config.json
```

### RCC Environment Build schlaegt fehl

```bash
# RCC direkt testen (als cmk-agent User)
sudo -u cmk-agent /usr/lib/check_mk_agent/plugins/rcc \
    task run \
    --robot /opt/robots/webportal \
    --task "Web Portal Tests"

# Holograms (gecachte Environments) zuruecksetzen
sudo -u cmk-agent /usr/lib/check_mk_agent/plugins/rcc \
    holotree variables \
    --space webportal
```

### Playwright / Browser startet nicht

```bash
# Fehlende System-Libraries pruefen
ldd /home/cmk-agent/.rcc/holotree/.../playwright/chromium-*/chrome-linux/chrome \
    | grep "not found"

# Headless-Test manuell
sudo -u cmk-agent DISPLAY= \
    python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto('https://example.com')
    print(page.title())
    b.close()
"
```

### Services erscheinen nicht nach Discovery

```bash
# Agent Output pruefen
sudo cmk-agent-ctl dump | grep -A5 "robotmk"

# Auf dem CMK-Server
cmk -d <TEST-HOST> | grep -A5 "robotmk"

# Discovery manuell ausfuehren
cmk -I --detect-plugins=robotmk <TEST-HOST>
```

### Haeufige Fehlerquellen

| Problem | Ursache | Loesung |
|---|---|---|
| `UNKNOWN: Scheduler not yet run` | Scheduler noch nicht gelaufen | Warten oder `systemctl restart cmk-robotmk-scheduler` |
| `CRIT: Plan timeout` | Test-Laufzeit zu hoch | Timeout in Bakery-Regel erhoehen oder Tests optimieren |
| `Robot file not found` | Falscher Pfad in Bakery-Regel | Base Directory und Suite-Pfad pruefen |
| `RCC holotree build failed` | Kein Internetzugang | Proxy konfigurieren oder Offline-Holotree nutzen |
| `Browser launch failed` | Fehlende System-Libs | Schritt 2.1 wiederholen |
| `SSL certificate error` | Selbstsigniertes Zertifikat | `ignore_https_errors=True` in Browser Library oder CA einbinden |

---

## Referenzen

- [Checkmk Synthetic Monitoring Doku](https://docs.checkmk.com/latest/en/robotmk.html)
- [Robotmk Homepage & Blog](https://www.robotmk.org)
- [Robotmk Examples Repository](https://github.com/Checkmk/robotmk-examples)
- [Robot Framework Browser Library](https://robotframework-browser.org)
- [RCC Tool](https://github.com/robocorp/rcc)

---

*Author: bh2005 | License: GPL v2*
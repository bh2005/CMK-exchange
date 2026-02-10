# Checkmk Spool-Verzeichnis – Praxis-Guide 2026  
(2.2 / 2.3 / 2.4 – alle aktuellen Versionen)

Das Spool-Verzeichnis ist einer der mächtigsten und gleichzeitig unterschätzten Mechanismen in Checkmk, um beliebige Daten asynchron in die Agentenausgabe zu integrieren.

## 1. Was macht das Spool-Verzeichnis eigentlich?

Checkmk liest **regelmäßig** (alle 60 Sekunden standardmäßig) alle Dateien aus dem Spool-Verzeichnis ein und hängt deren Inhalt **direkt** an die normale Agentenausgabe an.

→ Du kannst damit:

- Daten von Skripten nachliefern, die länger als 10 Sekunden brauchen
- Daten von externen Systemen (z. B. API-Calls, Datenbanken, Dateien)
- sehr große oder sehr langsame Abfragen asynchron ausführen
- beliebige <<<section>>> Blöcke erzeugen (auch solche, die kein normaler Agent liefert)

## 2. Wo liegt das Spool-Verzeichnis?

**Auf dem überwachten Host** (nicht auf dem Checkmk-Server!):

```
/var/lib/check_mk_agent/spool/
```

**Wichtig:**  
Das Verzeichnis muss **existiert** haben und vom Agent-Benutzer (meist `root` oder `cmk`) beschreibbar sein.

```bash
# Auf dem überwachten Host ausführen
sudo mkdir -p /var/lib/check_mk_agent/spool
sudo chown root:root /var/lib/check_mk_agent/spool   # oder cmk:cmk, je nach Agent
sudo chmod 755 /var/lib/check_mk_agent/spool
```

## 3. Wie funktioniert es genau?

1. Du (oder ein Skript) legst eine Datei in `/var/lib/check_mk_agent/spool/` ab
2. Dateiname = **Section-Name** (mit oder ohne `.txt`, `.log`, etc.)
3. Inhalt = **reiner Agent-Output** (genau so, wie er aussehen würde, wenn er vom Agent käme)
4. Checkmk liest alle Dateien im Verzeichnis (sortiert nach Name)
5. Inhalt wird **am Ende** der normalen Agentenausgabe angehängt
6. Dateien werden **nicht** automatisch gelöscht → du musst das selbst regeln

**Wichtigste Regel:**  
Der Dateiname bestimmt den Section-Namen!

```text
Dateiname               → erscheint als
-------------------------
60_myscript             → <<<60_myscript>>>
mysql_status.txt        → <<<mysql_status>>>
backup_status           → <<<backup_status>>>
```

**60_ am Anfang** ist Konvention → bedeutet „maximale Lebensdauer 60 Sekunden“  
(Checkmk löscht Dateien nicht selbst – das muss dein Skript tun!)

## 4. Klassische Anwendungsfälle (mit Beispielen)

### Beispiel 1: Langsamer Backup-Status

```bash
# /usr/local/bin/spool_backup_status.sh
#!/bin/bash

# Backup-Status nachliefern (dauert 15 Sekunden)
STATUS=$(zfs list -t snapshot | wc -l)
AGE=$(find /backup/latest -mtime -1 | wc -l)

cat <<EOF > /var/lib/check_mk_agent/spool/300_backup_status
<<<backup_status:sep(124)>>>
snapshots|$STATUS
last_backup_age_days|$AGE
EOF

chmod 644 /var/lib/check_mk_agent/spool/300_backup_status
```

→ Section erscheint als `<<<backup_status>>>`  
→ Lebensdauer ~300 Sekunden (5 Minuten) → Dateiname mit 300_

### Beispiel 2: API-Daten nachliefern (z. B. Lizenz-Status)

```bash
# /usr/local/bin/spool_license_api.sh  (cron alle 15 Minuten)
#!/bin/bash

API_KEY="xyz"
URL="https://api.company.com/license/status"

JSON=$(curl -s -H "Authorization: Bearer $API_KEY" "$URL" --max-time 20)

if [[ $? -eq 0 ]]; then
    cat <<EOF > /var/lib/check_mk_agent/spool/900_license_api
<<<license_api:json>>>
$JSON
EOF
else
    echo "ERROR|curl failed" > /var/lib/check_mk_agent/spool/900_license_api
fi
```

→ Checkmk erhält `<<<license_api:json>>>` + JSON-Inhalt

### Beispiel 3: Temperatur von externem Sensor (1x pro Minute)

```bash
# /usr/local/bin/spool_temp_sensor.sh  (cron * * * * *)
#!/bin/bash

TEMP=$(cat /sys/bus/i2c/devices/1-0048/temp1_input)   # Beispiel: DS18B20 oder ähnlich
TEMP_C=$(echo "scale=1; $TEMP / 1000" | bc)

echo "temperature|$TEMP_C" > /var/lib/check_mk_agent/spool/60_temp_sensor
```

→ Section: `<<<temp_sensor>>>`  
→ Service-Discovery findet `temperature` als Item

## 5. Häufige Stolpersteine & Lösungen

| Problem                                                                 | Lösung / Tipp                                                                                   |
|-------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| Section erscheint nicht                                                 | Dateiname prüfen → muss exakt Section-Name sein (keine .py, .sh, etc. am Ende!)                 |
| Datei wird nicht gelesen                                                | Rechte: 644 oder 664, Owner root oder cmk-Agent-User                                            |
| Alter Inhalt bleibt ewig                                                | Dateiname mit Lebensdauer-Präfix (z. B. `300_`) + Skript löscht Datei nach Ablauf               |
| Mehrere Dateien gleicher Section → Chaos                                | Nur **eine** Datei pro Section-Name erlaubt – vorherige überschreiben                          |
| Zu große Datei → Agent-Timeout                                          | Dateigröße < 1–2 MB halten oder in mehrere Sections aufteilen                                  |
| Cron-Job läuft nicht                                                    | `sudo -u cmkagent crontab -e` oder System-Cron mit korrektem User                               |
| Windows-Agent                                                           | Spool-Ordner: `C:\ProgramData\checkmk\agent\spool\`                                             |

## 6. Best Practices 2026

1. **Immer Präfix mit Lebensdauer**  
   `60_` = 1 Minute, `300_` = 5 Minuten, `3600_` = 1 Stunde, `86400_` = 1 Tag

2. **Datei am Ende selbst löschen** (wenn nicht mehr benötigt)  
   ```bash
   rm -f /var/lib/check_mk_agent/spool/60_myscript
   ```

3. **Section-Name sprechend** wählen  
   Gut: `backup_status`, `license_api`, `ext_temp_sensor`  
   Schlecht: `script1`, `data`, `out`

4. **:sep(124)** oder **:json** immer angeben  
   → erleichtert Parsing enorm

5. **Fehler immer sichtbar machen**  
   ```text
   <<<my_section>>>
   status|ERROR message|Timeout after 20 seconds
   ```

6. **Kombination mit Piggyback** möglich  
   ```text
   <<<<remotehost>>>>
   <<<spooled_backup>>>
   status|OK
   <<<<>>>>
   ```

## 7. Schnell-Referenz: Lebensdauer-Präfixe (Konvention)

| Präfix | Bedeutung                | Typische Verwendung                     |
|--------|--------------------------|-----------------------------------------|
| 60_    | 1 Minute                 | Sensoren, Temperatur, schnelle Metriken |
| 300_   | 5 Minuten                | Backup-Status, Lizenz-Checks            |
| 600_   | 10 Minuten               | Log-Analyse, mittlere APIs              |
| 3600_  | 1 Stunde                 | Monatliche Reports, große APIs          |
| 86400_ | 1 Tag                    | Zertifikats-Ablauf, Hardware-Scan       |

## 8. Test-Workflow (in < 60 Sekunden)

```bash
# Auf dem überwachten Host
echo "test|42" | sudo tee /var/lib/check_mk_agent/spool/60_test

# Auf Checkmk-Server
cmk -d HOSTNAME | grep -A 5 "<<<60_test>>>"
```

→ Sollte zeigen:

```
<<<60_test>>>
test|42
```

Hier sind zwei **konkrete, sofort einsetzbare Beispiele** für das Spool-Verzeichnis in Checkmk:

1. Ein klassisches **Piggyback-Beispiel** (häufigste echte Anwendung)  
2. Ein **Log-Parser-Beispiel** (asynchrone Log-Auswertung)

Beide Beispiele sind so gestaltet, dass sie direkt kopiert und getestet werden können.

### 1. Beispiel: Piggyback über das Spool-Verzeichnis

**Ziel:**  
Ein zentraler Server fragt per API/Skript den Status von 3 Remote-Servern ab und liefert die Daten als Piggyback an Checkmk weiter.

**Datei auf dem zentralen Host (z. B. Cron-Job alle 5 Minuten):**

```bash
#!/bin/bash
# /usr/local/bin/spool_remote_servers.sh

SPOOL="/var/lib/check_mk_agent/spool"
LIFETIME=300   # 5 Minuten

# Beispiel-Daten von 3 Remote-Servern (in echt: curl, ssh, API, ...)
cat <<'EOF' > "$SPOOL/${LIFETIME}_remote_backup_status"
<<<<backupserver1>>>>
<<<local>>>
0 "Backup Status" - Last Backup OK - 42 GB - Age 3h
<<<<>>>>

<<<<websrv02>>>>
<<<local>>>
0 "Disk Space" - /var 78% used - 124 GB free
<<<<>>>>

<<<<dbsrv03>>>>
<<<local>>>
2 "Database Replication" - Lag 45 minutes - CRITICAL
<<<<>>>>
EOF

chmod 644 "$SPOOL/${LIFETIME}_remote_backup_status"
```

**Ergebnis in Checkmk (nach Discovery):**

- Auf dem Host, auf dem der Agent läuft → keine neuen Services
- Aber drei neue **Piggyback-Hosts** erscheinen automatisch:
  - `backupserver1`
  - `websrv02`
  - `dbsrv03`

Jeder dieser Hosts hat dann einen Service „Backup Status“, „Disk Space“ bzw. „Database Replication“.

**Wichtig:**  
Die Piggyback-Hosts müssen in Checkmk **existiert** haben oder als **Piggyback-Host** konfiguriert sein (Setup → Hosts → Piggyback).

### 2. Beispiel: Asynchroner Log-Parser (Logdatei → Checkmk-Service)

**Ziel:**  
Eine Logdatei wird alle 60 Sekunden ausgewertet (z. B. Error-Counter, letzte Fehlermeldung).  
Das Parsing dauert manchmal länger → deshalb über Spool asynchron.

**Schritt 1: Parser-Skript (Cron alle 60 Sekunden)**

```bash
#!/bin/bash
# /usr/local/bin/spool_log_parser.sh

SPOOL="/var/lib/check_mk_agent/spool"
LOGFILE="/var/log/myapp/error.log"
LIFETIME=120   # 2 Minuten Lebensdauer

# Fehler der letzten 5 Minuten zählen
ERROR_COUNT=$(tail -n 5000 "$LOGFILE" | grep -c "$(date -d '5 minutes ago' '+%b %d %H:%M')")

# Letzte Fehlermeldung (letzte Zeile mit ERROR)
LAST_ERROR=$(tail -n 100 "$LOGFILE" | grep -i "ERROR" | tail -n 1)

if [ -z "$LAST_ERROR" ]; then
    STATE=0
    SUMMARY="No errors in last 5 minutes"
else
    STATE=2
    SUMMARY="Last error: $LAST_ERROR"
fi

cat <<EOF > "$SPOOL/${LIFETIME}_log_errors"
<<<log_errors>>>
$STATE "Log Errors" - $SUMMARY - Count last 5 min: $ERROR_COUNT
EOF

chmod 644 "$SPOOL/${LIFETIME}_log_errors"
```

**Schritt 2: Cron-Eintrag** (damit es automatisch läuft)

```bash
# sudo crontab -e   oder   /etc/cron.d/spool_log_parser
* * * * *   /usr/local/bin/spool_log_parser.sh
```

**Ergebnis in Checkmk:**

Nach Service-Discovery erscheint auf dem Host ein Service:

```
Log Errors    OK   No errors in last 5 minutes - Count last 5 min: 0
```

Wenn Fehler auftreten → CRIT + Text der letzten Fehlermeldung.

**Noch besser – mit Schwellwerten (optional):**

Füge in Checkmk eine Regel hinzu:

- Setup → Services → Service monitoring rules → Logfile patterns / Logfile groups
- Oder eigenen Check via `check_logfiles` (MKP) nutzen

### 3. Zusammenfassung – Wann Spool statt normaler Agent-Sektion?

| Szenario                                   | Besser mit Spool? | Warum?                                      |
|--------------------------------------------|-------------------|---------------------------------------------|
| API-Abfrage dauert >10 Sekunden            | Ja                | Agent-Timeout vermeiden                     |
| Logdatei parsen (grep, awk, …) dauert      | Ja                | Agent bleibt schnell                        |
| Daten von Remote-Systemen (SSH, REST, …)   | Ja                | Zentraler Server kann alles abarbeiten      |
| Backup-Status, Lizenz-Check, Zertifikate   | Meistens Ja       | Oft nur 1× pro Stunde / Tag nötig           |
| Schnelle Metriken (CPU, RAM, Disk)         | Nein              | Normaler Agent ist schneller & einfacher    |

### 4. Schnell-Start-Checkliste

```bash
# Test auf dem überwachten Host
echo "0 \"Test Spool\" - Alles super" | sudo tee /var/lib/check_mk_agent/spool/60_test_spool

# Auf Checkmk-Server prüfen
cmk -d HOSTNAME | grep -A 5 "<<<60_test_spool>>>"

# Sollte zeigen:
<<<60_test_spool>>>
0 "Test Spool" - Alles super
```

Viel Erfolg beim Spoolen!  
Das Spool-Verzeichnis ist eines der mächtigsten und gleichzeitig einfachsten Erweiterungsmittel in Checkmk – besonders wenn du externe Skripte, APIs oder Logs einbinden möchtest, ohne den Haupt-Agenten zu blockieren.


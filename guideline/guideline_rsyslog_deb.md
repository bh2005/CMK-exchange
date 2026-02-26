# Rsyslog Server – Konfiguration & Betrieb unter Debian 13

**Dokumentation für Multi-Team-Umgebungen mit Security, Monitoring & SOC**  
*Erstellt: Februar 2026 | Version: 1.7 | BH2005*

---

## Inhaltsverzeichnis

1. [Einführung & Architektur](#1-einführung--architektur)
2. [Installation & Grundkonfiguration](#2-installation--grundkonfiguration)
3. [Konfigurationsstruktur](#3-konfigurationsstruktur)
4. [Multi-Team-Architektur](#4-multi-team-architektur)
5. [Verzeichnisstruktur & Berechtigungen](#5-verzeichnisstruktur--berechtigungen)
6. [Templates](#6-templates)
7. [Security Team – Konfiguration](#7-security-team--konfiguration)
8. [Monitoring Team – Konfiguration](#8-monitoring-team--konfiguration)
9. [SOC Team – Konfiguration](#9-soc-team--konfiguration)
10. [Check_MK Integration](#10-checkmk-integration)
11. [E-Mail Benachrichtigungen](#11-e-mail-benachrichtigungen)
12. [Zentrale Alert-Konfiguration](#12-zentrale-alert-konfiguration)
13. [Rate-Limiting](#13-rate-limiting)
14. [Log-Rotation](#14-log-rotation)
15. [TLS-Verschlüsselung](#15-tls-verschlüsselung)
16. [Severity-Level & Routing-Übersicht](#16-severity-level--routing-übersicht)
17. [Netzwerk- & IP-Übersicht](#17-netzwerk---ip-übersicht)
18. [Testing & Troubleshooting](#18-testing--troubleshooting)

---

## 1. Einführung & Architektur

Rsyslog ist ein leistungsstarker, erweiterbarer Syslog-Daemon, der unter Debian standardmäßig vorinstalliert ist. Er sammelt, filtert und leitet Logmeldungen von lokalen Diensten und entfernten Hosts weiter.

Diese Dokumentation beschreibt eine vollständige Unternehmenskonfiguration mit drei Teams und automatisierter Alarmierung.

### Gesamtarchitektur

```
                    ┌──────────────────────────────────────────────┐
                    │              RSYSLOG SERVER                   │
                    │                                              │
Firewall  ─────────►│  /var/log/security/   ──► Critical ──┐       │
F5 LB     ─────────►│  /var/log/monitoring/ ──► Critical ──┼──► Check_MK
Linux-Srv ─────────►│  /var/log/soc/        ──► Critical ──┘       │
                    │                                    │          │
                    │                                    └──► E-Mail, SMS, Call
                    └──────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              Security-Team  Monitoring-Team   SOC-Team
```

### Wichtige Module im Überblick

| Modul | Funktion |
|---|---|
| `imuxsock` | Lokale Unix-Sockets (Standard) |
| `imjournal` | Systemd-Journal einlesen |
| `imudp` | UDP-Empfang (Port 514, für ältere Geräte) |
| `imtcp` | TCP-Empfang mit optionalem TLS |
| `omfile` | In Dateien schreiben |
| `omfwd` | Weiterleitung an Remote-Host |
| `omprogram` | Externe Skripte/Programme aufrufen |
| `omsnmp` | SNMP-Traps senden |
| `ommysql` / `ompgsql` | In Datenbank schreiben |

---

## 2. Installation & Grundkonfiguration

### Installation

Rsyslog ist auf Debian in der Regel bereits vorinstalliert. Falls nicht:

```bash
apt install rsyslog rsyslog-gnutls -y
systemctl enable --now rsyslog
```

### Verzeichnisse der Konfiguration

| Pfad | Beschreibung |
|---|---|
| `/etc/rsyslog.conf` | Hauptkonfigurationsdatei |
| `/etc/rsyslog.d/*.conf` | Modulare Zusatzkonfigurationen |
| `/var/lib/rsyslog/` | Queue-Dateien & Zustandsdaten |
| `/var/log/` | Standard-Log-Verzeichnis |

### Hinweis zu Debian 13 (Trixie)

Debian 13 nutzt weiterhin Systemd als Init-System. Die Integration mit `imjournal` (Systemd-Journal → Rsyslog) ist besonders relevant. In manchen Setups empfiehlt es sich, `imuxsock` durch `imjournal` zu ersetzen, um doppelte Log-Einträge zu vermeiden.

---

## 3. Konfigurationsstruktur

### Grundprinzip

Rsyslog-Regeln folgen dem Muster: **Facility.Severity → Ziel**

```
*.info;mail.none;authpriv.none   /var/log/messages
auth,authpriv.*                  /var/log/auth.log
mail.*                           /var/log/mail.log
*.emerg                          :omusrmsg:*
```

### Severity-Levels

| Level | Nummer | Bedeutung |
|---|---|---|
<span style="color:red">| emerg | 0 | System ist nicht nutzbar |</span>
<span style="color:red">| alert | 1 | Sofortige Aktion erforderlich |</span>
<span style="color:red">| crit | 2 | Kritischer Zustand |</span>
<span style="color:yellow">| err | 3 | Fehler |</span>
| warning | 4 | Warnung |
| notice | 5 | Normaler, aber bedeutsamer Zustand |
| info | 6 | Informationsmeldung |
| debug | 7 | Debug-Meldung |

---

## 4. Multi-Team-Architektur

### Hauptkonfiguration `/etc/rsyslog.conf`

```
# ============================================================
# GLOBALE EINSTELLUNGEN
# ============================================================
global(
  workDirectory="/var/lib/rsyslog"
  maxMessageSize="64k"
  defaultNetstreamDriver="gtls"
  defaultNetstreamDriverCAFile="/etc/ssl/rsyslog/ca.pem"
  defaultNetstreamDriverCertFile="/etc/ssl/rsyslog/server-cert.pem"
  defaultNetstreamDriverKeyFile="/etc/ssl/rsyslog/server-key.pem"
)

# Module laden
module(load="imuxsock")
module(load="imjournal")
module(load="imtcp" StreamDriver.Name="gtls"
                    StreamDriver.Mode="1"
                    StreamDriver.Authmode="anon")
module(load="imudp")

# TCP mit TLS (bevorzugt)
input(type="imtcp" port="6514")
# UDP Fallback (für ältere Geräte wie Firewalls)
input(type="imudp" port="514")

# Modulare Konfigurationen laden
include(file="/etc/rsyslog.d/*.conf" mode="optional")
```

---

## 5. Verzeichnisstruktur & Berechtigungen

```bash
# Verzeichnisse anlegen
mkdir -p /var/log/security/{firewall,vpn,ids}
mkdir -p /var/log/monitoring/{server,f5,health}
mkdir -p /var/log/soc/{alerts,incidents,correlation}

# Berechtigungen pro Team
chown -R syslog:security   /var/log/security
chown -R syslog:monitoring /var/log/monitoring
chown -R syslog:soc        /var/log/soc

chmod 750 /var/log/security /var/log/monitoring /var/log/soc

# Firewall-Port freigeben
ufw allow 514/tcp
ufw allow 514/udp
ufw allow 6514/tcp
ufw allow 6515/tcp
```

### Client-Konfiguration

Auf den Client-Rechnern Logs an den Server weiterleiten:

```
# /etc/rsyslog.d/forward.conf
*.* @@192.168.1.10:6514    # @@ = TCP, @ = UDP
```

---

## 6. Templates

### `/etc/rsyslog.d/00-templates.conf`

```
# ============================================================
# TEMPLATES – Dateistruktur nach Hostname & Datum
# ============================================================

# Security Team – Firewall & VPN
template(name="t_security_firewall" type="string"
  string="/var/log/security/firewall/%$YEAR%-%$MONTH%/%HOSTNAME%.log")

template(name="t_security_vpn" type="string"
  string="/var/log/security/vpn/%$YEAR%-%$MONTH%/%HOSTNAME%.log")

template(name="t_security_ids" type="string"
  string="/var/log/security/ids/%$YEAR%-%$MONTH%/%HOSTNAME%.log")

# Monitoring Team – Server & F5
template(name="t_monitoring_server" type="string"
  string="/var/log/monitoring/server/%$YEAR%-%$MONTH%/%HOSTNAME%.log")

template(name="t_monitoring_f5" type="string"
  string="/var/log/monitoring/f5/%$YEAR%-%$MONTH%/%HOSTNAME%.log")

template(name="t_monitoring_health" type="string"
  string="/var/log/monitoring/health/%$YEAR%-%$MONTH%/%HOSTNAME%.log")

# SOC – Alerts & Incidents
template(name="t_soc_alerts" type="string"
  string="/var/log/soc/alerts/%$YEAR%-%$MONTH%/%HOSTNAME%.log")

template(name="t_soc_incidents" type="string"
  string="/var/log/soc/incidents/%$YEAR%-%$MONTH%/%HOSTNAME%.log")

# Einheitliches Log-Format (JSON für SIEM-Integration)
template(name="t_json_format" type="list") {
  constant(value="{")
  constant(value="\"timestamp\":\"")      property(name="timereported" dateFormat="rfc3339")
  constant(value="\",\"host\":\"")        property(name="hostname")
  constant(value="\",\"program\":\"")     property(name="programname")
  constant(value="\",\"severity\":\"")    property(name="syslogseverity-text")
  constant(value="\",\"facility\":\"")    property(name="syslogfacility-text")
  constant(value="\",\"message\":\"")     property(name="msg" format="json")
  constant(value="\"}\n")
}

# Template für Skript-Parameter (Hostname Severity Message)
template(name="t_alert_params" type="string"
  string="%HOSTNAME% %syslogseverity-text% %msg%\n")

# Check_MK RFC5424 Format
template(name="t_checkmk_forward" type="string"
  string="<%PRI%>1 %TIMESTAMP:::date-rfc3339% %HOSTNAME% %APP-NAME% %PROCID% - - %MSG%\n")
```

> **Hinweis:** Das JSON-Format erleichtert die Integration mit SIEM-Systemen wie Graylog, Splunk oder dem Elastic Stack erheblich.

---

## 7. Security Team – Konfiguration

### `/etc/rsyslog.d/10-security.conf`

```
# ============================================================
# SECURITY TEAM – Firewall, VPN, IDS
# Quellen: Firewalls (Fortinet, pfSense, Cisco ASA)
# ============================================================

ruleset(name="rs_security") {

  # Firewall-Logs (Facility local3 + local4)
  if ($syslogfacility-text == "local3") then {
    action(type="omfile" dynaFile="t_security_firewall"
           template="t_json_format"
           asyncWriting="on" flushOnTXEnd="off"
           ioBufferSize="64k")
    stop
  }

  # VPN-Logs
  if ($syslogfacility-text == "local4"
      or $programname contains "vpn"
      or $programname contains "openvpn"
      or $programname contains "strongswan") then {
    action(type="omfile" dynaFile="t_security_vpn"
           template="t_json_format")
    stop
  }

  # IDS/IPS-Logs (Snort, Suricata)
  if ($programname contains "snort"
      or $programname contains "suricata") then {
    action(type="omfile" dynaFile="t_security_ids"
           template="t_json_format")
    stop
  }

  # Kritische Severity → Alerting-Ruleset
  call rs_alert_security
}

# IP-Ranges der Firewall-Systeme
input(type="imudp" port="514" ruleset="rs_security"
      address="10.10.1.0/24")   # Firewall-Segment
```

---

## 8. Monitoring Team – Konfiguration

### `/etc/rsyslog.d/20-monitoring.conf`

```
# ============================================================
# MONITORING TEAM – Server & F5 Load Balancer
# Quellen: Linux-Server, Windows (NXLog), F5 BIG-IP
# ============================================================

ruleset(name="rs_monitoring") {

  # F5 BIG-IP Logs (typisch: local0, local1)
  if ($syslogfacility-text == "local0"
      or $syslogfacility-text == "local1"
      or $msg contains "BIG-IP"
      or $msg contains "tmm"
      or $msg contains "ltm"
      or $msg contains "gtm") then {
    action(type="omfile" dynaFile="t_monitoring_f5"
           template="t_json_format"
           asyncWriting="on")
    stop
  }

  # Server Health / OS-Logs
  if ($syslogfacility-text == "syslog"
      or $syslogfacility-text == "daemon"
      or $syslogfacility-text == "kern") then {
    action(type="omfile" dynaFile="t_monitoring_server"
           template="t_json_format"
           asyncWriting="on")
    stop
  }

  # Genereller Health-Check Catch-All
  action(type="omfile" dynaFile="t_monitoring_health"
         template="t_json_format")

  # Alerting-Ruleset aufrufen
  call rs_alert_monitoring
}

# Server-Segment (TCP+TLS)
input(type="imtcp" port="6514" ruleset="rs_monitoring"
      address="10.10.2.0/24")

# F5-Segment (UDP, da F5 meist UDP nutzt)
input(type="imudp" port="514" ruleset="rs_monitoring"
      address="10.10.3.0/24")
```

---

## 9. SOC Team – Konfiguration

### `/etc/rsyslog.d/30-soc.conf`

```
# ============================================================
# SOC TEAM – Alerts, Incidents, Korrelation
# Empfängt kritische Logs aus allen Teams + eigene Quellen
# ============================================================

ruleset(name="rs_soc") {

  # Alle kritischen Meldungen (emerg, alert, crit)
  if ($syslogseverity <= 2) then {
    action(type="omfile" dynaFile="t_soc_incidents"
           template="t_json_format"
           asyncWriting="on")
  }

  # Auth-Fehler & Brute-Force-Indikatoren
  if ($syslogfacility-text == "auth"
      or $syslogfacility-text == "authpriv"
      or $msg contains "Failed password"
      or $msg contains "Invalid user"
      or $msg contains "authentication failure"
      or $msg contains "POSSIBLE BREAK-IN") then {
    action(type="omfile" dynaFile="t_soc_alerts"
           template="t_json_format")
    stop
  }

  # Firewall DENY/DROP Meldungen
  if ($msg contains "DENY"
      or $msg contains "DROP"
      or $msg contains "REJECT"
      or $msg contains "blocked") then {
    action(type="omfile" dynaFile="t_soc_alerts"
           template="t_json_format")
    stop
  }

  # F5 Security Events (ASM/WAF)
  if ($msg contains "ASM"
      or $msg contains "attack_type"
      or $msg contains "violation") then {
    action(type="omfile" dynaFile="t_soc_incidents"
           template="t_json_format")
    stop
  }

  # Alerting-Ruleset aufrufen
  call rs_alert_soc
}

# SOC-Eingang: eigener Port für weitergeleitete Logs
input(type="imtcp" port="6515" ruleset="rs_soc")
```

---

## 10. Check_MK Integration

### Methode 1: Syslog-Forward direkt (empfohlen)

Check_MK (Raw/CEE) kann Syslog-Meldungen nativ über den **Event Console Input** empfangen.

**In Check_MK aktivieren:**
```
Setup → Event Console → Settings → Syslog via UDP/TCP aktivieren (Port 514/6514)
```

**Check_MK Event Console Rule konfigurieren:**
```
Regel: Rsyslog Critical Alerts
─────────────────────────────────────────
Matching:
  Syslog Priority:  EMERG, ALERT, CRIT
  Syslog Facility:  (alle)

Actions:
  State:            CRITICAL
  Contact Groups:   security-team, monitoring-team, soc-team
  Notifications:    E-Mail (redundant zu Rsyslog-Mail)

Event Handling:
  Auto-Acknowledge: Nein
  Retention:        7 Tage
```

### Methode 2: SNMP-Trap (alternativ)

```bash
apt install rsyslog-snmp -y
```

```
# /etc/rsyslog.d/40-checkmk-snmp.conf
module(load="omsnmp")

ruleset(name="rs_checkmk_snmp") {
  if ($syslogseverity <= 2) then {
    action(type="omsnmp"
           server="checkmk.intern.company.com"
           port="162"
           version="2c"
           community="public"
           trapoid="1.3.6.1.4.1.2021.13.990"
           messageoid="1.3.6.1.4.1.2021.13.990.1")
  }
}
```

---

## 11. E-Mail Benachrichtigungen

### Voraussetzungen installieren

```bash
apt install msmtp msmtp-mta mailutils -y
```

### msmtp konfigurieren `/etc/msmtprc`

```
# Globale Defaults
defaults
auth           on
tls            on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile        /var/log/msmtp.log

# Mail-Relay (interner Exchange / Postfix-Relay)
account        internal
host           mail.intern.company.com
port           587
from           rsyslog-alerts@company.com
user           rsyslog-alerts
password       DEIN_PASSWORT
tls_starttls   on

account default : internal
```

```bash
chmod 600 /etc/msmtprc
chown syslog:syslog /etc/msmtprc
```

### Mail-Skript Security Team `/usr/local/bin/rsyslog-mail-security.sh`

```bash
#!/bin/bash
# Security Team Alert Mail

TEAM="Security"
MAIL="security-team@company.com"
HOSTNAME_VAR="$1"
SEVERITY="$2"
MESSAGE="$3"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

cat <<EOF | msmtp "$MAIL"
From: rsyslog-alerts@company.com
To: $MAIL
Subject: [CRITICAL] Security Alert - $HOSTNAME_VAR
Content-Type: text/html; charset=UTF-8

<html><body>
<h2 style="color:red;">⚠ CRITICAL Security Alert</h2>
<table border="1" cellpadding="5">
  <tr><th>Zeitstempel</th><td>$TIMESTAMP</td></tr>
  <tr><th>Host</th><td>$HOSTNAME_VAR</td></tr>
  <tr><th>Severity</th><td style="color:red;"><b>$SEVERITY</b></td></tr>
  <tr><th>Team</th><td>$TEAM</td></tr>
  <tr><th>Meldung</th><td>$MESSAGE</td></tr>
</table>
<p>Bitte sofort im SOC-Portal prüfen:
<a href="https://soc.intern/alerts">SOC Dashboard</a></p>
</body></html>
EOF
```

```bash
chmod +x /usr/local/bin/rsyslog-mail-security.sh
```

### Monitoring & SOC Skripte ableiten

```bash
# Monitoring Team
sed 's/security-team@company.com/monitoring-team@company.com/g
     s/TEAM="Security"/TEAM="Monitoring"/g' \
    /usr/local/bin/rsyslog-mail-security.sh \
    > /usr/local/bin/rsyslog-mail-monitoring.sh

# SOC Team
sed 's/security-team@company.com/soc-team@company.com/g
     s/TEAM="Security"/TEAM="SOC"/g' \
    /usr/local/bin/rsyslog-mail-security.sh \
    > /usr/local/bin/rsyslog-mail-soc.sh

chmod +x /usr/local/bin/rsyslog-mail-monitoring.sh
chmod +x /usr/local/bin/rsyslog-mail-soc.sh
```

---

## 12. Zentrale Alert-Konfiguration

### `/etc/rsyslog.d/50-alerting.conf`

```
# ============================================================
# ALERTING – Critical Weiterleitung an Check_MK & E-Mail
# ============================================================

# ── Security Team ──────────────────────────────────────────
ruleset(name="rs_alert_security") {

  if ($syslogseverity <= 2) then {

    # → Check_MK weiterleiten
    action(type="omfwd"
           target="checkmk.intern.company.com"
           port="514"
           protocol="udp"
           template="t_checkmk_forward"
           queue.type="linkedList"
           queue.size="5000"
           queue.filename="q_sec_checkmk"
           queue.saveOnShutdown="on")

    # → E-Mail an Security Team
    action(type="omprogram"
           binary="/usr/local/bin/rsyslog-mail-security.sh"
           template="t_alert_params"
           queue.type="linkedList"
           queue.size="1000"
           queue.filename="q_sec_mail"
           queue.saveOnShutdown="on")
  }

  # Error-Level → nur E-Mail (kein Check_MK)
  if ($syslogseverity == 3) then {
    action(type="omprogram"
           binary="/usr/local/bin/rsyslog-mail-security.sh"
           template="t_alert_params"
           queue.type="linkedList"
           queue.size="1000"
           queue.filename="q_sec_mail_err"
           queue.saveOnShutdown="on")
  }
}

# ── Monitoring Team ────────────────────────────────────────
ruleset(name="rs_alert_monitoring") {
  if ($syslogseverity <= 2) then {
    action(type="omfwd"
           target="checkmk.intern.company.com"
           port="514"
           protocol="udp"
           template="t_checkmk_forward"
           queue.type="linkedList"
           queue.size="5000"
           queue.filename="q_mon_checkmk"
           queue.saveOnShutdown="on")

    action(type="omprogram"
           binary="/usr/local/bin/rsyslog-mail-monitoring.sh"
           template="t_alert_params"
           queue.type="linkedList"
           queue.size="1000"
           queue.filename="q_mon_mail"
           queue.saveOnShutdown="on")
  }
}

# ── SOC Team ───────────────────────────────────────────────
ruleset(name="rs_alert_soc") {
  if ($syslogseverity <= 2) then {
    action(type="omfwd"
           target="checkmk.intern.company.com"
           port="514"
           protocol="udp"
           template="t_checkmk_forward"
           queue.type="linkedList"
           queue.size="5000"
           queue.filename="q_soc_checkmk"
           queue.saveOnShutdown="on")

    action(type="omprogram"
           binary="/usr/local/bin/rsyslog-mail-soc.sh"
           template="t_alert_params"
           queue.type="linkedList"
           queue.size="1000"
           queue.filename="q_soc_mail"
           queue.saveOnShutdown="on")
  }
}
```

---

## 13. Rate-Limiting

### `/etc/rsyslog.d/01-ratelimit.conf`

```
# ============================================================
# RATE LIMITING – Verhindert E-Mail-Flooding bei Incidents
# ============================================================

# Maximal 200 Nachrichten pro 60 Sekunden pro Host
module(load="imuxsock"
       SysSock.RateLimit.Interval="60"
       SysSock.RateLimit.Burst="200")

# Globales Rate-Limiting für omprogram (Mail-Versand)
main_queue(
  queue.type="linkedList"
  queue.size="100000"
  queue.dequeueBatchSize="16"
  queue.minDequeueBatchSize="1"
  queue.minDequeueBatchSize.timeout="2000"
)
```

> **Empfehlung:** Das Rate-Limiting verhindert Mail-Flooding bei größeren Incidents oder Fehlkonfigurationen. Die Werte sollten je nach Umgebungsgröße angepasst werden.

---

## 14. Log-Rotation

### `/etc/logrotate.d/rsyslog-teams`

```
/var/log/security/**/*.log
/var/log/monitoring/**/*.log
/var/log/soc/**/*.log
{
    daily
    rotate 90
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
    postrotate
        /usr/lib/rsyslog/rsyslog-rotate
    endscript
}
```

### Standard-Rotation `/etc/logrotate.d/rsyslog`

```
/var/log/syslog /var/log/auth.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    postrotate
        /usr/lib/rsyslog/rsyslog-rotate
    endscript
}
```

---

## 15. TLS-Verschlüsselung

TLS wird für alle produktiven Umgebungen dringend empfohlen.

```bash
apt install rsyslog-gnutls -y
```

### Zertifikate erstellen (Self-Signed für Test)

```bash
mkdir -p /etc/ssl/rsyslog
cd /etc/ssl/rsyslog

# CA erstellen
openssl req -new -x509 -days 3650 -nodes \
  -out ca.pem -keyout ca-key.pem \
  -subj "/CN=Rsyslog-CA"

# Server-Zertifikat
openssl req -new -nodes \
  -out server-req.pem -keyout server-key.pem \
  -subj "/CN=rsyslog.intern.company.com"

openssl x509 -req -days 3650 \
  -in server-req.pem -CA ca.pem -CAkey ca-key.pem \
  -CAcreateserial -out server-cert.pem

chmod 600 /etc/ssl/rsyslog/*.pem
chown syslog:syslog /etc/ssl/rsyslog/*.pem
```

### TLS-Konfiguration Server

```
# In /etc/rsyslog.conf → global() Block (bereits oben enthalten)
global(
  defaultNetstreamDriver="gtls"
  defaultNetstreamDriverCAFile="/etc/ssl/rsyslog/ca.pem"
  defaultNetstreamDriverCertFile="/etc/ssl/rsyslog/server-cert.pem"
  defaultNetstreamDriverKeyFile="/etc/ssl/rsyslog/server-key.pem"
)
```

### TLS-Konfiguration Client

```
# /etc/rsyslog.d/forward-tls.conf
global(
  defaultNetstreamDriver="gtls"
  defaultNetstreamDriverCAFile="/etc/ssl/rsyslog/ca.pem"
)

*.* action(type="omfwd"
           target="rsyslog.intern.company.com"
           port="6514"
           protocol="tcp"
           StreamDriver="gtls"
           StreamDriverMode="1"
           StreamDriverAuthMode="anon")
```

---

## 16. Severity-Level & Routing-Übersicht

| Severity | Level | → Check_MK | → E-Mail | → Log-Datei | Zuständigkeit |
|---|---|:---:|:---:|---|---|
| emerg | 0 | ✅ | ✅ alle Teams | incidents | Alle |
| alert | 1 | ✅ | ✅ alle Teams | incidents | Alle |
| crit | 2 | ✅ | ✅ alle Teams | incidents | Alle |
| err | 3 | ❌ | ✅ jeweiliges Team | alerts | Team |
| warning | 4 | ❌ | ❌ | alerts | Team |
| notice | 5 | ❌ | ❌ | normal | Lokal |
| info | 6 | ❌ | ❌ | normal | Lokal |
| debug | 7 | ❌ | ❌ | normal | Lokal |

---

## 17. Netzwerk- & IP-Übersicht

| Segment | Netz | Port | Protokoll | Ruleset | Team |
|---|---|---|---|---|---|
| Firewalls | 10.10.1.0/24 | 514 | UDP | rs_security | Security |
| Linux-Server | 10.10.2.0/24 | 6514 | TCP+TLS | rs_monitoring | Monitoring |
| F5 BIG-IP | 10.10.3.0/24 | 514 | UDP | rs_monitoring | Monitoring |
| SOC-Eingang | intern | 6515 | TCP+TLS | rs_soc | SOC |
| Check_MK | checkmk.intern | 514 | UDP | – | Alert-Forward |
| SIEM | soc-siem.intern | 6514 | TCP+TLS | – | Mirror |

---

## 18. Testing & Troubleshooting

### Konfiguration prüfen

```bash
# Syntax validieren (gibt Fehler aus)
rsyslogd -N1 -f /etc/rsyslog.conf

# Rsyslog neu starten
systemctl restart rsyslog

# Status prüfen
systemctl status rsyslog

# Rsyslog-eigene Logs ansehen
journalctl -u rsyslog -f
```

### Testlogs erzeugen

```bash
# Einfacher Test
logger "Testmeldung von $(hostname)"

# Critical-Log simulieren (löst Check_MK + Mail aus)
logger -p local3.crit -t "fw-test" "DENY SRC=192.168.99.1 Brute-Force detected"

# F5-Log simulieren
logger -p local0.err -t "tmm" "BIG-IP: ltm pool member down"

# Auth-Fehler simulieren (SOC-relevant)
logger -p auth.warning -t "sshd" "Failed password for invalid user admin"
```

### Mail-Skripte direkt testen

```bash
# Security-Mail testen
/usr/local/bin/rsyslog-mail-security.sh "fw-01" "CRITICAL" "Test von fw-01"

# msmtp-Log prüfen
tail -f /var/log/msmtp.log
```

### Netzwerk-Debugging

```bash
# Eingehende Pakete auf Port 514 beobachten
tcpdump -i any -n port 514

# Check_MK-Weiterleitung prüfen
tcpdump -i any -n port 514 host checkmk.intern.company.com

# Live-Monitoring aller Teams
tail -f /var/log/security/firewall/**/*.log
tail -f /var/log/monitoring/f5/**/*.log
tail -f /var/log/soc/alerts/**/*.log
```

### Häufige Fehler

| Problem | Ursache | Lösung |
|---|---|---|
| Keine Logs empfangen | Firewall blockiert | `ufw allow 514,6514,6515/tcp` |
| TLS-Fehler | Zertifikat abgelaufen/falsch | Zertifikate prüfen, `rsyslog-gnutls` installiert? |
| Mail wird nicht gesendet | msmtp-Konfiguration | `/var/log/msmtp.log` prüfen |
| Queue wächst unkontrolliert | Check_MK nicht erreichbar | `queue.saveOnShutdown="on"` schützt vor Datenverlust |
| Doppelte Log-Einträge | imuxsock + imjournal aktiv | Eines der beiden Module deaktivieren |

---

## Anhang: Dateiübersicht

```
/etc/rsyslog.conf                          ← Hauptkonfiguration
/etc/rsyslog.d/
├── 00-templates.conf                      ← Alle Templates & Formate
├── 01-ratelimit.conf                      ← Rate-Limiting
├── 10-security.conf                       ← Security Team Ruleset
├── 20-monitoring.conf                     ← Monitoring Team Ruleset
├── 30-soc.conf                            ← SOC Team Ruleset
└── 50-alerting.conf                       ← Check_MK & E-Mail Alerting

/usr/local/bin/
├── rsyslog-mail-security.sh               ← Mail-Skript Security
├── rsyslog-mail-monitoring.sh             ← Mail-Skript Monitoring
└── rsyslog-mail-soc.sh                    ← Mail-Skript SOC

/etc/msmtprc                               ← Mail-Relay Konfiguration
/etc/ssl/rsyslog/                          ← TLS-Zertifikate
/etc/logrotate.d/rsyslog-teams             ← Log-Rotation

/var/log/
├── security/{firewall,vpn,ids}/           ← Security Logs
├── monitoring/{server,f5,health}/         ← Monitoring Logs
└── soc/{alerts,incidents,correlation}/    ← SOC Logs
```

---

*Dokument – Version 1.7 | Rsyslog unter Debian 13 | BH2005*

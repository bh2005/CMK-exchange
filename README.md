
# Checkmk Exchange Extensions by bh2005

Dieses Repository enthält eine Sammlung von Checkmk-Erweiterungen (MKPs), die primär für die [Checkmk Exchange](https://exchange.checkmk.com/) entwickelt wurden. Der Fokus liegt auf Special Agents für Cloud-Infrastrukturen und spezialisierten SNMP-Checks.

## 🚀 Highlights

### ExtremeCloud-XIQ Special Agent

Ein leistungsstarker Special Agent für **Extreme Networks CloudIQ**.

* **Zero-Touch:** Automatische Erstellung von AP-Hosts via Piggyback und Dynamic Host Management (DHM).
* **Smart Attributes:** Überträgt IPv4-Adressen, Aliase und Standorte automatisch als Host-Attribute.
* **Deep Insights:** Monitoring von Radio-Bändern (2.4/5/6 GHz), SSIDs und LLDP-Nachbarschaften.
* **Optimiert:** JWT-Caching und intelligentes API-Paging für Umgebungen mit über 1000 APs.

> **Dokumentation:** [Detailierte Anleitung zum XIQ Agent](https://www.google.com/search?q=./special_agents/ExtremeCloud-XIQ/README.md)

---

## 📂 Repository Struktur

| Pfad | Beschreibung |
| --- | --- |
| `special_agents/` | Umfassende Integrationen für Cloud-Plattformen und APIs. |
| `snmp_checks/` | Spezialisierte SNMP-basierte Plugins für Netzwerk-Equipment. |
| `local_checks/` | Hilfreiche Skripte für das lokale Monitoring auf Hosts. |

---

## 🛠 Installation

Die Erweiterungen werden als **Checkmk Extension Packages (.mkp)** bereitgestellt.

### Via GUI (Empfohlen)

1. Gehe zu **Setup > Extensions > Extension Packages**.
2. Klicke auf **Upload package** und wähle die gewünschte `.mkp` Datei aus.

### Via CLI (für Site-User)

```bash
# Paket installieren
mkp install /pfad/zu/deinem/paket-1.0.mkp

# Installierte Pakete anzeigen
mkp list

```

---

## 📋 Best Practices für die Nutzung

### Aktive Checks auf Piggyback-Hosts

Da viele Agents in diesem Repo (wie XIQ) Piggyback-Daten nutzen, empfehlen wir die Einrichtung eines **aktiven IPv4-Pings**, um die echte Netzwerk-Verfügbarkeit zu prüfen:

1. Nutze die vom Agenten gesetzte IPv4-Adresse.
2. Konfiguriere unter *Host Check Command* den **Smart PING** oder **ICMP Echo Request**.

---

## 🤝 Mitwirken & Support

Hast du einen Bug gefunden oder einen Feature-Wunsch?

* **Issues:** Erstelle ein [Issue](https://www.google.com/search?q=https://github.com/bh2005/CMK-exchange/issues).
* **Pull Requests:** Beiträge sind jederzeit willkommen! Bitte stelle sicher, dass neue Checks der Checkmk 2.3/2.4 API-Struktur entsprechen.

---

## 📜 Lizenz

Alle Plugins in diesem Repository stehen unter der **GNU General Public License v2 (GPLv2)**.

---

**Autor:** [Bernd Holzhauer](https://www.google.com/search?q=https://github.com/bh2005)

**Checkmk Exchange Profil:** [bh2005](https://www.google.com/search?q=https://exchange.checkmk.com/u/bh2005)



# Checkmk Special Agent: ExtremeCloudIQ (XIQ)

Dieses Paket bietet eine  Integration für **Extreme Networks CloudIQ**. Es überwacht sowohl die globale Cloud-Instanz als auch alle verwalteten Access Points (APs) mithilfe der XIQ REST-API.

**Repository:** [bh2005/CMK-exchange](https://www.google.com/search?q=https://github.com/bh2005/CMK-exchange/tree/main/special_agents/ExtremeCloud-XIQ)

## Highlights

* **Vollautomatisch**: Access Points werden via Piggyback erkannt. Dank `cmk_host_attributes` wird die IPv4-Adresse automatisch von der Cloud an den Checkmk-Host übertragen.
* **Deep Monitoring**: Detaillierte Radio-Metriken (2.4/5/6 GHz), SSID-Auslastung und Topologie-Daten (LLDP/CDP).
* **API-Schonend**: Integriertes JWT-Caching und Handling von Rate-Limits.

---

## 1. Installation

1. MKP-Paket herunterladen oder aus dem Repo bauen.
2. Installation via GUI (**Setup > Extensions**) oder CLI:
```bash
mkp install xiq_cloud_agent-0.3.1.mkp

```



## 2. Einrichtung des Special Agents

1. **Zentraler API-Host**: Erstelle einen Host (z. B. `XIQ_Cloud_Connector`) mit **IP Address Family: No IP** und **No agent**.
2. **Regel erstellen**: Gehe zu **Setup > Agents > VM, Cloud, Container > ExtremeCloudIQ (XIQ)**.
* Hinterlege deine **XIQ-Zugangsdaten**.
* Wähle optional aus, welche Daten (Radios, Clients, Neighbors) abgerufen werden sollen.
* Weise die Regel dem `XIQ_Cloud_Connector` zu.



## 3. Dynamische Host-Konfiguration (DHM)

Um die APs nicht manuell anlegen zu müssen:

1. Gehe zu **Setup > Hosts > Dynamic host management**.
2. Erstelle eine neue Verbindung mit dem Connector **Piggyback data**.
3. **Wichtig**: Der Agent überträgt die IP-Adresse automatisch. In den Attributen der DHM-Verbindung sollte **Checkmk agent / API integrations** auf **No agent** stehen.

---

## 4. Host-Status & Aktiver IPv4-Ping

Da APs oft via Piggyback überwacht werden, "erben" sie den Status des API-Abfragers. Um die **echte Erreichbarkeit** im LAN zu prüfen, nutzt dieses Plugin die mitgelieferte IPv4-Adresse für einen aktiven Check:

### Schritt A: Host-Check-Kommando umstellen

1. Gehe zu **Setup > Host monitoring rules > Host Check Command**.
2. Erstelle eine Regel für die AP-Hosts (nutze z. B. das Label `tag_xiq_ap:yes`, das der Agent automatisch setzt).
3. Wähle **Use a custom check plugin** -> **Check ICMP echo request (PING)**.

### Schritt B: Aktiven Ping-Service konfigurieren

1. Gehe zu **Setup > Services > HTTP, TCP, Email, ... > Check ICMP Echo Request (PING)**.
2. Erstelle eine neue Regel.
3. **Wichtig**: Setze **IP address family** auf **IPv4**.
4. Wähle bei **Address to check**: **IP address of the host (IPv4)**.
* *Resultat: Checkmk nutzt die vom Agenten via `cmk_host_attributes` gesetzte IP-Adresse für einen realen Ping-Check.*



---

## 5. Verfügbare Check-Plugins

| Plugin | Beschreibung |
| --- | --- |
| **XIQ AP Status** | Grundstatus, Uptime und CPU/RAM des Access Points. |
| **XIQ Radios** | Metriken pro Band (2.4/5/6 GHz): Clients, Kanäle, TX-Power. |
| **XIQ SSID Clients** | Anzahl der Clients pro ausgestrahlter SSID. |
| **XIQ Neighbors** | LLDP/CDP Nachbarschaftsinformationen (Switchport-Anbindung). |
| **XIQ Rate Limits** | Überwachung des verbleibenden API-Kontingents. |
| **XIQ Summary** | Globale Cloud-Statistiken (Lizenzen, Geräte-Limits). |

---

## 6. Debugging

Falls die automatische IP-Zuweisung oder die Daten nicht wie gewünscht erscheinen, teste den Agenten auf der Konsole:

```bash
# Als Site-User:
~/local/share/check_mk/agents/special/agent_xiq --user 'USER' --password 'PASS' --debug 'INSTANCE'

```

Prüfe, ob die Sektion `<<<cmk_host_attributes:sep(0)>>>` die korrekte `ipaddress=...` Zeile für deine APs ausgibt.

---

**Lizenz:** GPLv2

**Autor:** Bernd Holzhauer

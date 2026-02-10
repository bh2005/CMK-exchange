# Link / Button Dashlet - Quick Start Guide

## 📦 Was ist das?

Ein **Universal Link Dashlet** für Check_MK das:

✅ **Links zu anderen Dashboards** erstellt
✅ **Links zu Views** erstellt (Hosts, Services, etc.)
✅ **Links zu externen URLs** erstellt (Grafana, andere Tools)
✅ **iFrames einbettet** (andere Webseiten direkt im Dashboard)
✅ **Verschiedene Styles** bietet (Button, Card, Minimal, Badge)
✅ **Icons & Farben** anpassbar macht

## 🚀 Installation

```bash
# Als site-user
sudo cp link_dashlet.py /omd/sites/SITE/local/share/check_mk/web/plugins/dashboard/
sudo chown SITE:SITE /omd/sites/SITE/local/share/check_mk/web/plugins/dashboard/link_dashlet.py
omd reload apache
```

Browser: `Ctrl + Shift + R`

## 🎯 Verwendungs-Beispiele

### Beispiel 1: Link zu anderem Dashboard

**Use Case:** Link von "Main Dashboard" zu "Extreme AP Dashboard"

```
Link Type: Internal Dashboard
  Dashboard Name: extreme_ap_dashboard

Title: Access Points Overview
Icon: 📡
Style: Large Button
Background: Gradient Blue
```

**Ergebnis:** Großer blauer Button mit 📡 Icon

---

### Beispiel 2: Link zu Grafana

**Use Case:** Direkter Link zu Grafana Dashboard

```
Link Type: External URL
  URL: https://grafana.company.com/d/abc123/network
  Open in: New window/tab

Title: Grafana Network Dashboard
Description: Network Performance Metrics
Icon: 📈
Style: Card with shadow
Background: Gradient Green
```

**Ergebnis:** Card mit Link zu Grafana (öffnet in neuem Tab)

---

### Beispiel 3: Embedded Grafana Panel

**Use Case:** Grafana direkt im Dashboard einbetten

```
Link Type: Embedded iframe
  URL: https://grafana.company.com/d-solo/abc123/network?panelId=2

Title: (nicht relevant bei iframe)
```

**Dashlet Size:** Width: 40, Height: 30

**Ergebnis:** Grafana Panel direkt im Dashboard embedded

---

### Beispiel 4: Link zu Check_MK View

**Use Case:** Schnellzugriff auf "All Services" View

```
Link Type: Internal View
  View Name: allservices

Title: All Services
Icon: 📋
Style: Badge/Tag
Background: Orange
```

**Ergebnis:** Kleiner Badge-Button

---

### Beispiel 5: Externe Monitoring Tools

**Use Case:** Links zu verschiedenen Tools

**Dashlet 1:**
```
URL: https://netbox.company.com
Title: NetBox IPAM
Icon: 🌐
Style: Minimal link
```

**Dashlet 2:**
```
URL: https://zabbix.company.com
Title: Zabbix Monitoring
Icon: 🖥️
Style: Minimal link
```

**Layout:** Beide nebeneinander als kleine Links

## 🎨 Konfigurations-Optionen

### Link Type

| Option | Verwendet für | Format |
|--------|---------------|---------|
| **Internal Dashboard** | Andere Check_MK Dashboards | `dashboard_name` |
| **Internal View** | Check_MK Views (Hosts, Services) | `view_name` |
| **External URL** | Externe Webseiten | `https://...` |
| **Embedded iframe** | Webseiten einbetten | `https://...` |

### Display Styles

| Style | Aussehen | Best für |
|-------|----------|----------|
| **Large Button** | Großer Button, zentriert | Hauptnavigation |
| **Card with shadow** | Card mit Schatten | Übersichtliche Links |
| **Minimal link** | Kleiner Link | Viele Links nebeneinander |
| **Badge/Tag** | Kleiner Badge | Kompakte Navigation |

### Icons

Emoji-Auswahl:
- 📊 Chart/Dashboard
- 🖥️ Server/Computer
- 📈 Graph/Trending
- 🔍 Search/View
- ⚙️ Settings
- 📱 Mobile/Device
- 🌐 Network/Globe
- 📡 Signal/Wireless
- 🚀 Rocket/Launch
- ⚡ Lightning/Fast
- 🎯 Target/Focus
- 📋 List/Document
- 🔔 Notification
- 👥 Users/Team
- 🏢 Building

### Farben

**Background:**
- Blue, Green, Purple, Orange, Red, Gray
- Gradient Blue, Green, Purple, Orange

**Text:**
- White, Black, Gray

## 📐 Layout-Beispiele

### Layout 1: Navigation Bar

```
┌─────────┬─────────┬─────────┬─────────┐
│ APs 📡  │ Grafana │ NetBox  │ Zabbix  │
│ (10x5)  │ (10x5)  │ (10x5)  │ (10x5)  │
└─────────┴─────────┴─────────┴─────────┘
```

**Style:** Badge/Tag oder Minimal
**Größe:** 10x5 jedes Dashlet

---

### Layout 2: Main Navigation

```
┌──────────────────┬──────────────────┐
│                  │                  │
│  Access Points   │   Switches       │
│      📡          │       🌐         │
│    (20x10)       │     (20x10)      │
│                  │                  │
├──────────────────┼──────────────────┤
│                  │                  │
│    Grafana       │    Netbox        │
│      📈          │       🏢         │
│    (20x10)       │     (20x10)      │
│                  │                  │
└──────────────────┴──────────────────┘
```

**Style:** Large Button
**Größe:** 20x10 jedes

---

### Layout 3: Embedded Tools

```
┌─────────────────────────────────────┐
│                                     │
│  [Link Buttons Row - 5x each]       │
│  APs | Grafana | NetBox | Zabbix   │
│                                     │
├─────────────────────────────────────┤
│                                     │
│    Embedded Grafana Dashboard       │
│           (iframe 60x40)            │
│                                     │
└─────────────────────────────────────┘
```

Top: 4x Badge Dashlets (60x5 gesamt)
Bottom: 1x iframe Dashlet (60x40)

---

### Layout 4: Mixed Dashboard

```
┌──────────────┬──────────────────────┐
│              │                      │
│  Extreme AP  │                      │
│  Statistics  │   Grafana iframe     │
│              │      (40x30)         │
│   (20x30)    │                      │
│              │                      │
├──────────────┼──────────────────────┤
│              │                      │
│ Link: NetBox │  Link: Other Tools   │
│   (20x10)    │      (40x10)         │
└──────────────┴──────────────────────┘
```

## 🔧 Häufige Use Cases

### 1. Navigation zu verschiedenen Monitoring-Bereichen

Erstelle ein "Navigation Dashboard" mit Links zu:
- Access Points Dashboard
- Switches Dashboard
- Servers Dashboard
- Network Dashboard
- Storage Dashboard

**Style:** Large Button, verschiedene Icons

---

### 2. Integration mit externen Tools

Erstelle Links zu:
- Grafana (Graphs & Dashboards)
- NetBox (IPAM/DCIM)
- Zabbix/Nagios (andere Monitoring)
- ITSM Tools (ServiceNow, JIRA)
- Documentation (Wiki, Confluence)

**Style:** Card oder Minimal

---

### 3. Eingebettete Dashboards

Bette ein via iframe:
- Grafana Panels
- Network Weather Maps
- Custom HTML Dashboards
- Status Pages

**Size:** Größeres Dashlet (40x30 oder mehr)

---

### 4. Quick Actions / Shortcuts

Kleine Badge-Links zu:
- Acknowledge all problems
- Service Discovery
- Host Configuration
- Reports
- Notifications

**Style:** Badge, kompakt nebeneinander

## 🎯 Schritt-für-Schritt: Ersten Link erstellen

### Schritt 1: Dashboard öffnen
```
Customize → Visualization → Dashboards → [Dein Dashboard]
```

### Schritt 2: Dashlet hinzufügen
```
Edit dashboard → Add dashlet → "Link / Button Dashlet"
```

### Schritt 3: Konfigurieren

**Basic Setup:**
```
Title: Access Points
```

**Link Type:**
```
○ Internal Dashboard
  Dashboard Name: extreme_ap_dashboard
```

**Appearance:**
```
Style: Large Button
Icon: 📡
Background Color: Gradient Blue
Text Color: White
```

**Size:**
```
Width: 20
Height: 10
```

### Schritt 4: Speichern & Testen
```
Save → Click auf Button → sollte zu Dashboard navigieren
```

## 💡 Pro Tips

### Tip 1: Dashboard Namen finden

Für "Internal Dashboard" brauchst du den internen Namen:

```
URL checken:
https://checkmk.company.com/site/check_mk/dashboard.py?name=DASHBOARD_NAME
                                                              ^^^^^^^^^^^^^^
```

Oder:
```
Customize → Visualization → Dashboards → [Dashboard] → Properties → ID
```

### Tip 2: View Namen finden

Für "Internal View":

```
Setup → Views → [View] → Properties → ID

Oder URL checken:
view.py?view_name=VIEW_NAME
                  ^^^^^^^^^
```

Common Views:
- `allhosts` - All Hosts
- `allservices` - All Services
- `svcproblems` - Service Problems
- `hostproblems` - Host Problems

### Tip 3: iframe Größe anpassen

Für iframe Embeds:
- **Small Panel:** 20x15
- **Medium Panel:** 40x30
- **Large Panel:** 60x40
- **Fullscreen:** 80x60

### Tip 4: Grafana Panel URL

Für Grafana iframe:
```
Normal URL:
https://grafana.com/d/abc123/dashboard?orgId=1

Solo Panel URL (für iframe):
https://grafana.com/d-solo/abc123/dashboard?orgId=1&panelId=2
                     ^^^^^                              ^^^^^^
```

Click auf Panel → Share → Link → "Direct link rendered image"

### Tip 5: Mehrere Links gruppieren

Erstelle ein Grid von kleinen Dashlets:
- Alle gleiche Größe (z.B. 15x8)
- Alle gleicher Style (z.B. Card)
- Verschiedene Farben für Kategorien

## 🔒 iframe Security

**⚠️ Wichtig:** Nicht alle Webseiten erlauben iframe embedding!

**Funktioniert meist:**
- ✅ Eigene interne Tools
- ✅ Grafana (mit richtigen Settings)
- ✅ Custom Dashboards

**Funktioniert oft NICHT:**
- ❌ Google
- ❌ Facebook
- ❌ GitHub
- ❌ Viele externe Sites (X-Frame-Options)

**Lösung:** Nutze "External URL" + "New window" statt iframe

## 📝 Checkliste

- [ ] Dashlet installiert
- [ ] Apache neu geladen
- [ ] Dashboard geöffnet
- [ ] Dashlet hinzugefügt
- [ ] Link Type gewählt
- [ ] Target konfiguriert (Dashboard/View/URL)
- [ ] Title & Icon gesetzt
- [ ] Style gewählt
- [ ] Farben angepasst
- [ ] Größe eingestellt
- [ ] Getestet - Link funktioniert

## 🎉 Fertig!

Du kannst jetzt:
- ✅ Links zu anderen Dashboards erstellen
- ✅ Links zu externen Tools erstellen
- ✅ iframes einbetten
- ✅ Schöne Navigation Buttons machen
- ✅ Komplexe Layouts bauen

**Weitere Ideen:**
- 🎨 Dashboard mit allen wichtigen Tools
- 🚀 Quick-Access Navigation Bar
- 📊 Mixed Dashboard (Check_MK + Grafana)
- 🔗 Tool-Übersicht für Admins

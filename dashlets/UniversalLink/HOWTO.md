# Link / Button Dashlet - Quick Start Guide

## 📦 Was ist das?

Ein **Universal Link Dashlet** für Checkmk 2.5: rendert einen klickbaren
Link/Button/Card zu einem anderen Dashboard, einer Checkmk View oder einer
externen URL, dargestellt über ein Iframe.

> **CMK 2.5 Rewrite:** Checkmk 2.5 hat die klassische `Dashlet.show()`-API
> entfernt, auf der ältere Dashlets (auch frühere Versionen dieses hier)
> basierten. Diese Version nutzt stattdessen die `IFrameDashlet`-API und
> rendert ihren Inhalt über eine eigene kleine Page (`link_dashlet_content.py`).
> Dadurch ist der frühere komfortable Konfigurationsdialog (Dropdowns für
> Icon/Farbe/Style/Link-Typ) aktuell weg – Ziel-URL und Aussehen werden
> vorerst per Hand als Query-Parameter konfiguriert (siehe unten).

## 🚀 Installation

Zwei Dateien, an **zwei unterschiedlichen Orten** – keine davon weglassen:

```bash
# Als site-user
sudo cp local/lib/python3/cmk/gui/plugins/dashboard/link_dashlet.py \
        /omd/sites/SITE/local/lib/python3/cmk/gui/plugins/dashboard/link_dashlet.py

sudo cp local/share/check_mk/web/plugins/pages/link_dashlet_content.py \
        /omd/sites/SITE/local/share/check_mk/web/plugins/pages/link_dashlet_content.py

sudo chown -R SITE:SITE /omd/sites/SITE/local/lib/python3/cmk/gui/plugins/dashboard/link_dashlet.py \
                          /omd/sites/SITE/local/share/check_mk/web/plugins/pages/link_dashlet_content.py
omd reload apache
```

Alternativ beide Dateien als ein `.mkp` packen (Part `gui`:
`dashboard/link_dashlet.py`, Part `web`: `plugins/pages/link_dashlet_content.py`)
und unter **Setup → Maintenance → Extension packages → Upload package**
hochladen.

Browser danach mit `Ctrl + Shift + R` hart neu laden.

## 🎯 Verwendung

1. Dashboard öffnen → **Edit dashboard → Add dashlet → "Link / Button"**.
2. Im URL/Iframe-Feld des Dashlets auf die Content-Page mit Query-Parametern
   verweisen:

```
../check_mk/link_dashlet_content.py?title=MyLink&icon=📊&color=blue&style=button&link_url=dashboard.py%3Fname%3Dmain&target=_top
```

### Parameter

| Parameter  | Werte                                | Default | Hinweis                                             |
|------------|----------------------------------------|---------|------------------------------------------------------|
| `title`    | beliebiger Text                       | `Link`  | Button-Beschriftung                                   |
| `icon`     | beliebiges Emoji                      | (keins) | Optionales Icon über dem Titel                        |
| `color`    | `blue`\|`green`\|`purple`\|`orange`\|`red` | `blue`  | Gradient-Hintergrund                             |
| `style`    | `button`\|`card`\|`minimal`           | `button`| Anzeigestil                                           |
| `link_url` | URL-encodete Ziel-URL                 | `#`     | z.B. `dashboard.py%3Fname%3Dmain`, `view.py%3Fview_name%3Dallservices`, oder eine volle externe `https://…` |
| `target`   | `_top`\|`_blank`\|`_self`             | `_top`  | `_top` nutzen, um aus dem Iframe heraus zu navigieren |

### Beispiele

**Link zu anderem Dashboard:**
```
link_url=dashboard.py%3Fname%3Dextreme_ap_dashboard&title=Access%20Points&icon=📡&color=blue&target=_top
```

**Link zu einer Checkmk View:**
```
link_url=view.py%3Fview_name%3Dallservices&title=All%20Services&icon=📋&color=orange&target=_top
```

**Link zu externem Tool (neuer Tab):**
```
link_url=https%3A%2F%2Fgrafana.company.com%2Fd%2Fabc123%2Fnetwork&title=Grafana&icon=📈&color=green&target=_blank
```

## 🎨 Farben

`blue`, `green`, `purple`, `orange`, `red` – jeweils ein zweistufiger
Gradient, exakte Hex-Werte siehe `link_dashlet_content.py`.

## 🎨 Styles

- `button` – großer zentrierter Button
- `card` – Card mit Rahmen/Schatten
- `minimal` – schlichter Textlink

## 🔒 Hinweise

- Das Dashlet rendert immer über ein Iframe (`link_dashlet_content.py`); ein
  separater Modus "externe Seite direkt einbetten" existiert nicht mehr –
  für ein beliebiges externes Iframe stattdessen das eingebaute generische
  Iframe-Dashlet von Checkmk nutzen.
- `target=_top` ist nötig, damit Dashboard-/View-Links die äußere
  Checkmk-Seite navigieren statt im Iframe gefangen zu bleiben.

## 📝 Checkliste

- [ ] Beide Dateien an ihren Site-Pfaden installiert (`gui/plugins/dashboard`
      **und** `web/plugins/pages`)
- [ ] Apache neu geladen
- [ ] Dashlet zum Dashboard hinzugefügt
- [ ] URL-Parameter konfiguriert, `target=_top` bei internen Links gesetzt
- [ ] Getestet – Link/Button rendert und navigiert korrekt

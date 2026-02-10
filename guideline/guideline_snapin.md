# Checkmk 2.4+ Sidebar Snapin Development Guide

## 📋 Übersicht

Sidebar Snapins sind kompakte GUI-Elemente in der Checkmk-Sidebar, die Informationen anzeigen oder Funktionen bereitstellen.

---

## 🏗️ Grundstruktur

### Datei-Speicherort

**WICHTIG:** Checkmk 2.0+ verwendet neuen Pfad!

```bash
# KORREKT (Checkmk 2.0+):
~/local/lib/python3/cmk/gui/plugins/sidebar/<dateiname>.py

# FALSCH (alte Versionen):
~/local/share/check_mk/web/plugins/sidebar/<dateiname>.py
```

### Verzeichnis erstellen

```bash
# Als site-user
sudo su - <sitename>

# Verzeichnis anlegen
mkdir -p ~/local/lib/python3/cmk/gui/plugins/sidebar

# __init__.py erstellen (leer, aber notwendig)
touch ~/local/lib/python3/cmk/gui/plugins/sidebar/__init__.py
```

---

## 📝 Snapin-Template (Checkmk 2.4+)

### Minimales Beispiel

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Custom Sidebar Snapin: Example
"""

from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar.utils import (
    SidebarSnapin,
    snapin_registry,
)


@snapin_registry.register
class ExampleSnapin(SidebarSnapin):
    """
    Example sidebar snapin showing basic structure.
    """
    
    @staticmethod
    def type_name() -> str:
        """
        Unique identifier for this snapin.
        Must be unique across all snapins.
        """
        return "example"
    
    @classmethod
    def title(cls) -> str:
        """
        Display title shown in snapin header.
        Use _() for translations.
        """
        return _("Example Snapin")
    
    @classmethod
    def description(cls) -> str:
        """
        Description shown in "Add snapin" dialog.
        """
        return _("An example snapin demonstrating basic functionality")
    
    def show(self) -> None:
        """
        Main render function.
        Called when snapin is displayed.
        """
        from cmk.gui.htmllib.html import html
        
        html.open_div(class_="example_snapin")
        html.write_text(_("Hello from Example Snapin!"))
        html.close_div()
```

### Vollständiges Beispiel mit allen Features

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Advanced Sidebar Snapin with all features
"""

from typing import Optional, List

from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar.utils import (
    SidebarSnapin,
    snapin_registry,
    snapin_site_choice,
    make_topic_menu,
)
from cmk.gui.htmllib.html import html
from cmk.gui.utils.urls import makeuri_contextless


@snapin_registry.register
class AdvancedSnapin(SidebarSnapin):
    """
    Advanced sidebar snapin with all available features.
    """
    
    @staticmethod
    def type_name() -> str:
        return "advanced_example"
    
    @classmethod
    def title(cls) -> str:
        return _("Advanced Example")
    
    @classmethod
    def description(cls) -> str:
        return _("Demonstrates all snapin features including refresh, styles, and links")
    
    @classmethod
    def refresh_regularly(cls) -> bool:
        """
        If True, snapin refreshes automatically.
        Default: False
        """
        return True
    
    @classmethod
    def refresh_on_restart(cls) -> bool:
        """
        If True, snapin refreshes when Checkmk core restarts.
        Default: False
        """
        return False
    
    @classmethod
    def allowed_roles(cls) -> List[str]:
        """
        List of roles allowed to see this snapin.
        Default: ["admin", "user", "guest"]
        Return empty list for all roles.
        """
        return []  # All roles
    
    @classmethod
    def styles(cls) -> Optional[str]:
        """
        Optional CSS styles for this snapin.
        """
        return """
        .advanced_snapin {
            padding: 5px;
        }
        .advanced_snapin .stat {
            display: flex;
            justify-content: space-between;
            padding: 3px 0;
        }
        .advanced_snapin .value {
            font-weight: bold;
            color: #0084c8;
        }
        """
    
    def show(self) -> None:
        """
        Render the snapin content.
        """
        html.open_div(class_="advanced_snapin")
        
        # Simple text
        html.write_text(_("Status Information"))
        html.br()
        
        # Stats with formatting
        html.open_div(class_="stat")
        html.write_text(_("Hosts:"))
        html.span("42", class_="value")
        html.close_div()
        
        html.open_div(class_="stat")
        html.write_text(_("Services:"))
        html.span("1337", class_="value")
        html.close_div()
        
        # Links
        html.hr()
        
        # Simple link
        html.a(
            _("View All Hosts"),
            href=makeuri_contextless(
                request=html.request,
                vars=[("view_name", "allhosts")],
                filename="view.py",
            ),
        )
        
        html.close_div()
```

---

## 🎨 HTML Helper Functions

### Wichtigste HTML-Funktionen

```python
from cmk.gui.htmllib.html import html

# Text schreiben
html.write_text(_("Hello World"))
html.write_html("<b>Bold</b>")  # Raw HTML

# Strukturen
html.open_div(class_="my-class", id="my-id")
html.close_div()

html.open_span(class_="highlight")
html.close_span()

html.br()  # Line break
html.hr()  # Horizontal rule

# Links
html.a(
    _("Link Text"),
    href="https://example.com",
    target="_blank",
    class_="external-link",
)

# Listen
html.open_ul()
html.li(_("Item 1"))
html.li(_("Item 2"))
html.close_ul()

# Tabellen
html.open_table(class_="data")
html.open_tr()
html.th(_("Header 1"))
html.th(_("Header 2"))
html.close_tr()
html.open_tr()
html.td("Value 1")
html.td("Value 2")
html.close_tr()
html.close_table()

# Icons
html.icon("check", title=_("OK"))
html.icon("warning", title=_("Warning"))
html.icon("error", title=_("Error"))

# Buttons
html.buttonlink(
    href="some_page.py",
    text=_("Click Me"),
    class_="hot",
)
```

---

## 🔗 Nützliche Helper-Funktionen

### URL-Generierung

```python
from cmk.gui.utils.urls import makeuri_contextless

# View-URL
view_url = makeuri_contextless(
    request=html.request,
    vars=[
        ("view_name", "allhosts"),
        ("site", "mysite"),
    ],
    filename="view.py",
)

# Dashboard-URL
dashboard_url = makeuri_contextless(
    request=html.request,
    vars=[("name", "main")],
    filename="dashboard.py",
)
```

### Site-Auswahl

```python
from cmk.gui.plugins.sidebar.utils import snapin_site_choice

# Zeigt Site-Auswahl Dropdown
snapin_site_choice()
```

### Links mit Icons

```python
from cmk.gui.plugins.sidebar.utils import (
    link,
    simplelink,
    bulletlink,
    iconlink,
)

# Einfacher Link
link(_("Text"), "https://example.com")

# Link mit Bullet
bulletlink(_("Item"), "view.py?view_name=allhosts")

# Link mit Icon
iconlink(_("Hosts"), "view.py?view_name=allhosts", "host")
```

---

## 📊 Daten von Checkmk abrufen

### LiveStatus-Abfragen

```python
import livestatus

def show(self) -> None:
    try:
        sites.live().set_prepend_site(True)
        
        # Einfache Abfrage
        hosts = sites.live().query("GET hosts\nColumns: name state")
        
        # Mit Filter
        down_hosts = sites.live().query(
            "GET hosts\n"
            "Columns: name state\n"
            "Filter: state = 1\n"
        )
        
        html.write_text(f"Total hosts: {len(hosts)}")
        html.br()
        html.write_text(f"Down hosts: {len(down_hosts)}")
        
    except Exception as e:
        html.show_error(_("Error querying Livestatus: %s") % e)
```

### Statistiken abrufen

```python
from cmk.gui.plugins.views.utils import get_host_stats, get_service_stats

def show(self) -> None:
    # Host-Statistiken
    host_stats = get_host_stats()
    html.write_text(f"Hosts UP: {host_stats['up']}")
    html.br()
    html.write_text(f"Hosts DOWN: {host_stats['down']}")
    
    # Service-Statistiken
    service_stats = get_service_stats()
    html.write_text(f"Services OK: {service_stats['ok']}")
    html.br()
    html.write_text(f"Services CRIT: {service_stats['crit']}")
```

---

## 🔄 Refresh-Verhalten

### Auto-Refresh aktivieren

```python
@classmethod
def refresh_regularly(cls) -> bool:
    """
    Snapin wird automatisch alle paar Sekunden aktualisiert.
    Standard: False
    """
    return True
```

### Refresh bei Core-Restart

```python
@classmethod
def refresh_on_restart(cls) -> bool:
    """
    Snapin wird aktualisiert wenn Monitoring-Core neu startet.
    Nützlich für Snapins die Core-Daten anzeigen.
    """
    return True
```

---

## 🎨 Styling

### Inline CSS

```python
@classmethod
def styles(cls) -> Optional[str]:
    return """
    .my_snapin {
        background-color: #f0f0f0;
        padding: 10px;
    }
    .my_snapin .warning {
        color: #ff9900;
        font-weight: bold;
    }
    """
```

### Verfügbare CSS-Klassen

```python
# Checkmk Standard-Klassen:
"state0"     # OK/UP
"state1"     # WARN/DOWN
"state2"     # CRIT/UNREACH
"state3"     # UNKNOWN
"statep"     # PENDING

"hot"        # Hervorgehobener Button
"really"     # Bestätigungs-Button

"icon"       # Icon-Wrapper
"warning"    # Warning-Farbe
"error"      # Error-Farbe
```

---

## 🔐 Berechtigungen

### Role-Based Access

```python
@classmethod
def allowed_roles(cls) -> List[str]:
    """
    Nur bestimmte Rollen dürfen Snapin sehen.
    """
    return ["admin", "user"]  # Nicht "guest"
```

### Permission-Check im Code

```python
from cmk.gui.config import user

def show(self) -> None:
    if not user.may("general.see_all"):
        html.show_error(_("You don't have permission to view this"))
        return
    
    # Normal rendering...
```

---

## 🧪 Testing & Debugging

### Installation

```bash
# Als site-user
sudo su - <sitename>

# Python-Syntax prüfen
python3 -m py_compile ~/local/lib/python3/cmk/gui/plugins/sidebar/my_snapin.py

# Cache löschen
rm -rf ~/local/lib/python3/cmk/gui/plugins/sidebar/__pycache__

# Webserver neu laden
omd reload apache
```

### Snapin aktivieren

1. Checkmk GUI öffnen
2. Unten links auf "Add snapin" klicken
3. Eigenes Snapin in der Liste finden
4. Hinzufügen

### Debug-Ausgaben

```python
import logging

logger = logging.getLogger("cmk.web.sidebar")

def show(self) -> None:
    logger.info("Snapin is being rendered")
    logger.debug("Debug info: %s", some_variable)
    
    # Im Snapin sichtbare Fehler
    html.show_error(_("Something went wrong"))
    html.show_warning(_("This is a warning"))
```

### Logs anschauen

```bash
# Web-Log
tail -f ~/var/log/web.log

# Apache-Log
tail -f ~/var/log/apache/error_log
```

---

## 🎯 Praxis-Beispiele

### Beispiel 1: System Info Snapin

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar.utils import (
    SidebarSnapin,
    snapin_registry,
)
from cmk.gui.htmllib.html import html
import platform
import psutil


@snapin_registry.register
class SystemInfoSnapin(SidebarSnapin):
    
    @staticmethod
    def type_name() -> str:
        return "system_info"
    
    @classmethod
    def title(cls) -> str:
        return _("System Info")
    
    @classmethod
    def description(cls) -> str:
        return _("Shows system information of the Checkmk server")
    
    @classmethod
    def refresh_regularly(cls) -> bool:
        return True
    
    @classmethod
    def styles(cls) -> str:
        return """
        .system_info table {
            width: 100%;
        }
        .system_info td:first-child {
            color: #666;
        }
        .system_info td:last-child {
            font-weight: bold;
            text-align: right;
        }
        """
    
    def show(self) -> None:
        html.open_div(class_="system_info")
        html.open_table()
        
        # CPU
        html.open_tr()
        html.td(_("CPU Usage:"))
        html.td(f"{psutil.cpu_percent():.1f}%")
        html.close_tr()
        
        # Memory
        mem = psutil.virtual_memory()
        html.open_tr()
        html.td(_("Memory:"))
        html.td(f"{mem.percent:.1f}%")
        html.close_tr()
        
        # Hostname
        html.open_tr()
        html.td(_("Hostname:"))
        html.td(platform.node())
        html.close_tr()
        
        html.close_table()
        html.close_div()
```

### Beispiel 2: Quick Links Snapin

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar.utils import (
    SidebarSnapin,
    snapin_registry,
    bulletlink,
    iconlink,
)
from cmk.gui.htmllib.html import html


@snapin_registry.register
class QuickLinksSnapin(SidebarSnapin):
    
    @staticmethod
    def type_name() -> str:
        return "quick_links"
    
    @classmethod
    def title(cls) -> str:
        return _("Quick Links")
    
    @classmethod
    def description(cls) -> str:
        return _("Frequently used views and pages")
    
    def show(self) -> None:
        html.open_ul()
        
        # Verschiedene Link-Styles
        bulletlink(_("All Hosts"), "view.py?view_name=allhosts")
        bulletlink(_("Problems"), "view.py?view_name=problems")
        bulletlink(_("Events"), "view.py?view_name=events")
        
        html.close_ul()
        
        html.hr()
        
        # Mit Icons
        iconlink(_("Dashboards"), "dashboard.py", "dashboard")
        html.br()
        iconlink(_("Reports"), "report.py", "report")
```

### Beispiel 3: Counter Snapin mit LiveStatus

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar.utils import (
    SidebarSnapin,
    snapin_registry,
)
from cmk.gui.htmllib.html import html
import livestatus


@snapin_registry.register
class CounterSnapin(SidebarSnapin):
    
    @staticmethod
    def type_name() -> str:
        return "counters"
    
    @classmethod
    def title(cls) -> str:
        return _("Counters")
    
    @classmethod
    def description(cls) -> str:
        return _("Shows various monitoring counters")
    
    @classmethod
    def refresh_regularly(cls) -> bool:
        return True
    
    @classmethod
    def styles(cls) -> str:
        return """
        .counters .stat {
            display: flex;
            justify-content: space-between;
            padding: 3px 0;
            border-bottom: 1px solid #eee;
        }
        .counters .count {
            font-weight: bold;
        }
        .counters .state0 { color: #0d0; }
        .counters .state1 { color: #fc0; }
        .counters .state2 { color: #f00; }
        """
    
    def show(self) -> None:
        try:
            # Host-Statistiken
            hosts_up = sites.live().query_value(
                "GET hosts\nStats: state = 0\n"
            )
            hosts_down = sites.live().query_value(
                "GET hosts\nStats: state = 1\n"
            )
            
            # Service-Statistiken
            services_ok = sites.live().query_value(
                "GET services\nStats: state = 0\n"
            )
            services_warn = sites.live().query_value(
                "GET services\nStats: state = 1\n"
            )
            services_crit = sites.live().query_value(
                "GET services\nStats: state = 2\n"
            )
            
            html.open_div(class_="counters")
            
            # Hosts
            html.h3(_("Hosts"))
            
            html.open_div(class_="stat")
            html.write_text(_("UP:"))
            html.span(str(hosts_up), class_="count state0")
            html.close_div()
            
            html.open_div(class_="stat")
            html.write_text(_("DOWN:"))
            html.span(str(hosts_down), class_="count state2")
            html.close_div()
            
            # Services
            html.h3(_("Services"))
            
            html.open_div(class_="stat")
            html.write_text(_("OK:"))
            html.span(str(services_ok), class_="count state0")
            html.close_div()
            
            html.open_div(class_="stat")
            html.write_text(_("WARN:"))
            html.span(str(services_warn), class_="count state1")
            html.close_div()
            
            html.open_div(class_="stat")
            html.write_text(_("CRIT:"))
            html.span(str(services_crit), class_="count state2")
            html.close_div()
            
            html.close_div()
            
        except Exception as e:
            html.show_error(_("Error: %s") % e)
```

---

## ⚠️ Häufige Fehler

### 1. Falscher Pfad

```bash
# FALSCH:
~/local/share/check_mk/web/plugins/sidebar/

# RICHTIG:
~/local/lib/python3/cmk/gui/plugins/sidebar/
```

### 2. Fehlende __init__.py

```bash
# Erstellen:
touch ~/local/lib/python3/cmk/gui/plugins/sidebar/__init__.py
```

### 3. Import-Fehler

```python
# FALSCH:
from cmk.gui.sidebar import SidebarSnapin

# RICHTIG:
from cmk.gui.plugins.sidebar.utils import SidebarSnapin
```

### 4. Registrierung vergessen

```python
# Decorator nicht vergessen!
@snapin_registry.register
class MySnapin(SidebarSnapin):
    ...
```

### 5. type_name() nicht unique

```python
# Muss einzigartig sein:
@staticmethod
def type_name() -> str:
    return "my_unique_snapin_name"  # Kein Konflikt mit anderen
```

---

## 📚 Weitere Ressourcen

### Checkmk Quellcode (Beispiele)

Beste Referenz: Originale Snapins in Checkmk ansehen:

```bash
# Built-in Snapins
ls -la ~/lib/python3/cmk/gui/plugins/sidebar/

# Beispiele:
- bookmarks.py      # Einfaches Beispiel
- performance.py    # Mit Graphen
- views.py          # Mit LiveStatus
- tactical_overview.py  # Komplexes Beispiel
```

### Hilfreiche Imports

```python
from cmk.gui.i18n import _                              # Übersetzungen
from cmk.gui.htmllib.html import html                   # HTML-Rendering
from cmk.gui.plugins.sidebar.utils import (
    SidebarSnapin,                                      # Basis-Klasse
    snapin_registry,                                    # Registry
    link, simplelink, bulletlink, iconlink,            # Link-Helper
    snapin_site_choice,                                # Site-Auswahl
)
from cmk.gui.utils.urls import makeuri_contextless     # URL-Generierung
from cmk.gui.config import user                        # User-Info
import livestatus                                       # LiveStatus-Abfragen
```

---

## 🎓 Best Practices

1. **Immer i18n verwenden**: `_("Text")` für Übersetzungen
2. **Error Handling**: Immer try/except bei externen Daten
3. **Performance**: Bei refresh_regularly() auf schnelle Queries achten
4. **CSS**: Eigene Klassen verwenden, nicht Built-in überschreiben
5. **Permissions**: Sensible Daten mit Permission-Checks schützen
6. **Testing**: In Test-Installation entwickeln
7. **Documentation**: Code dokumentieren für andere Admins

---

## 🚀 Deployment

### Produktiv-Installation

```bash
# 1. Auf Test-System entwickeln
# 2. Testen
# 3. Datei kopieren

# Von Test nach Prod
scp ~/local/lib/python3/cmk/gui/plugins/sidebar/my_snapin.py \
    prod-server:/omd/sites/prod/local/lib/python3/cmk/gui/plugins/sidebar/

# Auf Prod-Server
omd reload apache
```

### Versionierung

```python
# Version im Docstring
"""
Custom Snapin: My Snapin
Version: 1.0.0
Author: Your Name
Date: 2025-02-10
"""
```

---

**Ende der Guideline**

Dieses Dokument basiert auf Checkmk 2.4+ und sollte für alle 2.x Versionen funktionieren.

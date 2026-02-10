Hier ist eine aktuelle **Guideline für die Entwicklung eigener Dashlets** in Checkmk (Stand Februar 2026, Checkmk 2.3.x und 2.4.x).

Leider gibt es **keine offizielle, detaillierte Developer-Dokumentation** speziell für Dashlets in den Checkmk-Docs (docs.checkmk.com). Das Thema wird nur als Endbenutzer-Funktion behandelt. Die beste und aktuellste Informationsquelle ist der **Checkmk-Quellcode** selbst (GitHub-Repository) sowie Community-Beispiele (z. B. aus CMK-exchange).

### 1. Aktueller Stand – Wo liegt der Code?

**Offizieller Checkmk-Quellcode**  
https://github.com/Checkmk/checkmk/tree/master/cmk/gui/dashboard

Wichtige Dateien / Verzeichnisse (Stand master / 2.4-Entwicklung):

- `dashlet/__init__.py`  
- `dashlet/registry.py` → enthält `dashlet_registry` (zentraler Registrierungsmechanismus)
- `dashlet/types.py` → Basisklasse `Dashlet` und viele konkrete Dashlet-Typen
- `dashlet/utils.py`, `dashlet/store.py` usw.

**Typische mitgelieferte Dashlets** (Beispiele zum Anschauen):

- `graph.py` → Single-Metric / Multi-Graph Dashlet
- `view.py` → Embedded View Dashlet
- `url.py` → URL / iframe Dashlet
- `alert_history.py`
- `custom_link.py`
- `hoststats.py`, `servicestats.py`
- `problems.py`
- `monitored_hosts.py` usw.

→ **Fazit:** Die beste Möglichkeit, ein neues Dashlet zu entwickeln, ist, eines der bestehenden Dashlets (z. B. `url.py` oder `custom_link.py`) als Vorlage zu kopieren und anzupassen.

### 2. Datei-Ort für eigene Dashlets

Seit Checkmk 2.0+ (und weiterhin in 2.4):

```text
~/local/lib/python3/cmk/gui/plugins/dashboard/
   └── mein_custom_dashlet.py
```

**Nicht mehr** (alter Weg, wird nicht mehr empfohlen):

```text
~/local/share/check_mk/web/plugins/dashboard/
```

**Schritte zur Erstellung:**

```bash
# Als Site-User
sudo su - <sitename>

mkdir -p ~/local/lib/python3/cmk/gui/plugins/dashboard
touch ~/local/lib/python3/cmk/gui/plugins/dashboard/__init__.py   # leer, aber nötig
touch ~/local/lib/python3/cmk/gui/plugins/dashboard/my_dashlet.py
```

### 3. Minimalbeispiel – Eigenes Dashlet (Checkmk 2.3/2.4)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# my_dashlet.py

from cmk.gui.i18n import _
from cmk.gui.plugins.dashboard import Dashlet, dashlet_registry
from cmk.gui.htmllib.html import html
from cmk.gui.valuespec import (
    Dictionary,
    TextInput,
)


@dashlet_registry.register
class MyCustomDashlet(Dashlet):
    """Minimales eigenes Dashlet-Beispiel"""

    @classmethod
    def dashlet_type_name(cls) -> str:
        """Eindeutiger interner Name – klein geschrieben, keine Sonderzeichen"""
        return "my_custom_dashlet"

    @classmethod
    def title(cls) -> str:
        return _("My Custom Dashlet")

    @classmethod
    def description(cls) -> str:
        return _("Ein einfaches Beispiel-Dashlet mit konfigurierbarem Text")

    @classmethod
    def is_resizable(cls) -> bool:
        return True

    @classmethod
    def initial_size(cls) -> tuple[int, int]:
        return (30, 15)  # Breite × Höhe in Raster-Einheiten

    @classmethod
    def vs_parameters(cls):
        """Valuespec für die Dashlet-Konfiguration (erscheint im Edit-Dialog)"""
        return Dictionary(
            title=_("Custom Dashlet Settings"),
            elements=[
                ("title_text", TextInput(
                    title=_("Angezeigter Text"),
                    size=60,
                    default_value=_("Hello from my custom dashlet!"),
                )),
            ],
            optional_keys=[],
        )

    def show(self) -> None:
        """Haupt-Render-Funktion"""
        params = self._dashlet_spec.get("custom_parameters", {})
        display_text = params.get("title_text", _("No text configured"))

        html.open_div(class_="my_custom_dashlet")
        html.h2(display_text)
        html.write_text(_("This is a custom dashlet running in Checkmk %s") % self.config.version)
        html.close_div()

    @classmethod
    def styles(cls) -> str:
        """Optionales CSS nur für dieses Dashlet"""
        return """
        .my_custom_dashlet {
            padding: 12px;
            background: linear-gradient(135deg, #f0f8ff, #e6f2ff);
            border-radius: 8px;
        }
        .my_custom_dashlet h2 {
            color: #0066cc;
            margin-top: 0;
        }
        """
```

### 4. Wichtige Methoden & Attribute (aktuell in 2.4)

| Methode / Attribut              | Zweck                                                                 | Pflicht? |
|---------------------------------|-----------------------------------------------------------------------|----------|
| `dashlet_type_name()`           | Eindeutiger interner Schlüssel (klein, snake_case)                    | Ja       |
| `title()`                       | Anzeigename im Dashlet-Auswahl-Dialog                                 | Ja       |
| `description()`                 | Tooltip / Hilfe-Text                                                  | Ja       |
| `vs_parameters()`               | Valuespec für Dashlet-Konfiguration (UI-Formular)                     | Nein     |
| `show()`                        | Rendert den Inhalt (meist mit `html.open_div()`, `html.write()` etc.) | Ja       |
| `initial_size()`                | Standardgröße beim Hinzufügen (Breite, Höhe)                          | Nein     |
| `is_resizable()`                | Darf der Benutzer die Größe ändern?                                   | Nein     |
| `styles()`                      | Dashlet-spezifisches CSS                                              | Nein     |
| `allowed_roles()`               | Welche Rollen dürfen dieses Dashlet nutzen?                           | Nein     |

### 5. Häufige Patterns & Tricks

- **Parameter speichern**  
  Die Konfiguration landet in `self._dashlet_spec["custom_parameters"]` (dict)

- **Context nutzen** (Filter, Site, Host/Service-Listen)  
  ```python
  context = self.context()
  hostname = context.get("HOSTNAME")
  ```

- **AJAX-Refresh / periodisches Update**  
  ```python
  @classmethod
  def refresh_regularly(cls) -> bool:
      return True
  ```

- **Dashlet mit View einbetten**  
  Schau in `view.py` – sehr gutes Beispiel für `self._get_view()` und `render_view()`

- **Graph-Dashlet nachbauen**  
  → `graph.py` studieren (nutzt `cmk.gui.graphing` intensiv)

### 6. Deployment & Testing

```bash
# Syntax prüfen
python3 -m py_compile ~/local/lib/python3/cmk/gui/plugins/dashboard/my_dashlet.py

# Cache löschen
rm -rf ~/local/lib/python3/cmk/gui/plugins/dashboard/__pycache__

# Web neu laden
omd reload apache
```

Danach:

1. Dashboard öffnen → Edit → Add dashlet
2. Dein neues Dashlet sollte in der Liste erscheinen (unter „Custom dashlets“ oder alphabetisch)

### 7. Community-Beispiele (CMK-exchange)

https://github.com/bh2005/CMK-exchange/tree/main/dashlets

Enthält (Stand 2026) oft folgende Beispiele:

- `link_dashlet.py` → universeller Link/Button/iframe-Dashlet
- `weather_map.py` → Integration von Netzwerk-Karten
- `custom_text.py` → Markdown/HTML-Box
- `external_content.py` → iframe + URL-Proxy-Varianten

→ Sehr empfehlenswert als Vorlage! Viele davon sind als MKP verpackt.

### 8. Fazit & Empfehlung 2026

- Keine offizielle Guideline → **Quellcode ist die Dokumentation**
- Beste Lernmethode: `url.py`, `custom_link.py` oder `graph.py` kopieren und modifizieren
- Für UI-Parameter → immer `vs_parameters()` mit `Dictionary` nutzen
- Packaging → als **MKP** ausliefern (sehr einfach mit `mkp create`)
- Forum-Beitrag oder GitHub-Issue → wenn etwas unklar ist (z. B. neue Dashlet-Features in 2.4)

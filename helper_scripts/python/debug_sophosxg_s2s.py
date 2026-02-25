#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHECKMK PLUGIN REGISTRATION DEBUGGER – speziell für sophosxg_s2s
Prüft, ob der Check korrekt geladen und registriert wurde
"""

import importlib
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

print("=" * 90)
print("CHECKMK PLUGIN REGISTRATION DEBUGGER – Sophos XG S2S Tunnel Check")
print("=" * 90)
print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# =====================================================================
# Konfiguration – Pfad zum lokalen Plugin-Verzeichnis
# =====================================================================

PLUGIN_DIR = Path(os.environ.get("OMD_ROOT", "")) / "local" / "lib" / "python3" / "cmk" / "base" / "plugins" / "agent_based"

if not PLUGIN_DIR.exists():
    print(f"FEHLER: Plugin-Verzeichnis nicht gefunden: {PLUGIN_DIR}")
    print("→ Prüfen Sie, ob Sie als Site-Benutzer eingeloggt sind (omd su <site>)")
    sys.exit(1)

PLUGIN_FILE = PLUGIN_DIR / "sophosxg_s2s.py"

# =====================================================================
# Hauptprüfung
# =====================================================================

print(f"Scanning directory: {PLUGIN_DIR}")
print()

if not PLUGIN_FILE.exists():
    print(f"✗ Datei nicht gefunden: {PLUGIN_FILE}")
    print("→ Plugin muss heißen: sophosxg_s2s.py")
    print("→ Und im Verzeichnis liegen: local/lib/python3/cmk/base/plugins/agent_based/")
    sys.exit(1)

print(f"→ Datei gefunden: {PLUGIN_FILE}")
print()

# =====================================================================
# Modul importieren und prüfen
# =====================================================================

module_name = "cmk.base.plugins.agent_based.sophosxg_s2s"

print(f"Versuche Import: {module_name}")

try:
    module = importlib.import_module(module_name)
    print("✓ Modul erfolgreich importiert")
except Exception as e:
    print("✗ Import fehlgeschlagen!")
    print(traceback.format_exc())
    print()
    print("Mögliche Ursachen:")
    print("  - Syntaxfehler im Plugin")
    print("  - Falsche Imports (cmk.agent_based.v2 statt v1)")
    print("  - Dateiname oder Modulname falsch")
    sys.exit(1)

# =====================================================================
# Prüfen der registrierten Objekte
# =====================================================================

print()
print("Prüfe Registrierungen...")

found_section = False
found_plugin = False

# Prüfen auf snmp_section_*
for name in dir(module):
    obj = getattr(module, name)
    if name == "snmp_section_sophosxg_s2s":
        found_section = True
        print("✓ SNMP-Section gefunden: snmp_section_sophosxg_s2s")
    elif name == "check_plugin_sophosxg_s2s":
        found_plugin = True
        print("✓ Check-Plugin gefunden: check_plugin_sophosxg_s2s")

if not found_section:
    print("✗ Keine snmp_section_sophosxg_s2s gefunden!")
    print("→ Muss exakt so heißen und mit register.snmp_section(...) registriert sein")

if not found_plugin:
    print("✗ Kein check_plugin_sophosxg_s2s gefunden!")
    print("→ Muss exakt so heißen und mit register.check_plugin(...) registriert sein")

# =====================================================================
# Zusammenfassung
# =====================================================================

print()
print("=" * 60)
print("ZUSAMMENFASSUNG")
print("=" * 60)

if found_section and found_plugin:
    print("✓ Beide Komponenten erfolgreich registriert")
    print("→ Das Plugin sollte jetzt in Checkmk sichtbar sein")
    print("→ Nächster Schritt: omd reload apache")
    print("→ Dann: Agent neu ausführen → Services suchen nach 'S2S Tunnel'")
else:
    print("✗ Mindestens eine Komponente fehlt oder ist falsch registriert")
    print("→ Bitte Plugin-Code prüfen (Name, register-Aufruf, Imports)")
    print("→ Häufige Fehler:")
    print("   - Falscher Klassen-/Variablenname")
    print("   - register.check_plugin() fehlt")
    print("   - Syntaxfehler vor der Registrierung")

print()
print("Debug beendet.")

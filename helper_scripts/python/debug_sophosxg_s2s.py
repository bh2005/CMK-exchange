#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHECKMK PLUGIN REGISTRATION DEBUGGER – speziell für sophosxg_s2s
Prüft, ob der Check korrekt geladen und registriert wurde
Kompatibel mit CMK 2.4 und 2.5 (prüft beide Plugin-Pfade)
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

OMD_ROOT = os.environ.get("OMD_ROOT", "")
if not OMD_ROOT:
    print("FEHLER: OMD_ROOT Umgebungsvariable nicht gesetzt!")
    print("→ Prüfen Sie, ob Sie als Site-Benutzer eingeloggt sind (omd su <site>)")
    sys.exit(1)

# =====================================================================
# Konfiguration – Plugin-Pfade für CMK 2.4 und 2.5
# CMK 2.4: cmk/base/plugins/agent_based/
# CMK 2.5: cmk_addons/plugins/<name>/agent_based/  (MKP-Pfad)
#           cmk/base/plugins/agent_based/            (weiterhin gültig für Site-Installs)
# =====================================================================

CANDIDATES = [
    # CMK 2.5 MKP-Pfad (empfohlen)
    (
        Path(OMD_ROOT) / "local" / "lib" / "python3" / "cmk_addons" / "plugins" / "sophosxg" / "agent_based",
        "cmk_addons.plugins.sophosxg.agent_based.sophosxg_s2s",
        "CMK 2.5 MKP-Pfad",
    ),
    # CMK 2.4 / Standalone-Pfad (weiterhin gültig in 2.5)
    (
        Path(OMD_ROOT) / "local" / "lib" / "python3" / "cmk" / "base" / "plugins" / "agent_based",
        "cmk.base.plugins.agent_based.sophosxg_s2s",
        "CMK 2.4 Standalone-Pfad",
    ),
]

PLUGIN_DIR = None
module_name = None

for candidate_dir, candidate_module, label in CANDIDATES:
    candidate_file = candidate_dir / "sophosxg_s2s.py"
    if candidate_file.exists():
        PLUGIN_DIR = candidate_dir
        module_name = candidate_module
        print(f"→ Datei gefunden ({label}):")
        print(f"  {candidate_file}")
        print()
        break

if PLUGIN_DIR is None:
    print("✗ Plugin-Datei nicht gefunden!")
    print()
    print("Gesuchte Pfade:")
    for candidate_dir, _, label in CANDIDATES:
        print(f"  [{label}] {candidate_dir / 'sophosxg_s2s.py'}")
    print()
    print("→ CMK 2.5 (MKP): local/lib/python3/cmk_addons/plugins/sophosxg/agent_based/sophosxg_s2s.py")
    print("→ CMK 2.4:       local/lib/python3/cmk/base/plugins/agent_based/sophosxg_s2s.py")
    sys.exit(1)

# =====================================================================
# Modul importieren und prüfen
# =====================================================================

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
    print("  - Falsche Imports (v1 statt v2: 'from cmk.agent_based.v2 import ...')")
    print("  - Dateiname oder Modulname falsch")
    sys.exit(1)

# =====================================================================
# Prüfen der registrierten Objekte (CMK v2 API: Variablennamen)
# =====================================================================

print()
print("Prüfe Registrierungen (CMK agent_based v2 API)...")

found_section = False
found_plugin = False

for name in dir(module):
    if name == "snmp_section_sophosxg_s2s":
        found_section = True
        print("✓ SNMP-Section gefunden: snmp_section_sophosxg_s2s")
    elif name == "check_plugin_sophosxg_s2s":
        found_plugin = True
        print("✓ Check-Plugin gefunden: check_plugin_sophosxg_s2s")

if not found_section:
    print("✗ Keine snmp_section_sophosxg_s2s gefunden!")
    print("→ CMK v2 API: Variable muss so heißen:")
    print("    snmp_section_sophosxg_s2s = SNMPSection(name='sophosxg_s2s', ...)")
    print("→ CMK v1 API (veraltet): register.snmp_section(name='sophosxg_s2s', ...)")

if not found_plugin:
    print("✗ Kein check_plugin_sophosxg_s2s gefunden!")
    print("→ CMK v2 API: Variable muss so heißen:")
    print("    check_plugin_sophosxg_s2s = CheckPlugin(name='sophosxg_s2s', ...)")
    print("→ CMK v1 API (veraltet): register.check_plugin(name='sophosxg_s2s', ...)")

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
    print("→ Nächster Schritt: omd reload apache  (oder: cmk -R)")
    print("→ Dann: Agent neu ausführen → Services suchen nach 'S2S Tunnel'")
else:
    print("✗ Mindestens eine Komponente fehlt oder ist falsch registriert")
    print("→ Bitte Plugin-Code prüfen (Variablenname, Imports, Syntax)")
    print("→ Häufige Fehler:")
    print("   - Variablenname stimmt nicht mit check_plugin_sophosxg_s2s überein")
    print("   - Falscher Import-Pfad (v1 statt v2)")
    print("   - Syntaxfehler vor der Variablendefinition")

print()
print("Debug beendet.")

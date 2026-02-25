#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# debug_snapins.py - Detaillierter Snapin-Import-Debugger

import sys
import os
import importlib
import traceback
from pathlib import Path
from datetime import datetime

print("=" * 90)
print("CHECKMK SIDEBAR SNAPIN REGISTRATION DEBUGGER")
print("=" * 90)
print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# 1. Verzeichnis ermitteln
site_root = os.environ.get('OMD_ROOT')
if not site_root:
    print("ERROR: OMD_ROOT Umgebungsvariable nicht gesetzt!")
    sys.exit(1)

plugin_dir = Path(site_root) / "local" / "lib" / "python3" / "cmk" / "gui" / "plugins" / "sidebar"
print(f"Scanning directory: {plugin_dir}\n")

# 2. Alle .py Dateien finden (außer __init__.py)
py_files = [f for f in plugin_dir.glob("*.py") if f.name != "__init__.py"]

print(f"Found {len(py_files)} Python files:\n")
for f in sorted(py_files):
    print(f"   • {f.name}")

print("\n" + "=" * 90)
print("Testing import of each snapin...\n")

results = []

for py_file in sorted(py_files):
    module_name = py_file.stem
    full_module = f"cmk.gui.plugins.sidebar.{module_name}"
    
    print(f"→ Testing: {module_name}")

    try:
        # Modul importieren
        module = importlib.import_module(full_module)
        print("   ✓ Module imported successfully")

        # Prüfen auf Snapin-Registrierung
        snapin_classes = []
        for name, obj in module.__dict__.items():
            if isinstance(obj, type) and hasattr(obj, 'type_name'):
                snapin_classes.append(name)
        
        if snapin_classes:
            print(f"   ✓ Found snapin class(es): {snapin_classes}")
            results.append((module_name, "SUCCESS", snapin_classes))
        else:
            print("   ⚠ No snapin class found (missing @snapin_registry.register?)")
            results.append((module_name, "NO_SNAPIN", []))

    except ImportError as e:
        print(f"   ✗ ImportError: {e}")
        results.append((module_name, "IMPORT_ERROR", str(e)))
    except Exception as e:
        print(f"   ✗ Exception: {e}")
        traceback.print_exc()
        results.append((module_name, "EXCEPTION", str(e)))

    print("-" * 70)

# 3. Zusammenfassung
print("\n" + "=" * 90)
print("FINAL SUMMARY")
print("=" * 90)

success = [r for r in results if r[1] == "SUCCESS"]
failed = [r for r in results if r[1] != "SUCCESS"]

print(f"Total files scanned     : {len(results)}")
print(f"Successfully loaded     : {len(success)}")
print(f"Failed / problematic    : {len(failed)}\n")

if success:
    print("SUCCESSFUL SNAPINS:")
    for name, _, classes in success:
        print(f"   ✓ {name} → {classes}")

if failed:
    print("\nPROBLEMATIC FILES:")
    for name, status, details in failed:
        print(f"   ✗ {name}: {status}")
        if details:
            print(f"      → {details[:100]}...")

print("\n" + "=" * 90)
print("EMPFEHLUNGEN:")
print("• Wenn ein Snapin 'IMPORT_ERROR' zeigt → falscher Import-Pfad")
print("• Wenn 'NO_SNAPIN' → fehlender @snapin_registry.register")
print("• Wenn 'EXCEPTION' → Syntax- oder Laufzeitfehler in der Datei")
print("=" * 90)

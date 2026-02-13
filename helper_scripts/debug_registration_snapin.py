#!/usr/bin/env python3
# debug_registration_snapin.py - Warum erscheint das Snapin nicht?

import sys
import os

sys.path.insert(0, os.environ['OMD_ROOT'] + '/local/lib/python3')
sys.path.insert(0, os.environ['OMD_ROOT'] + '/lib/python3')

print("=" * 70)
print("CHECKMK SNAPIN REGISTRATION DEBUG")
print("=" * 70)

# 1. Import Registry
print("\n1. Registry Import...")
from cmk.gui.sidebar._snapin import snapin_registry
print(f"✓ snapin_registry imported: {type(snapin_registry)}")

# 2. List all registered snapins BEFORE import
print("\n2. Currently registered snapins BEFORE loading custom:")
registered_before = sorted(snapin_registry.keys())
print(f"   Total: {len(registered_before)}")
for name in registered_before[:5]:
    print(f"   - {name}")
print(f"   ... ({len(registered_before) - 5} more)")

# 3. Try to import the custom snapin
print("\n3. Attempting to import ticket_test...")
try:
    from cmk.gui.plugins.sidebar.ticket_test import MiniTestSnapin
    print(f"✓ Import successful: {MiniTestSnapin}")
    print(f"  - Class name: {MiniTestSnapin.__name__}")
    print(f"  - type_name: {MiniTestSnapin.type_name()}")
    print(f"  - title: {MiniTestSnapin.title()}")
    print(f"  - Has show(): {hasattr(MiniTestSnapin, 'show')}")
except Exception as e:
    print(f"✗ Import FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Check if it's registered AFTER import
print("\n4. Registered snapins AFTER loading custom:")
registered_after = sorted(snapin_registry.keys())
print(f"   Total: {len(registered_after)}")

# 5. Check if our snapin was added
new_snapins = set(registered_after) - set(registered_before)
if new_snapins:
    print(f"\n✓ NEW snapins registered:")
    for name in new_snapins:
        print(f"   - {name}")
else:
    print(f"\n✗ NO new snapins registered!")

# 6. Check specifically for our snapin
print("\n5. Checking for 'mini_test'...")
if 'mini_test' in snapin_registry:
    print("✓ 'mini_test' IS registered!")
    snapin = snapin_registry['mini_test']
    print(f"   Type: {type(snapin)}")
    print(f"   Title: {snapin.title()}")
    print(f"   Description: {snapin.description()}")
else:
    print("✗ 'mini_test' NOT registered!")
    print("\nSearching for similar names...")
    for name in registered_after:
        if 'test' in name.lower() or 'mini' in name.lower() or 'ticket' in name.lower():
            print(f"   Found: {name}")

# 7. Check file syntax
print("\n6. Checking file syntax...")
ticket_test_path = os.path.join(
    os.environ['OMD_ROOT'],
    'local/lib/python3/cmk/gui/plugins/sidebar/ticket_test.py'
)
print(f"   File: {ticket_test_path}")
print(f"   Exists: {os.path.exists(ticket_test_path)}")
if os.path.exists(ticket_test_path):
    with open(ticket_test_path, 'r') as f:
        content = f.read()
        print(f"   Size: {len(content)} bytes")
        print(f"   Lines: {len(content.splitlines())}")
        
        # Check for key elements
        checks = {
            '@snapin_registry.register': '@snapin_registry.register' in content,
            'CustomizableSidebarSnapin': 'CustomizableSidebarSnapin' in content,
            'def type_name': 'def type_name' in content,
            'def show': 'def show' in content,
        }
        print("\n   Content checks:")
        for check, result in checks.items():
            status = "✓" if result else "✗"
            print(f"   {status} {check}: {result}")

# 8. Try to instantiate
print("\n7. Trying to instantiate snapin...")
try:
    # CustomizableSidebarSnapin might need context
    instance = MiniTestSnapin()
    print(f"✓ Instance created: {type(instance)}")
    print(f"   type_name: {instance.type_name()}")
except Exception as e:
    print(f"✗ Instantiation failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("DEBUG COMPLETE")
print("=" * 70)

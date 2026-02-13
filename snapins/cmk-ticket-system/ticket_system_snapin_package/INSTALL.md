# Quick Installation Guide

## Prerequisites

1. Checkmk 2.4.0 or higher
2. jbelkacemi's Ticket System installed

## Installation Steps

```bash
# 1. Switch to site user
sudo su - <sitename>

# 2. Create directory
mkdir -p ~/local/lib/python3/cmk/gui/plugins/sidebar

# 3. Create __init__.py files
for dir in cmk cmk/gui cmk/gui/plugins cmk/gui/plugins/sidebar; do
    touch ~/local/lib/python3/$dir/__init__.py
done

# 4. Copy snapin
cp ticket_system_snapin.py ~/local/lib/python3/cmk/gui/plugins/sidebar/ticket_system.py

# 5. Verify syntax
python3 -m py_compile ~/local/lib/python3/cmk/gui/plugins/sidebar/ticket_system.py

# 6. Clear cache
find ~/local/lib/python3 -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 7. Reload Apache
omd reload apache
```

## Add to Sidebar

1. Open Checkmk GUI
2. Click "+" in sidebar
3. Search "Ticket System"
4. Add it

## Test Installation

```bash
# Test database access
python3 test_ticket_db.py

# Check logs
tail -f ~/var/log/web.log | grep -i ticket
```

Done! 🎉

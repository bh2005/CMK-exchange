#!/bin/bash

# -----------------------------------------
# Arguments: SITE + PLUGINNAME
# -----------------------------------------
if [[ -z "$1" || -z "$2" ]]; then
    echo "Usage: $0 <site> <pluginname>"
    echo "Example: $0 test xiq"
    exit 1
fi

SITE="$1"
PLUGIN="$2"

BASE="/opt/omd/sites/${SITE}/local/lib/python3/cmk_addons/plugins/${PLUGIN}"
SRC="${BASE}/agent_based"
DST="${BASE}/checkman"

echo "Site:         $SITE"
echo "Pluginname:   $PLUGIN"
echo "Source:       $SRC"
echo "Destination:  $DST"
echo

mkdir -p "$DST"


# -----------------------------------------
# Function: extract plugin name
# Supports:
#   check_plugin_<name> = CheckPlugin(
#   CheckPlugin(name="<name>"
#   inventory_plugin_<name> = InventoryPlugin(
#   InventoryPlugin(name="<name>"
# -----------------------------------------
extract_plugin_name() {
    local file="$1"
    local NAME=""

    # Variant A1: variable starts with check_plugin_
    NAME=$(grep -Po 'check_plugin_\K[A-Za-z0-9_]+' "$file")
    if [[ -n "$NAME" ]]; then
        echo "$NAME"
        return
    fi

    # Variant A2: variable starts with inventory_plugin_
    NAME=$(grep -Po 'inventory_plugin_\K[A-Za-z0-9_]+' "$file")
    if [[ -n "$NAME" ]]; then
        echo "$NAME"
        return
    fi

    # Variant B1: name="xyz" inside CheckPlugin(...)
    NAME=$(grep -Po 'CheckPlugin\s*\(\s*name\s*=\s*"\K[^"]+' "$file")
    if [[ -n "$NAME" ]]; then
        echo "$NAME"
        return
    fi

    # Variant B2: name="xyz" inside InventoryPlugin(...)
    NAME=$(grep -Po 'InventoryPlugin\s*\(\s*name\s*=\s*"\K[^"]+' "$file")
    if [[ -n "$NAME" ]]; then
        echo "$NAME"
        return
    fi

    echo ""
}


# -----------------------------------------
# MAIN LOOP
# -----------------------------------------
for file in "$SRC"/*.py; do
    filename=$(basename "$file")
    echo "Processing: $filename"

    CHECK_NAME=$(extract_plugin_name "$file")

    if [[ -z "$CHECK_NAME" ]]; then
        echo "  -> No CheckPlugin / InventoryPlugin found. Skipping."
        continue
    fi

    target="${DST}/${CHECK_NAME}"

    if [[ -e "$target" ]]; then
        echo "  -> [SKIP] ${CHECK_NAME} (already exists)"
    else
        echo "  -> [NEW]  Creating ${target}"

        cat > "$target" <<EOF
title: ${CHECK_NAME}
agents: piggyback
catalog: custom/${PLUGIN}
license: GPLv2
distribution: check_mk
description:
 This man page was auto-generated for plugin '${CHECK_NAME}'.
 Please update this description manually.

discovery:
 One service or inventory entry is created.
EOF

        # Clean unsafe characters (Windows CP1252, BOM, HTML entities)
        sed -i 's/\r$//' "$target"
        sed -i 's/\xEF\xBB\xBF//g' "$target"
        sed -i 's/\x96/-/g' "$target"
        sed -i 's/\x97/-/g' "$target"
        sed -i 's/\x91/'\''/g' "$target"
        sed -i 's/\x92/'\''/g' "$target"
        sed -i 's/\x93/"/g' "$target"
        sed -i 's/\x94/"/g' "$target"
        sed -i 's/&gt;/>/g' "$target"
        sed -i 's/&lt;/</g' "$target"
    fi
done

echo
echo "Done."
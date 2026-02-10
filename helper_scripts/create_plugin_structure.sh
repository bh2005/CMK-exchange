#!/bin/bash

# ----------------------------------------------------------
#  Create Checkmk extension folder structure for a plugin
#  Usage: ./create_plugin_structure.sh <pluginname>
# ----------------------------------------------------------

if [[ -z "$1" ]]; then
    echo "Usage: $0 <pluginname>"
    echo "Example: $0 xiq"
    exit 1
fi

PLUGIN="$1"

# Base folder inside the site environment
BASE_DIR="$HOME/local/lib/python3/cmk_addons/plugins/${PLUGIN}"

echo "Creating plugin folder structure for plugin: ${PLUGIN}"
echo "Base directory: ${BASE_DIR}"
echo

# List all required subdirectories according to Checkmk plugin API layout:
DIRS=(
    "agent_based"
    "checkman"
    "graphing"
    "inventory"
    "libexec"
    "rulesets"
    "server_side_calls"
    "web"
)

# Create directories
for d in "${DIRS[@]}"; do
    TARGET="${BASE_DIR}/${d}"
    if [[ -d "$TARGET" ]]; then
        echo "[SKIP] $TARGET (already exists)"
    else
        echo "[NEW]  $TARGET"
        mkdir -p "$TARGET"
    fi
done

echo
echo "Plugin directory structure created successfully."
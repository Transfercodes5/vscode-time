#!/bin/bash
# Uninstallation script for vscode-time
# Removes installed files but preserves user data

set -e

# Determine installation directories
LOCAL_BIN="$HOME/.local/bin"
LOCAL_LIB="$HOME/.local/lib/vscode-time"

echo "Uninstalling vscode-time..."
echo ""

# Remove installed files
if [ -f "$LOCAL_BIN/vscode-time" ]; then
    echo "Removing $LOCAL_BIN/vscode-time..."
    rm "$LOCAL_BIN/vscode-time"
fi

if [ -f "$LOCAL_BIN/vscode-time-waybar" ]; then
    echo "Removing $LOCAL_BIN/vscode-time-waybar..."
    rm "$LOCAL_BIN/vscode-time-waybar"
fi

if [ -d "$LOCAL_LIB" ]; then
    echo "Removing $LOCAL_LIB..."
    rm -rf "$LOCAL_LIB"
fi

echo ""
echo "Uninstallation complete!"
echo ""
echo "Note: User data has been preserved:"
echo "  - ~/.local/share/vscode-time/vscode-time.db"
echo "  - ~/.coding-tracker/"
echo "  - ~/.config/vscode-time/"
echo ""
echo "To remove user data manually:"
echo "  rm -rf ~/.local/share/vscode-time"
echo "  rm -rf ~/.coding-tracker"
echo "  rm -rf ~/.config/vscode-time"
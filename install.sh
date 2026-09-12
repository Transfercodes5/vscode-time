#!/bin/bash
# Installation script for vscode-time
# Installs vscode-time to ~/.local/bin and supporting files to ~/.local/lib/vscode-time

set -e

# Determine installation directories
LOCAL_BIN="$HOME/.local/bin"
LOCAL_LIB="$HOME/.local/lib/vscode-time"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing vscode-time..."
echo ""

# Create directories if they don't exist
mkdir -p "$LOCAL_BIN"
mkdir -p "$LOCAL_LIB"

# Install Python source files
echo "Installing application files to $LOCAL_LIB..."
cp -r "$SCRIPT_DIR/src/"* "$LOCAL_LIB/"

# Install the main CLI
echo "Installing CLI to $LOCAL_BIN/vscode-time..."
cat > "$LOCAL_BIN/vscode-time" << 'INSTALLEOF'
#!/usr/bin/env python3
"""vscode-time CLI - Local coding time tracker."""

import sys
import os

INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(os.path.dirname(INSTALL_DIR), "lib", "vscode-time")

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from vscode_time_cli import main

if __name__ == "__main__":
    main()
INSTALLEOF

chmod +x "$LOCAL_BIN/vscode-time"

# Install the Waybar formatter
echo "Installing Waybar formatter to $LOCAL_BIN/vscode-time-waybar..."
cat > "$LOCAL_BIN/vscode-time-waybar" << 'EOF'
#!/usr/bin/env python3
"""Waybar formatter for vscode-time."""

import sys
import os
import json
import subprocess
from pathlib import Path


def find_vscode_time():
    """Find the vscode-time executable."""
    # Check if vscode-time is in PATH
    try:
        result = subprocess.run(
            ["which", "vscode-time"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Check common locations
    common_paths = [
        Path.home() / ".local" / "bin" / "vscode-time",
        Path("/usr/local/bin/vscode-time"),
        Path("/usr/bin/vscode-time"),
    ]
    
    for path in common_paths:
        if path.exists():
            return str(path)
    
    return None


def get_status():
    """Get status from vscode-time."""
    vscode_time = find_vscode_time()
    if not vscode_time:
        return None
    
    try:
        result = subprocess.run(
            [vscode_time, "status", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        return json.loads(result.stdout)
        
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None


def format_waybar_output(status):
    """Format status for Waybar display."""
    if not status:
        return {
            "text": "󰄉 ?",
            "tooltip": "vscode-time unavailable",
            "class": "error"
        }
    
    coding_duration = status.get("coding_duration", "0s")
    goal_duration = status.get("goal_duration", "0s")
    goal_met = status.get("goal_met", False)
    goal_percent = status.get("goal_percent", 0)
    current_streak = status.get("current_streak", 0)
    longest_streak = status.get("longest_streak", 0)
    coding_seconds = status.get("coding_seconds", 0)
    
    if coding_seconds == 0:
        text = f"󰄉 0m / {goal_duration}"
    else:
        text = f"󰄉 {coding_duration} / {goal_duration}"
    
    tooltip_lines = [
        f"Coding: {coding_duration}",
        f"Goal: {goal_duration}",
        f"Progress: {goal_percent:.0f}%",
        f"Streak: {current_streak} day{'s' if current_streak != 1 else ''}",
        f"Longest: {longest_streak} day{'s' if longest_streak != 1 else ''}",
    ]
    tooltip = "\n".join(tooltip_lines)
    
    if goal_met:
        css_class = "goal-met"
    elif coding_seconds > 0:
        css_class = "goal-in-progress"
    else:
        css_class = "no-coding"
    
    return {
        "text": text,
        "tooltip": tooltip,
        "class": css_class
    }


def main():
    """Main entry point."""
    status = get_status()
    output = format_waybar_output(status)
    print(json.dumps(output))


if __name__ == "__main__":
    main()
EOF

chmod +x "$LOCAL_BIN/vscode-time-waybar"

echo ""
echo "Installation complete!"
echo ""
echo "Installed files:"
echo "  CLI:      $LOCAL_BIN/vscode-time"
echo "  Waybar:   $LOCAL_BIN/vscode-time-waybar"
echo "  Library:  $LOCAL_LIB/"
echo ""

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    echo "WARNING: $LOCAL_BIN is not in your PATH."
    echo ""
    echo "Add it to your shell configuration:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Then restart your shell or run:"
    echo "  source ~/.bashrc  # or ~/.zshrc, ~/.profile, etc."
else
    echo "✓ $LOCAL_BIN is in your PATH"
fi

echo ""
echo "Verify installation:"
echo "  vscode-time --version"
echo "  vscode-time status"
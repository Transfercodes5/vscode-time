#!/usr/bin/env python3
"""Waybar formatter for vscode-time.

This script reads JSON from vscode-time status --json and formats it
for display in Waybar.

Usage:
    ./vscode-time.sh

Waybar configuration:
    "custom/vscode-time": {
        "exec": "/path/to/waybar/vscode-time.sh",
        "return-type": "json",
        "interval": 60,
        "tooltip": true
    }
"""

import sys
import os
import json
import subprocess
from pathlib import Path


def find_vscode_time():
    """Find the vscode-time executable."""
    # First check relative to this script's parent directory (repository version)
    script_dir = Path(__file__).parent
    vscode_time = script_dir.parent / "vscode-time"
    if vscode_time.exists():
        return str(vscode_time)
    
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
    
    # Extract values
    coding_duration = status.get("coding_duration", "0s")
    goal_duration = status.get("goal_duration", "0s")
    goal_met = status.get("goal_met", False)
    goal_percent = status.get("goal_percent", 0)
    current_streak = status.get("current_streak", 0)
    longest_streak = status.get("longest_streak", 0)
    coding_seconds = status.get("coding_seconds", 0)
    goal_seconds = status.get("goal_seconds", 0)
    
    # Format text display
    if coding_seconds == 0:
        text = f"󰄉 0m / {goal_duration}"
    else:
        text = f"󰄉 {coding_duration} / {goal_duration}"
    
    # Format tooltip
    tooltip_lines = [
        f"Coding: {coding_duration}",
        f"Goal: {goal_duration}",
        f"Progress: {goal_percent:.0f}%",
        f"Streak: {current_streak} day{'s' if current_streak != 1 else ''}",
        f"Longest: {longest_streak} day{'s' if longest_streak != 1 else ''}",
    ]
    tooltip = "\n".join(tooltip_lines)
    
    # Determine CSS class
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
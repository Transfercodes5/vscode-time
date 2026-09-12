# Waybar Integration for vscode-time

This directory contains the Waybar integration for vscode-time.

## Files

- `vscode-time.sh` — Waybar formatter script
- `README.md` — This file

## Setup

### 1. Make the script executable

```bash
chmod +x waybar/vscode-time.sh
```

### 2. Add to Waybar configuration

Add the following to your Waybar configuration file (typically `~/.config/waybar/config`):

```json
"custom/vscode-time": {
    "exec": "/path/to/vscode-time/waybar/vscode-time.sh",
    "return-type": "json",
    "interval": 60,
    "tooltip": true,
    "on-click": "gnome-terminal -- vscode-time status",
    "on-click-right": "gnome-terminal -- vscode-time goal"
}
```

Replace `/path/to/vscode-time/` with the actual path to your vscode-time installation.

### 3. Add module to Waybar modules

Add `custom/vscode-time` to your Waybar modules list:

```json
"modules-left": ["custom/vscode-time", ...],
```

### 4. Reload Waybar

Reload Waybar to apply the changes:

```bash
# For Omarchy/Hyprland
hyprctl reload

# Or restart Waybar
killall waybar && waybar &
```

## Display

The module shows:

```
󰄉 3h 25m / 1h
```

Where:
- `󰄉` is a Nerd Font icon (requires Nerd Font support)
- `3h 25m` is the coding time today
- `/ 1h` is the daily goal

### States

- **Goal met**: `󰄉 3h 25m / 1h` (green/highlighted)
- **Goal in progress**: `󰄉 42m / 1h` (default)
- **No coding**: `󰄉 0m / 1h` (dimmed)
- **Error**: `󰄉 ?` (red)

## Tooltip

Hovering over the module shows:

```
Coding: 3h 25m
Goal: 1h
Progress: 100%
Streak: 2 days
Longest: 2 days
```

## Click Actions

- **Left click**: Opens terminal with `vscode-time status`
- **Right click**: Opens terminal with `vscode-time goal`

## Optional CSS

Add to `~/.config/waybar/style.css`:

```css
#custom-vscode-time {
    padding: 0 8px;
}

#custom-vscode-time.goal-met {
    color: #a6da95;
}

#custom-vscode-time.goal-in-progress {
    color: #eed49f;
}

#custom-vscode-time.no-coding {
    color: #6e738d;
}

#custom-vscode-time.error {
    color: #ed8796;
}
```

## Troubleshooting

### Module not showing

1. Check that the script is executable:
   ```bash
   ls -la waybar/vscode-time.sh
   ```

2. Test the script directly:
   ```bash
   ./waybar/vscode-time.sh
   ```

3. Check Waybar logs for errors.

### Wrong vscode-time version

The script prioritizes the repository version over any installed version in PATH. If you want to use the installed version, ensure the repository's `vscode-time` script is not in the same directory as `waybar/`.

### No icon display

The `󰄉` icon requires a Nerd Font. If you don't have Nerd Font support, the icon will show as a placeholder character. You can replace it with plain text by editing `vscode-time.sh`.
# vscode-time

Local-first coding-time tracker for Linux. Imports activity from the VS Code Coding Tracker extension.

## Features

- Import coding activity from VS Code Coding Tracker
- Daily goals with progress tracking
- Streak tracking (current and longest)
- Statistics (totals, averages, projects, languages)
- Time-range reports (today, yesterday, 7d, 30d)
- JSON/CSV data export
- Waybar integration
- TOML configuration
- Local-only — no network, no telemetry

## Quick Start

```bash
# Install
git clone <repository-url> vscode-time
cd vscode-time
./install.sh

# Import your coding activity
vscode-time sync

# Set a daily goal
vscode-time goal 1h

# Check today's progress
vscode-time today

# View recent history
vscode-time history 7

# View statistics
vscode-time stats
```

## Requirements

- Python 3.11+
- [VS Code Coding Tracker](https://marketplace.visualstudio.com/items?itemName=hangxingliu.coding-tracker) extension
- SQLite (included with Python)

Optional: Waybar for status bar integration

## Installation

```bash
git clone <repository-url> vscode-time
cd vscode-time
./install.sh
```

Installs to:
- `~/.local/bin/vscode-time` — CLI
- `~/.local/bin/vscode-time-waybar` — Waybar formatter
- `~/.local/lib/vscode-time/` — Application library

## Commands

| Command | Description |
|---------|-------------|
| `vscode-time sync` | Import from source tracker |
| `vscode-time today` | Today's progress |
| `vscode-time history [days]` | Daily history |
| `vscode-time goal [duration]` | Show/set daily goal |
| `vscode-time streak` | Current and longest streaks |
| `vscode-time stats` | Overall statistics |
| `vscode-time report [range]` | Range report |
| `vscode-time status [--json]` | Today's status |
| `vscode-time config [key] [val]` | Configuration |
| `vscode-time export --json/--csv` | Export data |

## Waybar

```json
"custom/vscode-time": {
    "exec": "vscode-time-waybar",
    "return-type": "json",
    "interval": 60,
    "tooltip": true
}
```

## Data Locations

| Data | Location |
|------|----------|
| Source tracker | `~/.coding-tracker/*.db` |
| Database | `~/.local/share/vscode-time/vscode-time.db` |
| Configuration | `~/.config/vscode-time/config.toml` |

## Privacy

- Local only — no network, no telemetry
- No source code collection
- No keystroke logging
- Source tracker files are read-only
- No daemon or background process

## Uninstallation

```bash
./uninstall.sh
```

Removes application files. Preserves database, config, and source tracker data.

## Documentation

- [User Guide](USER_GUIDE.md) — Complete usage documentation
- [Waybar Setup](waybar/README.md) — Waybar integration details

## Development

Run tests:
```bash
python3 tests/test_phase4b.py   # Streaks and statistics
python3 tests/test_phase5.py    # Waybar integration
python3 tests/test_phase6a.py   # Installation
python3 tests/test_phase6b.py   # Reports
python3 tests/test_phase6c.py   # Correctness hardening
python3 tests/test_phase7.py    # CLI/UX
python3 tests/test_phase8.py    # Export
python3 tests/test_phase9.py    # Configuration
```

## License

MIT

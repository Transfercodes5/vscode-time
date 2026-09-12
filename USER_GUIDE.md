# vscode-time User Guide

## What is vscode-time?

vscode-time is a local-first coding-time tracker for Linux. It imports coding activity from the [VS Code Coding Tracker extension](https://marketplace.visualstudio.com/items?itemName=hangxingliu.coding-tracker) and provides a CLI to view goals, streaks, statistics, and reports.

vscode-time does not implement independent activity detection. It reads data recorded by the Coding Tracker extension.

## How Time Is Measured

vscode-time uses accumulated activity values recorded by `hangxingliu.vscode-coding-tracker`.

The source tracker records two types of activity:

- **Type 2 (coding/editing)** — Active coding time. Only these records are imported by vscode-time.
- **Type 0 (watching)** — Time spent viewing files without editing. These are ignored.

The duration value in each record is an **accumulated activity counter**, not wall-clock elapsed time. If you edited a file for 5 minutes, then switched away for 10 minutes, then came back and edited for 5 more minutes, the tracker records two separate 5-minute sessions — not a continuous 20-minute block.

Each record's duration is attributed to its **start date in your local timezone**. Records are not split across midnight.

## Requirements

- **Python 3.11+** (for `tomllib` support in configuration)
- **VS Code** with [hangxingliu.vscode-coding-tracker](https://marketplace.visualstudio.com/items?itemName=hangxingliu.coding-tracker) extension installed and running
- **SQLite** (included with Python — no separate installation needed)

Optional:
- **Waybar** for status bar integration
- **Nerd Font** for the Waybar icon

## Installation

```bash
git clone <repository-url> vscode-time
cd vscode-time
./install.sh
```

This installs:
- `~/.local/bin/vscode-time` — CLI
- `~/.local/bin/vscode-time-waybar` — Waybar formatter
- `~/.local/lib/vscode-time/` — Application library

Verify the installation:
```bash
vscode-time --version
```

If `vscode-time: command not found`, ensure `~/.local/bin` is in your PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add that line to your `~/.bashrc` or `~/.zshrc` to make it permanent.

## First-Time Setup

1. Make sure the Coding Tracker extension is installed in VS Code and has recorded some activity.

2. Import your existing coding activity:
```bash
vscode-time sync
```

3. Set a daily goal:
```bash
vscode-time goal 1h
```

4. Check today's progress:
```bash
vscode-time today
```

## Commands

### sync

```bash
vscode-time sync
```

Imports new coding activity from the source tracker's database files in `~/.coding-tracker/`.

Example output:
```
Sync complete
Imported: 13
Existing: 64
Rejected: 2
```

- **Imported**: New records added to the database
- **Existing**: Records already in the database (skipped)
- **Rejected**: Malformed records in the source file (skipped)

Synchronization is incremental. Running it multiple times does not duplicate records. Source files are never modified.

### today

```bash
vscode-time today
```

Shows today's coding time and goal progress.

Example output:
```
Date:     2026-09-12
Goal:     1h
Coding:   344h 26m
Progress: 100%
Status:   COMPLETE
```

### history

```bash
vscode-time history
vscode-time history 7
```

Shows recent daily coding history. Default is 7 days.

Example output:
```
Daily coding history (last 7 days):
----------------------------------------
  2026-09-06           0s
  2026-09-07           0s
  2026-09-08           0s
  2026-09-09           0s
  2026-09-10           0s
  2026-09-11 ✓    63h 53m
  2026-09-12 ✓   344h 26m
```

A checkmark (✓) indicates the daily goal was met.

### goal

```bash
vscode-time goal
vscode-time goal 1h
vscode-time goal 90m
vscode-time goal 5400s
```

Shows or sets the daily coding goal.

Accepted formats:
- `2h` — hours
- `90m` — minutes
- `5400s` — seconds
- `5400` — plain seconds

Valid range: 60 seconds to 86400 seconds (24 hours).

Default: 7200 seconds (2 hours).

Changing the goal does not alter historical coding records. Historical goal evaluation uses the current goal value.

### streak

```bash
vscode-time streak
```

Shows current and longest coding streaks.

Example output:
```
Current streak: 2 days
Longest streak: 2 days

Today:
  344h 26m / 1h ✓
```

A streak counts consecutive days where the daily goal was met. Today counts toward the current streak only if the goal is already met. Days with no coding break a streak.

### stats

```bash
vscode-time stats
```

Shows overall coding statistics.

Example output:
```
Total coding:         408h 20m
Active days:          2
Avg active day:       204h 10m
Avg calendar day:     204h 10m
Longest day:          344h 26m (2026-09-12)
Goal completion:      100%

Projects:
  %2Fhome%2Ftaksh%2FCoding%2FLearn%2Fml-learning-journey 408h 20m

Languages:
  python                         262h 30m
  markdown                       143h 3m
  ignore                         2h 46m
```

### report

```bash
vscode-time report
vscode-time report today
vscode-time report yesterday
vscode-time report 7d
vscode-time report 30d
vscode-time report 7d --json
```

Shows a detailed coding report for a time range. Default range is `7d`.

The report includes:
- Total coding time
- Active days vs calendar days
- Averages
- Goal completion
- Current and longest streaks
- Daily breakdown
- Project breakdown
- Language breakdown

### status

```bash
vscode-time status
vscode-time status --json
```

Shows today's coding status. The `--json` flag outputs machine-readable JSON for integrations like Waybar.

Example JSON output:
```json
{
  "date": "2026-09-12",
  "coding_seconds": 1240000,
  "coding_duration": "344h 26m",
  "goal_seconds": 3600,
  "goal_duration": "1h",
  "goal_progress": 344.444,
  "goal_percent": 100.0,
  "goal_met": true,
  "current_streak": 2,
  "longest_streak": 2
}
```

### export

```bash
vscode-time export --json
vscode-time export --csv
vscode-time export --json 7d
vscode-time export --csv 30d
```

Exports coding session data. Requires exactly one format flag (`--json` or `--csv`).

Supported ranges: `today`, `yesterday`, `7d`, `30d`. Without a range, exports all sessions.

JSON export includes metadata:
```json
{
  "format": "vscode-time-export",
  "version": 1,
  "exported_at": "2026-09-12T09:48:28.199318+00:00",
  "range": {
    "start_date": null,
    "end_date": null,
    "days": null
  },
  "sessions": [...]
}
```

Export is read-only. It does not modify the database or source files.

### config

```bash
vscode-time config
vscode-time config daily_goal_seconds
vscode-time config daily_goal_seconds 7200
```

Shows or sets configuration values.

Currently supported settings:
- `daily_goal_seconds` — Daily coding goal in seconds (default: 7200)

Configuration is stored at `~/.config/vscode-time/config.toml`.

## Waybar Integration

The `vscode-time-waybar` formatter displays coding status in Waybar.

Add to your Waybar configuration (`~/.config/waybar/config`):

```json
"custom/vscode-time": {
    "exec": "vscode-time-waybar",
    "return-type": "json",
    "interval": 60,
    "tooltip": true
}
```

Add `custom/vscode-time` to your Waybar modules list.

The formatter displays:
```
󰄉 3h 25m / 1h
```

Hover tooltip shows detailed stats. CSS classes (`goal-met`, `goal-in-progress`, `no-coding`, `error`) allow custom styling.

See `waybar/README.md` for full setup including CSS examples.

## Configuration

Configuration file: `~/.config/vscode-time/config.toml`

Default configuration:
```toml
daily_goal_seconds = 7200
```

The configuration file is created on first write. If the file is malformed, vscode-time will report an error and exit.

## Data Locations

| Data | Location | Description |
|------|----------|-------------|
| Source tracker | `~/.coding-tracker/*.db` | Files created by the VS Code extension. Never modified by vscode-time. |
| Database | `~/.local/share/vscode-time/vscode-time.db` | Canonical local database with imported sessions. |
| Configuration | `~/.config/vscode-time/config.toml` | User preferences (daily goal). |

## Backup and Recovery

Important data locations:
```
~/.local/share/vscode-time/    # vscode-time database
~/.config/vscode-time/         # Configuration
~/.coding-tracker/             # Source tracker data
```

To back up your data, copy these directories. To restore, copy them back.

Note: Restoring only the vscode-time database without the source tracker data means new syncs will not have the original source history. Restoring only the source tracker data allows re-syncing into a fresh database.

## Uninstallation

```bash
./uninstall.sh
```

Removes:
- `~/.local/bin/vscode-time`
- `~/.local/bin/vscode-time-waybar`
- `~/.local/lib/vscode-time/`

Preserved:
- `~/.local/share/vscode-time/vscode-time.db` (database)
- `~/.coding-tracker/` (source tracker)
- `~/.config/vscode-time/` (configuration)

To remove all data manually:
```bash
rm -rf ~/.local/share/vscode-time
rm -rf ~/.coding-tracker
rm -rf ~/.config/vscode-time
```

## Troubleshooting

### vscode-time: command not found

Ensure `~/.local/bin` is in your PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### No coding time appears

1. Verify the Coding Tracker extension is installed in VS Code.
2. Check that source data exists: `ls ~/.coding-tracker/`
3. Run sync: `vscode-time sync`

### Sync imports nothing new

This is normal if all records are already imported. The "Existing" count shows how many records were already in the database.

### Waybar shows unavailable

Test the formatter directly:
```bash
vscode-time-waybar
```

If it returns an error, check that `vscode-time` is in your PATH and working.

### Configuration error

Inspect your configuration:
```bash
vscode-time config
```

If the configuration file is malformed, delete it and let vscode-time recreate it with defaults.

### Database corruption

Back up your data first, then delete the database to start fresh:
```bash
mv ~/.local/share/vscode-time/vscode-time.db ~/.local/share/vscode-time/vscode-time.db.bak
vscode-time sync
```

This re-imports all records from the source tracker.

## Privacy

vscode-time is local-only:
- No network connections
- No telemetry
- No cloud accounts
- Source tracker files are read-only
- No independent keystroke logger
- No independent activity detector
- No daemon or background process

## Limitations

- **Historical goals**: When you change the daily goal, historical days are evaluated against the current goal value. There is no per-day goal history in v1.
- **Project names**: Project paths from the source tracker may be URL-encoded (e.g., `%2Fhome%2F...`).
- **Time semantics**: Duration values represent accumulated activity, not wall-clock time. Two 5-minute coding sessions with a 10-minute break between them are recorded as 10 minutes of coding, not 20 minutes.
- **Date boundaries**: Records are attributed to their start date. A session that starts before midnight and continues after midnight is counted on the start date.

## FAQ

### Does vscode-time track my keyboard?

No. vscode-time does not implement independent activity tracking. It imports data from the VS Code Coding Tracker extension.

### Does it send my coding data anywhere?

No. The application is local-only with no network access.

### Does it modify the Coding Tracker database?

No. Source files in `~/.coding-tracker/` are read-only.

### Does it measure wall-clock time?

No. Duration values are accumulated activity counters from the source tracker. See "How Time Is Measured" above.

### Where is my data stored?

Three locations:
- `~/.coding-tracker/` — Source tracker data (read-only)
- `~/.local/share/vscode-time/vscode-time.db` — Canonical database
- `~/.config/vscode-time/config.toml` — Configuration

### Can I uninstall it without losing data?

Yes. The uninstall script removes application files but preserves all data and configuration.

### Can I export my data?

Yes. Use `vscode-time export --json` or `vscode-time export --csv`.

### Can I use it without Waybar?

Yes. The CLI works independently. Waybar integration is optional.

## CLI Reference

```
vscode-time --help              Show help
vscode-time --version           Show version

vscode-time sync                Import from source tracker
vscode-time today               Today's progress
vscode-time history [days]      Daily history (default: 7 days)
vscode-time goal [duration]     Show or set daily goal
vscode-time streak              Current and longest streaks
vscode-time stats               Overall statistics
vscode-time report [range]      Range report (default: 7d)
vscode-time status [--json]     Today's status (JSON for Waybar)
vscode-time config [key] [val]  Show or set configuration
vscode-time export --json [r]   Export as JSON
vscode-time export --csv [r]    Export as CSV
```

Supported ranges: `today`, `yesterday`, `7d`, `30d`

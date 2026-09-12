#!/usr/bin/env python3
"""CLI interface for vscode-time.

A local-first coding-time tracker that imports activity from the
VS Code coding tracker extension.
"""

import sys
import os
import json

# Add src to path (for development from repository)
_src_dir = os.path.join(os.path.dirname(__file__), 'src')
if os.path.isdir(_src_dir) and _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from storage.database import Database
from goals import GoalManager, format_seconds, parse_goal_input, InvalidGoalError
from streaks import StreakCalculator
from statistics import StatisticsCalculator
from reports import (
    ReportGenerator, format_report_text, format_report_json,
    InvalidRangeError, SUPPORTED_RANGES
)
from sync.importer import Importer
from adapter.coding_tracker import CodingTrackerAdapter
from export import Exporter, ExportError, SUPPORTED_FORMATS
from config import (
    load_config, Config, ConfigError, ConfigValidationError,
    CONFIG_FILE, SUPPORTED_KEYS, DEFAULTS
)
from pathlib import Path

# Version
VERSION = "0.1.0"

# Program name
PROGRAM = "vscode-time"


def eprint(*args, **kwargs):
    """Print to stderr."""
    print(*args, file=sys.stderr, **kwargs)


def print_help():
    """Print top-level help message."""
    print(f"Usage: {PROGRAM} <command> [options]")
    print()
    print("Commands:")
    print("  sync                Import coding activity from tracker")
    print("  today               Show today's coding time")
    print("  history [days]      Show recent daily history")
    print("  goal [duration]     Show or set daily goal")
    print("  streak              Show coding streaks")
    print("  stats               Show overall statistics")
    print("  report [range]      Show a coding report")
    print("  status              Show today's status")
    print("  export [options]    Export session data")
    print("  config [key] [val]  Show or set configuration")
    print()
    print("Options:")
    print("  --help              Show this help")
    print("  --version           Show version")
    print()
    print("Report/Export ranges: today, yesterday, 7d, 30d")
    print()
    print("Examples:")
    print(f"  {PROGRAM} sync")
    print(f"  {PROGRAM} today")
    print(f"  {PROGRAM} history 7")
    print(f"  {PROGRAM} goal 1h")
    print(f"  {PROGRAM} streak")
    print(f"  {PROGRAM} stats")
    print(f"  {PROGRAM} report 30d")
    print(f"  {PROGRAM} status --json")
    print(f"  {PROGRAM} export --json > backup.json")
    print(f"  {PROGRAM} export --csv > sessions.csv")
    print(f"  {PROGRAM} config")
    print(f"  {PROGRAM} config daily_goal_seconds 7200")


def print_command_help(command):
    """Print help for a specific command."""
    helps = {
        "sync": f"""Usage: {PROGRAM} sync

Import new coding activity from the VS Code coding tracker.

The source database (~/.coding-tracker/) is never modified.

Output:
  Sync complete
  Imported: <new records>
  Existing: <already in database>
  Rejected: <invalid records>""",

        "today": f"""Usage: {PROGRAM} today

Show today's coding time and goal progress.

Output:
  Date, goal, coding time, remaining, progress, status""",

        "history": f"""Usage: {PROGRAM} history [days]

Show recent daily coding history.

Arguments:
  days    Number of days to show (default: 7)""",

        "goal": f"""Usage: {PROGRAM} goal [duration]

Show or set the daily coding goal.

Arguments:
  duration    New goal (e.g., 1h, 90m, 5400s)

Without arguments, shows the current goal.
With an argument, sets a new goal.""",

        "streak": f"""Usage: {PROGRAM} streak

Show current and longest coding streaks.

A streak counts consecutive days where the daily goal was met.""",

        "stats": f"""Usage: {PROGRAM} stats

Show overall coding statistics including totals, averages,
project breakdown, and language breakdown.""",

        "report": f"""Usage: {PROGRAM} report [range] [--json]

Show a coding report for a time range.

Arguments:
  range    Time range (default: 7d)
           Supported: today, yesterday, 7d, 30d

Options:
  --json   Output as JSON""",

        "status": f"""Usage: {PROGRAM} status [--json]

Show today's coding status.

Options:
  --json   Output as JSON (for Waybar)""",

        "export": f"""Usage: {PROGRAM} export --format [range]

Export coding session data.

Options:
  --json   Export as JSON
  --csv    Export as CSV

Arguments:
  range    Time range (default: all)
           Supported: today, yesterday, 7d, 30d

Examples:
  {PROGRAM} export --json > backup.json
  {PROGRAM} export --csv > sessions.csv
  {PROGRAM} export --json 7d > last-week.json

Output goes to stdout. Use shell redirection to save to file.
Export does not modify the database or source files.""",

        "config": f"""Usage: {PROGRAM} config [key] [value]

Show or set configuration values.

Without arguments, shows all configuration.
With one argument, shows that specific setting.
With two arguments, sets the setting.

Supported settings:
  daily_goal_seconds    Daily coding goal in seconds

Examples:
  {PROGRAM} config
  {PROGRAM} config daily_goal_seconds
  {PROGRAM} config daily_goal_seconds 7200

Configuration is stored at: ~/.config/vscode-time/config.toml""",
    }

    if command in helps:
        print(helps[command])
    else:
        eprint(f"Error: no help available for '{command}'")
        sys.exit(1)


def get_db():
    """Get database connection."""
    db_path = Path.home() / ".local" / "share" / "vscode-time" / "vscode-time.db"
    db = Database(db_path)
    db.connect()
    return db


def cmd_goal(args):
    """Handle goal command."""
    if args and args[0] in ("--help", "-h"):
        print_command_help("goal")
        return

    db = get_db()
    manager = GoalManager(db)

    if not args:
        goal = manager.get_goal()
        print(f"Current daily goal: {format_seconds(goal)}")
    else:
        goal_input = args[0]
        try:
            new_goal = manager.set_goal_from_input(goal_input)
            print(f"Daily goal set to: {format_seconds(new_goal)}")
        except InvalidGoalError as e:
            eprint(f"Error: {e}")
            sys.exit(1)

    db.close()


def cmd_today(args):
    """Handle today command."""
    if args and args[0] in ("--help", "-h"):
        print_command_help("today")
        return

    db = get_db()
    manager = GoalManager(db)

    status = manager.get_today_status()
    print(f"Date:     {status.date}")
    print(f"Goal:     {format_seconds(status.goal_seconds)}")
    print(f"Coding:   {format_seconds(status.coding_seconds)}")
    print(f"Progress: {status.progress_percent:.0f}%")
    print(f"Status:   {'COMPLETE' if status.goal_met else 'IN PROGRESS'}")

    db.close()


def cmd_history(args):
    """Handle history command."""
    if args and args[0] in ("--help", "-h"):
        print_command_help("history")
        return

    db = get_db()
    manager = GoalManager(db)

    days = 7
    if args:
        try:
            days = int(args[0])
        except ValueError:
            eprint(f"Error: invalid number of days '{args[0]}'")
            sys.exit(1)

    from datetime import datetime, timedelta
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    history = manager.get_daily_history(start_date, end_date)

    print(f"Daily coding history (last {days} days):")
    print("-" * 40)

    for status in history:
        marker = "✓" if status.goal_met else " "
        print(f"  {status.date} {marker} {format_seconds(status.coding_seconds):>10}")

    db.close()


def cmd_streak(args):
    """Handle streak command."""
    if args and args[0] in ("--help", "-h"):
        print_command_help("streak")
        return

    db = get_db()
    calculator = StreakCalculator(db)

    info = calculator.get_streak_info()
    today = info["today_status"]

    print(f"Current streak: {info['current_streak']} days")
    print(f"Longest streak: {info['longest_streak']} days")
    print()
    print("Today:")
    print(f"  {format_seconds(today.coding_seconds)} / {format_seconds(today.goal_seconds)} {'✓' if today.goal_met else '✗'}")

    db.close()


def cmd_stats(args):
    """Handle stats command."""
    if args and args[0] in ("--help", "-h"):
        print_command_help("stats")
        return

    db = get_db()
    calculator = StatisticsCalculator(db)

    stats = calculator.calculate()

    print(f"Total coding:         {format_seconds(stats.total_seconds)}")
    print(f"Active days:          {stats.active_days}")
    print(f"Avg active day:       {format_seconds(int(stats.avg_per_active_day))}")
    print(f"Avg calendar day:     {format_seconds(int(stats.avg_per_calendar_day))}")
    print(f"Longest day:          {format_seconds(stats.longest_day_seconds)} ({stats.longest_day_date})")
    print(f"Goal completion:      {stats.goal_completion_rate:.0f}%")

    if stats.projects:
        print()
        print("Projects:")
        for p in stats.projects:
            proj_name = p['project'].split('/')[-1] if p['project'] else '(no project)'
            print(f"  {proj_name:30s} {format_seconds(p['total_seconds'])}")

    if stats.languages:
        print()
        print("Languages:")
        for l in stats.languages:
            print(f"  {l['language']:30s} {format_seconds(l['total_seconds'])}")

    db.close()


def cmd_report(args):
    """Handle report command."""
    if args and args[0] in ("--help", "-h"):
        print_command_help("report")
        return

    json_mode = "--json" in args
    range_str = "7d"

    for arg in args:
        if not arg.startswith("-"):
            range_str = arg
            break

    db = get_db()

    try:
        generator = ReportGenerator(db)
        report = generator.generate(range_str)

        if json_mode:
            print(json.dumps(format_report_json(report), indent=2))
        else:
            print(format_report_text(report))

    except InvalidRangeError as e:
        eprint(f"Error: {e}")
        sys.exit(1)
    finally:
        db.close()


def cmd_sync(args):
    """Handle sync command."""
    if args and args[0] in ("--help", "-h"):
        print_command_help("sync")
        return

    db = get_db()
    adapter = CodingTrackerAdapter()
    importer = Importer(db, adapter)

    result = importer.sync()

    print("Sync complete")
    print(f"Imported: {result.new_imported}")
    print(f"Existing: {result.already_imported}")
    if result.rejected:
        print(f"Rejected: {result.rejected}")

    if result.errors:
        for error in result.errors:
            eprint(f"Error: {error}")

    db.close()


def cmd_status(args):
    """Handle status command."""
    if args and args[0] in ("--help", "-h"):
        print_command_help("status")
        return

    json_mode = "--json" in args

    db = get_db()

    if json_mode:
        try:
            goal_manager = GoalManager(db)
            streak_calculator = StreakCalculator(db)

            today_status = goal_manager.get_today_status()
            streak_info = streak_calculator.get_streak_info()

            if today_status.goal_seconds > 0:
                goal_progress = today_status.coding_seconds / today_status.goal_seconds
            else:
                goal_progress = 1.0 if today_status.coding_seconds > 0 else 0.0

            status_json = {
                "date": today_status.date,
                "coding_seconds": today_status.coding_seconds,
                "coding_duration": format_seconds(today_status.coding_seconds),
                "goal_seconds": today_status.goal_seconds,
                "goal_duration": format_seconds(today_status.goal_seconds),
                "goal_progress": round(goal_progress, 3),
                "goal_percent": min(today_status.progress_percent, 100),
                "goal_met": today_status.goal_met,
                "current_streak": streak_info["current_streak"],
                "longest_streak": streak_info["longest_streak"],
            }

            print(json.dumps(status_json, indent=2))

        except Exception as e:
            error_json = {
                "error": str(e),
                "date": "",
                "coding_seconds": 0,
                "coding_duration": "0s",
                "goal_seconds": 0,
                "goal_duration": "0s",
                "goal_progress": 0,
                "goal_percent": 0,
                "goal_met": False,
                "current_streak": 0,
                "longest_streak": 0,
            }
            print(json.dumps(error_json, indent=2))
            sys.exit(1)
        finally:
            db.close()
    else:
        goal_manager = GoalManager(db)
        streak_calculator = StreakCalculator(db)

        today_status = goal_manager.get_today_status()
        streak_info = streak_calculator.get_streak_info()

        print("Today")
        print("─────")
        print(f"Coding:   {format_seconds(today_status.coding_seconds)}")
        print(f"Goal:     {format_seconds(today_status.goal_seconds)}")
        print(f"Progress: {today_status.progress_percent:.0f}%")
        print(f"Status:   {'COMPLETE' if today_status.goal_met else 'IN PROGRESS'}")
        print(f"Streak:   {streak_info['current_streak']} days")

        db.close()


def cmd_export(args):
    """Handle export command."""
    if args and args[0] in ("--help", "-h"):
        print_command_help("export")
        return

    json_mode = "--json" in args
    csv_mode = "--csv" in args

    # Must have exactly one format
    if not json_mode and not csv_mode:
        eprint("Error: export requires a format flag")
        eprint("Usage: vscode-time export --json [range]")
        eprint("       vscode-time export --csv [range]")
        sys.exit(1)

    if json_mode and csv_mode:
        eprint("Error: cannot use both --json and --csv")
        sys.exit(1)

    # Find range argument (first non-flag argument)
    range_str = None
    for arg in args:
        if not arg.startswith("-"):
            range_str = arg
            break

    db = get_db()

    try:
        exporter = Exporter(db)

        if json_mode:
            output = exporter.export_json(range_str)
        else:
            output = exporter.export_csv(range_str)

        print(output, end="")

    except InvalidRangeError as e:
        eprint(f"Error: {e}")
        sys.exit(1)
    except ExportError as e:
        eprint(f"Error: {e}")
        sys.exit(1)
    finally:
        db.close()


def cmd_config(args):
    """Handle config command."""
    if args and args[0] in ("--help", "-h"):
        print_command_help("config")
        return

    try:
        config = load_config()
    except ConfigError as e:
        eprint(f"Error: {e}")
        sys.exit(1)

    if not args:
        # Show all configuration
        print("Configuration")
        print("─────────────")
        for key in sorted(DEFAULTS.keys()):
            value = config.get(key)
            if key == "daily_goal_seconds":
                print(f"  Daily goal: {format_seconds(value)}")
            else:
                print(f"  {key}: {value}")
        print()
        print(f"Config file: {CONFIG_FILE}")
        return

    if len(args) == 1:
        # Show specific setting
        key = args[0]
        if key not in SUPPORTED_KEYS:
            eprint(f"Error: unknown configuration key '{key}'")
            eprint(f"Supported keys: {', '.join(sorted(SUPPORTED_KEYS))}")
            sys.exit(1)

        value = config.get(key)
        if key == "daily_goal_seconds":
            print(f"{format_seconds(value)}")
        else:
            print(f"{value}")
        return

    if len(args) >= 2:
        # Set specific setting
        key = args[0]
        value_str = args[1]

        if key not in SUPPORTED_KEYS:
            eprint(f"Error: unknown configuration key '{key}'")
            eprint(f"Supported keys: {', '.join(sorted(SUPPORTED_KEYS))}")
            sys.exit(1)

        try:
            if key == "daily_goal_seconds":
                from goals import parse_goal_input, validate_goal
                value = parse_goal_input(value_str)
                validate_goal(value)
                config.set(key, value)
                config.save()
                print(f"Daily goal set to: {format_seconds(value)}")
            else:
                eprint(f"Error: cannot set key '{key}' via CLI")
                sys.exit(1)
        except InvalidGoalError as e:
            eprint(f"Error: {e}")
            sys.exit(1)
        except ConfigError as e:
            eprint(f"Error: {e}")
            sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_help()
        return

    command = sys.argv[1].lower()
    args = sys.argv[2:]

    # Handle flags
    if command in ("--help", "-h"):
        print_help()
        return

    if command in ("--version", "-v"):
        print(f"{PROGRAM} {VERSION}")
        return

    commands = {
        "goal": cmd_goal,
        "today": cmd_today,
        "history": cmd_history,
        "streak": cmd_streak,
        "stats": cmd_stats,
        "report": cmd_report,
        "sync": cmd_sync,
        "status": cmd_status,
        "export": cmd_export,
        "config": cmd_config,
        "help": lambda a: print_help(),
    }

    if command in commands:
        commands[command](args)
    else:
        eprint(f"Error: unknown command '{command}'")
        eprint(f"Run '{PROGRAM} --help' for available commands.")
        sys.exit(1)


if __name__ == "__main__":
    main()

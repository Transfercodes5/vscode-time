"""Goal management for vscode-time.

This module handles daily coding goals, including persistence,
validation, and status calculations.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from storage.database import Database


# Default daily goal: 2 hours in seconds
DEFAULT_DAILY_GOAL_SECONDS = 7200

# Goal setting key in database (for backward compatibility)
GOAL_KEY = "daily_goal_seconds"

# Minimum allowed goal: 1 minute
MIN_GOAL_SECONDS = 60

# Maximum allowed goal: 24 hours
MAX_GOAL_SECONDS = 86400


class GoalError(Exception):
    """Base error for goal operations."""
    pass


class InvalidGoalError(GoalError):
    """Raised when goal value is invalid."""
    pass


def validate_goal(goal_seconds: int) -> bool:
    """Validate a goal value.

    Args:
        goal_seconds: Goal in seconds.

    Returns:
        True if valid.

    Raises:
        InvalidGoalError: If goal is invalid.
    """
    if not isinstance(goal_seconds, int):
        raise InvalidGoalError(f"Goal must be an integer, got {type(goal_seconds).__name__}")

    if goal_seconds < 0:
        raise InvalidGoalError(f"Goal cannot be negative, got {goal_seconds}")

    if goal_seconds > MAX_GOAL_SECONDS:
        raise InvalidGoalError(f"Goal cannot exceed 24 hours ({MAX_GOAL_SECONDS}s), got {goal_seconds}")

    return True


def parse_goal_input(input_str: str) -> int:
    """Parse human-readable goal input to seconds.

    Supported formats:
        - "2h" (hours)
        - "90m" (minutes)
        - "5400s" (seconds)
        - "7200" (plain seconds)

    Args:
        input_str: Human-readable goal string.

    Returns:
        Goal in seconds.

    Raises:
        InvalidGoalError: If input cannot be parsed or is negative.
    """
    input_str = input_str.strip().lower()

    if not input_str:
        raise InvalidGoalError("Empty goal input")

    # Check for negative sign before parsing
    if input_str.startswith("-"):
        raise InvalidGoalError(f"Goal cannot be negative: {input_str}")

    # Try plain seconds first
    if input_str.isdigit():
        return int(input_str)

    # Try suffix formats
    if input_str.endswith("h"):
        try:
            hours = float(input_str[:-1])
            return int(hours * 3600)
        except ValueError:
            raise InvalidGoalError(f"Invalid hours format: {input_str}")

    if input_str.endswith("m"):
        try:
            minutes = float(input_str[:-1])
            return int(minutes * 60)
        except ValueError:
            raise InvalidGoalError(f"Invalid minutes format: {input_str}")

    if input_str.endswith("s"):
        try:
            return int(input_str[:-1])
        except ValueError:
            raise InvalidGoalError(f"Invalid seconds format: {input_str}")

    raise InvalidGoalError(f"Unknown goal format: {input_str}")


def format_seconds(seconds: int) -> str:
    """Format seconds as human-readable duration.

    Examples:
        0 → "0s"
        300 → "5m"
        3600 → "1h"
        3900 → "1h 5m"
        370000 → "102h 46m"

    Args:
        seconds: Duration in seconds.

    Returns:
        Human-readable string.
    """
    if seconds < 0:
        return f"-{format_seconds(-seconds)}"

    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    parts = []
    if h > 0:
        parts.append(f"{h}h")
    if m > 0:
        parts.append(f"{m}m")
    if s > 0 and not parts:
        parts.append(f"{s}s")

    return " ".join(parts) if parts else "0s"


class DailyStatus:
    """Status for a single day's coding progress."""

    __slots__ = (
        "date",
        "goal_seconds",
        "coding_seconds",
    )

    def __init__(self, date: str, goal_seconds: int, coding_seconds: int):
        self.date = date
        self.goal_seconds = goal_seconds
        self.coding_seconds = coding_seconds

    @property
    def remaining_seconds(self) -> int:
        """Seconds remaining to meet goal."""
        return max(self.goal_seconds - self.coding_seconds, 0)

    @property
    def progress_percent(self) -> float:
        """Progress toward goal as percentage (0-100)."""
        if self.goal_seconds <= 0:
            return 100.0 if self.coding_seconds > 0 else 0.0
        return min((self.coding_seconds / self.goal_seconds) * 100, 100.0)

    @property
    def goal_met(self) -> bool:
        """Whether the goal was met."""
        return self.coding_seconds >= self.goal_seconds

    def __repr__(self):
        return (
            f"DailyStatus(date={self.date}, goal={self.goal_seconds}s, "
            f"coding={self.coding_seconds}s, met={self.goal_met})"
        )


class GoalManager:
    """Manager for daily coding goals."""

    def __init__(self, db: Database):
        self.db = db
        self._config = None

    def _get_config(self):
        """Lazy-load configuration."""
        if self._config is None:
            try:
                from config import load_config
                self._config = load_config()
            except Exception:
                self._config = None
        return self._config

    def get_goal(self) -> int:
        """Get current daily goal in seconds.

        Checks config file first, then falls back to database setting.

        Returns:
            Current goal in seconds, or default if not set.
        """
        # Try config file first
        config = self._get_config()
        if config is not None:
            value = config.get("daily_goal_seconds")
            if value is not None:
                try:
                    validate_goal(value)
                    return value
                except InvalidGoalError:
                    pass

        # Fall back to database
        value = self.db.get_setting(GOAL_KEY)
        if value is None:
            return DEFAULT_DAILY_GOAL_SECONDS

        try:
            goal = int(value)
            validate_goal(goal)
            return goal
        except (ValueError, InvalidGoalError):
            return DEFAULT_DAILY_GOAL_SECONDS

    def set_goal(self, goal_seconds: int) -> None:
        """Set daily goal.

        Saves to both config file and database for backward compatibility.

        Args:
            goal_seconds: Goal in seconds.

        Raises:
            InvalidGoalError: If goal is invalid.
        """
        validate_goal(goal_seconds)

        # Save to config file
        config = self._get_config()
        if config is not None:
            try:
                config.set("daily_goal_seconds", goal_seconds)
                config.save()
            except Exception as e:
                import sys
                print(f"Warning: Could not save to config file: {e}", file=sys.stderr)

        # Also save to database for backward compatibility
        self.db.set_setting(GOAL_KEY, str(goal_seconds))

    def set_goal_from_input(self, input_str: str) -> int:
        """Set goal from human-readable input.

        Args:
            input_str: Goal string (e.g., "2h", "90m").

        Returns:
            Goal in seconds that was set.

        Raises:
            InvalidGoalError: If input cannot be parsed.
        """
        goal = parse_goal_input(input_str)
        validate_goal(goal)
        self.set_goal(goal)
        return goal

    def get_today_status(self) -> DailyStatus:
        """Get today's coding status.

        Uses local timezone for date calculation.

        Returns:
            DailyStatus for today.
        """
        # Get today's date in local timezone
        local_tz = datetime.now().astimezone().tzinfo
        today = datetime.now(local_tz).strftime("%Y-%m-%d")

        # Get coding seconds for today
        coding_seconds = self._get_coding_seconds_for_date(today)

        # Get current goal
        goal = self.get_goal()

        return DailyStatus(
            date=today,
            goal_seconds=goal,
            coding_seconds=coding_seconds,
        )

    def get_status_for_date(self, date_str: str) -> DailyStatus:
        """Get coding status for a specific date.

        Args:
            date_str: Date string (YYYY-MM-DD).

        Returns:
            DailyStatus for the specified date.
        """
        coding_seconds = self._get_coding_seconds_for_date(date_str)
        goal = self.get_goal()

        return DailyStatus(
            date=date_str,
            goal_seconds=goal,
            coding_seconds=coding_seconds,
        )

    def get_daily_history(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list:
        """Get daily coding history.

        Args:
            start_date: Start date (YYYY-MM-DD). If None, uses earliest available.
            end_date: End date (YYYY-MM-DD). If None, uses today.

        Returns:
            List of DailyStatus objects, one per day.
        """
        # Get all daily totals from database
        daily_totals = self.db.get_daily_totals()

        if not daily_totals:
            return []

        # Determine date range
        if start_date is None:
            start_date = daily_totals[-1]["day"]  # Oldest

        if end_date is None:
            end_date = datetime.now().astimezone().strftime("%Y-%m-%d")

        # Build date range
        goal = self.get_goal()
        result = []
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        # Create lookup from database totals
        totals_lookup = {d["day"]: d["total_seconds"] for d in daily_totals}

        while current_date <= end:
            date_str = current_date.strftime("%Y-%m-%d")
            coding_seconds = totals_lookup.get(date_str, 0)

            result.append(DailyStatus(
                date=date_str,
                goal_seconds=goal,
                coding_seconds=coding_seconds,
            ))

            current_date += timedelta(days=1)

        return result

    def _get_coding_seconds_for_date(self, date_str: str) -> int:
        """Get coding seconds for a specific date using local timezone.

        Args:
            date_str: Date string (YYYY-MM-DD).

        Returns:
            Total coding seconds for the date.
        """
        cursor = self.db._conn.cursor()

        # Convert date string to epoch ms range using local timezone
        local_tz = datetime.now().astimezone().tzinfo
        dt_start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=local_tz)
        dt_end = dt_start + timedelta(days=1)

        start_ms = int(dt_start.timestamp() * 1000)
        end_ms = int(dt_end.timestamp() * 1000)

        cursor.execute("""
            SELECT COALESCE(SUM(duration_seconds), 0) as total
            FROM coding_sessions
            WHERE start_time >= ? AND start_time < ?
        """, (start_ms, end_ms))

        row = cursor.fetchone()
        return row["total"]
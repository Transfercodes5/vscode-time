"""Basic statistics for vscode-time.

This module calculates coding statistics from persisted sessions.

Statistics implemented:
- Total coding time
- Active days (days with coding > 0)
- Average coding time per active day
- Average coding time per calendar day
- Longest coding day
- Goal completion rate
- Project breakdown
- Language breakdown
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from storage.database import Database
from goals import GoalManager


class Statistics:
    """Container for coding statistics."""

    __slots__ = (
        "total_seconds",
        "active_days",
        "calendar_days",
        "avg_per_active_day",
        "avg_per_calendar_day",
        "longest_day_seconds",
        "longest_day_date",
        "goal_completion_rate",
        "projects",
        "languages",
    )

    def __init__(
        self,
        total_seconds: int,
        active_days: int,
        calendar_days: int,
        avg_per_active_day: float,
        avg_per_calendar_day: float,
        longest_day_seconds: int,
        longest_day_date: str,
        goal_completion_rate: float,
        projects: List[Dict],
        languages: List[Dict],
    ):
        self.total_seconds = total_seconds
        self.active_days = active_days
        self.calendar_days = calendar_days
        self.avg_per_active_day = avg_per_active_day
        self.avg_per_calendar_day = avg_per_calendar_day
        self.longest_day_seconds = longest_day_seconds
        self.longest_day_date = longest_day_date
        self.goal_completion_rate = goal_completion_rate
        self.projects = projects
        self.languages = languages


class StatisticsCalculator:
    """Calculate statistics from persisted coding sessions."""

    def __init__(self, db: Database):
        self.db = db
        self.goal_manager = GoalManager(db)

    def calculate(self) -> Statistics:
        """Calculate all statistics.

        Returns:
            Statistics object with all computed values.
        """
        # Get total coding time
        total_seconds = self.db.get_total_coding_seconds()
        
        # Get daily totals
        daily_totals = self.db.get_daily_totals()
        
        # Calculate active days (days with coding > 0)
        active_days = sum(1 for d in daily_totals if d["total_seconds"] > 0)
        
        # Calculate calendar days (from first coding day to today)
        if daily_totals:
            first_date = daily_totals[-1]["day"]  # Oldest
            today = datetime.now().astimezone().strftime("%Y-%m-%d")
            start = datetime.strptime(first_date, "%Y-%m-%d")
            end = datetime.strptime(today, "%Y-%m-%d")
            calendar_days = (end - start).days + 1
        else:
            calendar_days = 0
        
        # Calculate averages
        avg_per_active_day = total_seconds / active_days if active_days > 0 else 0
        avg_per_calendar_day = total_seconds / calendar_days if calendar_days > 0 else 0
        
        # Find longest coding day
        if daily_totals:
            longest_day = max(daily_totals, key=lambda x: x["total_seconds"])
            longest_day_seconds = longest_day["total_seconds"]
            longest_day_date = longest_day["day"]
        else:
            longest_day_seconds = 0
            longest_day_date = ""
        
        # Calculate goal completion rate
        goal_completion_rate = self._calculate_goal_completion_rate()
        
        # Get project breakdown
        projects = self.db.get_project_totals()
        
        # Get language breakdown
        languages = self._get_language_totals()
        
        return Statistics(
            total_seconds=total_seconds,
            active_days=active_days,
            calendar_days=calendar_days,
            avg_per_active_day=avg_per_active_day,
            avg_per_calendar_day=avg_per_calendar_day,
            longest_day_seconds=longest_day_seconds,
            longest_day_date=longest_day_date,
            goal_completion_rate=goal_completion_rate,
            projects=projects,
            languages=languages,
        )

    def _calculate_goal_completion_rate(self) -> float:
        """Calculate goal completion rate.

        Returns:
            Percentage of days with goal met (0-100).
        """
        # Get date range
        daily_totals = self.db.get_daily_totals()
        if not daily_totals:
            return 0.0
        
        start_date = daily_totals[-1]["day"]  # Oldest
        end_date = datetime.now().astimezone().strftime("%Y-%m-%d")
        
        # Get all daily statuses
        statuses = self.goal_manager.get_daily_history(start_date, end_date)
        
        if not statuses:
            return 0.0
        
        # Count completed days
        completed_days = sum(1 for s in statuses if s.goal_met)
        
        return (completed_days / len(statuses)) * 100

    def _get_language_totals(self) -> List[Dict]:
        """Get total coding seconds per language.

        Returns:
            List of dictionaries with language and total_seconds.
        """
        cursor = self.db._conn.cursor()
        cursor.execute("""
            SELECT
                language,
                SUM(duration_seconds) as total_seconds,
                COUNT(*) as session_count
            FROM coding_sessions
            GROUP BY language
            ORDER BY total_seconds DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
"""Reporting and analytics for vscode-time.

This module provides time-range reports that analyze existing SQLite data.
It does NOT introduce new activity tracking.

Supported ranges:
- today: Current local calendar date
- yesterday: Previous local calendar date
- 7d: Current date plus preceding 6 calendar days (total = 7)
- 30d: Current date plus preceding 29 calendar days (total = 30)

Default range: 7d
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from storage.database import Database
from goals import GoalManager, DailyStatus, format_seconds
from streaks import StreakCalculator


# Supported time ranges
SUPPORTED_RANGES = ["today", "yesterday", "7d", "30d"]
DEFAULT_RANGE = "7d"


class InvalidRangeError(Exception):
    """Raised when an invalid report range is specified."""
    pass


@dataclass
class TimeRange:
    """Represents a time range for reporting."""
    
    name: str
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    days: int        # Number of calendar days
    
    def __repr__(self):
        return f"TimeRange({self.name}, {self.start_date} → {self.end_date}, {self.days} days)"


def parse_range(range_str: str) -> TimeRange:
    """Parse a range string into a TimeRange object.
    
    Args:
        range_str: One of "today", "yesterday", "7d", "30d"
        
    Returns:
        TimeRange object
        
    Raises:
        InvalidRangeError: If range_str is not supported
    """
    if range_str not in SUPPORTED_RANGES:
        raise InvalidRangeError(
            f"Invalid report range: {range_str}\n"
            f"Supported ranges: {', '.join(SUPPORTED_RANGES)}"
        )
    
    local_tz = datetime.now().astimezone().tzinfo
    today = datetime.now(local_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    
    if range_str == "today":
        start = today
        end = today
        days = 1
    elif range_str == "yesterday":
        start = today - timedelta(days=1)
        end = today - timedelta(days=1)
        days = 1
    elif range_str == "7d":
        start = today - timedelta(days=6)
        end = today
        days = 7
    elif range_str == "30d":
        start = today - timedelta(days=29)
        end = today
        days = 30
    else:
        raise InvalidRangeError(f"Invalid report range: {range_str}")
    
    return TimeRange(
        name=range_str,
        start_date=start.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d"),
        days=days,
    )


@dataclass
class DailyBreakdown:
    """Daily breakdown for a single day."""
    
    date: str
    coding_seconds: int
    goal_seconds: int
    goal_met: bool
    
    @property
    def coding_duration(self) -> str:
        return format_seconds(self.coding_seconds)
    
    @property
    def goal_duration(self) -> str:
        return format_seconds(self.goal_seconds)


@dataclass
class ProjectBreakdown:
    """Project breakdown entry."""
    
    project: str
    total_seconds: int
    
    @property
    def duration(self) -> str:
        return format_seconds(self.total_seconds)
    
    @property
    def display_name(self) -> str:
        """Extract short project name from full path."""
        if self.project:
            return self.project.split('/')[-1]
        return "(no project)"


@dataclass
class LanguageBreakdown:
    """Language breakdown entry."""
    
    language: str
    total_seconds: int
    
    @property
    def duration(self) -> str:
        return format_seconds(self.total_seconds)


@dataclass
class Report:
    """Complete report for a time range."""
    
    # Range information
    range_name: str
    start_date: str
    end_date: str
    calendar_days: int
    
    # Aggregate metrics
    total_coding_seconds: int
    active_days: int
    average_per_active_day_seconds: float
    average_per_calendar_day_seconds: float
    
    # Goal metrics
    goal_seconds: int
    goal_completed_days: int
    goal_completion_rate: float
    
    # Streak information (global)
    current_streak: int
    longest_streak: int
    
    # Breakdowns
    daily: List[DailyBreakdown]
    projects: List[ProjectBreakdown]
    languages: List[LanguageBreakdown]
    
    @property
    def total_coding_duration(self) -> str:
        return format_seconds(self.total_coding_seconds)
    
    @property
    def goal_duration(self) -> str:
        return format_seconds(self.goal_seconds)
    
    @property
    def average_per_active_day(self) -> str:
        return format_seconds(int(self.average_per_active_day_seconds))
    
    @property
    def average_per_calendar_day(self) -> str:
        return format_seconds(int(self.average_per_calendar_day_seconds))


class ReportGenerator:
    """Generate reports from persisted coding sessions."""
    
    def __init__(self, db: Database):
        self.db = db
        self.goal_manager = GoalManager(db)
        self.streak_calculator = StreakCalculator(db)
    
    def generate(self, range_str: str = DEFAULT_RANGE) -> Report:
        """Generate a report for the specified time range.
        
        Args:
            range_str: Time range string ("today", "yesterday", "7d", "30d")
            
        Returns:
            Report object with all metrics
        """
        # Parse time range
        time_range = parse_range(range_str)
        
        # Get daily statuses for the range
        daily_statuses = self.goal_manager.get_daily_history(
            time_range.start_date,
            time_range.end_date
        )
        
        # Calculate aggregate metrics
        total_coding_seconds = sum(s.coding_seconds for s in daily_statuses)
        active_days = sum(1 for s in daily_statuses if s.coding_seconds > 0)
        
        # Calculate averages
        avg_per_active_day = (
            total_coding_seconds / active_days if active_days > 0 else 0
        )
        avg_per_calendar_day = (
            total_coding_seconds / time_range.days if time_range.days > 0 else 0
        )
        
        # Get goal information
        goal_seconds = self.goal_manager.get_goal()
        goal_completed_days = sum(1 for s in daily_statuses if s.goal_met)
        goal_completion_rate = (
            (goal_completed_days / len(daily_statuses) * 100) 
            if daily_statuses else 0
        )
        
        # Get global streak information
        current_streak = self.streak_calculator.get_current_streak()
        longest_streak = self.streak_calculator.get_longest_streak()
        
        # Build daily breakdown
        daily_breakdown = [
            DailyBreakdown(
                date=s.date,
                coding_seconds=s.coding_seconds,
                goal_seconds=s.goal_seconds,
                goal_met=s.goal_met,
            )
            for s in daily_statuses
        ]
        
        # Get project breakdown for the range
        projects = self._get_project_breakdown(time_range)
        
        # Get language breakdown for the range
        languages = self._get_language_breakdown(time_range)
        
        return Report(
            range_name=time_range.name,
            start_date=time_range.start_date,
            end_date=time_range.end_date,
            calendar_days=time_range.days,
            total_coding_seconds=total_coding_seconds,
            active_days=active_days,
            average_per_active_day_seconds=avg_per_active_day,
            average_per_calendar_day_seconds=avg_per_calendar_day,
            goal_seconds=goal_seconds,
            goal_completed_days=goal_completed_days,
            goal_completion_rate=goal_completion_rate,
            current_streak=current_streak,
            longest_streak=longest_streak,
            daily=daily_breakdown,
            projects=projects,
            languages=languages,
        )
    
    def _get_project_breakdown(self, time_range: TimeRange) -> List[ProjectBreakdown]:
        """Get project breakdown for the time range.
        
        Args:
            time_range: Time range to analyze
             
        Returns:
            List of ProjectBreakdown objects sorted by total_seconds DESC
        """
        cursor = self.db._conn.cursor()
        
        # Convert date range to epoch ms
        local_tz = datetime.now().astimezone().tzinfo
        dt_start = datetime.strptime(time_range.start_date, "%Y-%m-%d").replace(tzinfo=local_tz)
        dt_end = (datetime.strptime(time_range.end_date, "%Y-%m-%d") + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, tzinfo=local_tz
        )
        
        start_ms = int(dt_start.timestamp() * 1000)
        end_ms = int(dt_end.timestamp() * 1000)
        
        cursor.execute("""
            SELECT
                project,
                SUM(duration_seconds) as total_seconds
            FROM coding_sessions
            WHERE start_time >= ? AND start_time < ?
            GROUP BY project
            ORDER BY total_seconds DESC, project ASC
        """, (start_ms, end_ms))
        
        return [
            ProjectBreakdown(project=row["project"], total_seconds=row["total_seconds"])
            for row in cursor.fetchall()
        ]
    
    def _get_language_breakdown(self, time_range: TimeRange) -> List[LanguageBreakdown]:
        """Get language breakdown for the time range.
        
        Args:
            time_range: Time range to analyze
             
        Returns:
            List of LanguageBreakdown objects sorted by total_seconds DESC
        """
        cursor = self.db._conn.cursor()
        
        # Convert date range to epoch ms
        local_tz = datetime.now().astimezone().tzinfo
        dt_start = datetime.strptime(time_range.start_date, "%Y-%m-%d").replace(tzinfo=local_tz)
        dt_end = (datetime.strptime(time_range.end_date, "%Y-%m-%d") + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, tzinfo=local_tz
        )
        
        start_ms = int(dt_start.timestamp() * 1000)
        end_ms = int(dt_end.timestamp() * 1000)
        
        cursor.execute("""
            SELECT
                language,
                SUM(duration_seconds) as total_seconds
            FROM coding_sessions
            WHERE start_time >= ? AND start_time < ?
            GROUP BY language
            ORDER BY total_seconds DESC, language ASC
        """, (start_ms, end_ms))
        
        return [
            LanguageBreakdown(language=row["language"], total_seconds=row["total_seconds"])
            for row in cursor.fetchall()
        ]


def format_report_text(report: Report) -> str:
    """Format a report as human-readable text.
    
    Args:
        report: Report object
        
    Returns:
        Formatted text string
    """
    lines = []
    
    # Header
    lines.append("Coding Report")
    lines.append("=" * 40)
    lines.append("")
    
    # Period
    lines.append(f"Period: {report.start_date} → {report.end_date}")
    lines.append("")
    
    # Summary metrics
    lines.append(f"Total coding       {report.total_coding_duration}")
    lines.append(f"Active days        {report.active_days} / {report.calendar_days}")
    lines.append(f"Average active     {report.average_per_active_day}")
    lines.append(f"Average calendar   {report.average_per_calendar_day}")
    lines.append("")
    
    # Goal
    lines.append(f"Goal               {report.goal_duration}")
    lines.append(f"Completed          {report.goal_completed_days} / {report.calendar_days}")
    lines.append(f"Completion rate    {report.goal_completion_rate:.1f}%")
    lines.append("")
    
    # Streak
    lines.append("Streak")
    lines.append(f"Current            {report.current_streak} days")
    lines.append(f"Longest            {report.longest_streak} days")
    lines.append("")
    
    # Daily breakdown
    lines.append("Daily")
    lines.append("-" * 40)
    for day in report.daily:
        status = "✓" if day.goal_met else "—"
        lines.append(f"{day.date}         {day.coding_duration:>10}      {status}")
    lines.append("")
    
    # Project breakdown
    if report.projects:
        lines.append("Projects")
        lines.append("-" * 40)
        for proj in report.projects:
            lines.append(f"{proj.display_name:30s}  {proj.duration}")
        lines.append("")
    
    # Language breakdown
    if report.languages:
        lines.append("Languages")
        lines.append("-" * 40)
        for lang in report.languages:
            lines.append(f"{lang.language:30s}  {lang.duration}")
        lines.append("")
    
    return "\n".join(lines)


def format_report_json(report: Report) -> Dict:
    """Format a report as JSON-serializable dictionary.
    
    Args:
        report: Report object
        
    Returns:
        Dictionary suitable for JSON serialization
    """
    return {
        "range": report.range_name,
        "start_date": report.start_date,
        "end_date": report.end_date,
        "calendar_days": report.calendar_days,
        "total_coding_seconds": report.total_coding_seconds,
        "total_coding_duration": report.total_coding_duration,
        "active_days": report.active_days,
        "average_per_active_day_seconds": int(report.average_per_active_day_seconds),
        "average_per_active_day": report.average_per_active_day,
        "average_per_calendar_day_seconds": int(report.average_per_calendar_day_seconds),
        "average_per_calendar_day": report.average_per_calendar_day,
        "goal_seconds": report.goal_seconds,
        "goal_duration": report.goal_duration,
        "goal_completed_days": report.goal_completed_days,
        "goal_completion_rate": round(report.goal_completion_rate, 3),
        "current_streak": report.current_streak,
        "longest_streak": report.longest_streak,
        "daily": [
            {
                "date": day.date,
                "coding_seconds": day.coding_seconds,
                "coding_duration": day.coding_duration,
                "goal_seconds": day.goal_seconds,
                "goal_met": day.goal_met,
            }
            for day in report.daily
        ],
        "projects": [
            {
                "project": proj.project,
                "display_name": proj.display_name,
                "total_seconds": proj.total_seconds,
                "duration": proj.duration,
            }
            for proj in report.projects
        ],
        "languages": [
            {
                "language": lang.language,
                "total_seconds": lang.total_seconds,
                "duration": lang.duration,
            }
            for lang in report.languages
        ],
    }
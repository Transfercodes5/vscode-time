"""Streak calculations for vscode-time.

This module implements streak tracking based on daily goal completion.

Streak Semantics:
- A day is "completed" when coding_seconds >= daily_goal_seconds
- A day with no coding (coding_seconds = 0) breaks a streak
- Current streak: consecutive completed days ending today
- Longest streak: maximum consecutive completed days in history
- Today counts toward current streak only if goal is already met
- Future dates never affect streak calculations
- Historical days use the current goal (no goal history in v1)
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from storage.database import Database
from goals import GoalManager, DailyStatus


class StreakCalculator:
    """Calculate streaks from persisted coding sessions and goals."""

    def __init__(self, db: Database):
        self.db = db
        self.goal_manager = GoalManager(db)

    def get_daily_goal_statuses(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[DailyStatus]:
        """Get daily goal completion status for a date range.

        Args:
            start_date: Start date (YYYY-MM-DD). If None, uses earliest available.
            end_date: End date (YYYY-MM-DD). If None, uses today.

        Returns:
            List of DailyStatus objects with goal_met status.
        """
        return self.goal_manager.get_daily_history(start_date, end_date)

    def get_current_streak(self) -> int:
        """Get current streak of consecutive completed days.

        Counts backward from today. Today counts only if goal is met.
        Stops at the first incomplete day.

        Returns:
            Number of consecutive completed days.
        """
        # Get today's status
        today_status = self.goal_manager.get_today_status()
        
        # Start from today
        current_date = datetime.strptime(today_status.date, "%Y-%m-%d")
        
        # If today's goal is not met, streak is 0
        if not today_status.goal_met:
            return 0
        
        # Count consecutive completed days backward from today
        streak = 1  # Today is completed
        current_date -= timedelta(days=1)
        
        while True:
            date_str = current_date.strftime("%Y-%m-%d")
            status = self.goal_manager.get_status_for_date(date_str)
            
            # Stop if we hit an incomplete day or no coding
            if not status.goal_met:
                break
            
            streak += 1
            current_date -= timedelta(days=1)
            
            # Safety limit to prevent infinite loops
            if streak > 1000:
                break
        
        return streak

    def get_longest_streak(self) -> int:
        """Get longest streak of consecutive completed days in history.

        Scans all available history to find the maximum streak.

        Returns:
            Maximum number of consecutive completed days.
        """
        # Get all daily statuses
        daily_totals = self.db.get_daily_totals()
        
        if not daily_totals:
            return 0
        
        # Get date range
        start_date = daily_totals[-1]["day"]  # Oldest
        end_date = datetime.now().astimezone().strftime("%Y-%m-%d")
        
        # Get all statuses
        statuses = self.goal_manager.get_daily_history(start_date, end_date)
        
        if not statuses:
            return 0
        
        # Find longest streak
        longest = 0
        current_streak = 0
        
        for status in statuses:
            if status.goal_met:
                current_streak += 1
                longest = max(longest, current_streak)
            else:
                current_streak = 0
        
        return longest

    def get_streak_info(self) -> dict:
        """Get comprehensive streak information.

        Returns:
            Dictionary with current_streak, longest_streak, and today_status.
        """
        today_status = self.goal_manager.get_today_status()
        current_streak = self.get_current_streak()
        longest_streak = self.get_longest_streak()
        
        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "today_status": today_status,
        }
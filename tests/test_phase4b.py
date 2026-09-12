#!/usr/bin/env python3
"""Comprehensive tests for Phase 4B - Streaks & Basic Statistics.

This script tests all streak and statistics functionality.
"""

import sys
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from storage.database import Database
from goals import GoalManager, DailyStatus, format_seconds
from streaks import StreakCalculator
from statistics import StatisticsCalculator


def create_test_db():
    """Create a temporary test database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        return Path(f.name)


def delete_test_db(db_path):
    """Delete test database file."""
    if db_path.exists():
        db_path.unlink()


def create_mock_session(start_time_ms, duration_seconds, language="python", project="/test/project"):
    """Create a mock coding session for testing."""
    class MockSession:
        def __init__(self):
            self.record_id = f"test_{start_time_ms}"
            self.session_type = 2
            self.start_time = start_time_ms
            self.duration_seconds = duration_seconds
            self.language = language
            self.file = "/test/file.py"
            self.project = project
            self.vcs = "git"
            self.line_count = 100
            self.char_count = 1000
            self.source_file = "/test/source.db"
    return MockSession()


def date_to_ms(date_str, hour=12):
    """Convert date string to milliseconds since epoch."""
    from datetime import timezone
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=hour, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def test_streak_no_history():
    """Test streaks with no history."""
    print("1. STREAK NO HISTORY TEST")
    db_path = create_test_db()
    
    try:
        db = Database(db_path)
        db.connect()
        
        calculator = StreakCalculator(db)
        
        current = calculator.get_current_streak()
        longest = calculator.get_longest_streak()
        
        print(f"   Current streak: {current} (expected: 0)")
        print(f"   Longest streak: {longest} (expected: 0)")
        assert current == 0, f"Expected current streak 0, got {current}"
        assert longest == 0, f"Expected longest streak 0, got {longest}"
        
        print("   PASS")
        db.close()
    finally:
        delete_test_db(db_path)


def test_streak_one_completed_day():
    """Test streaks with one completed day."""
    print("\n2. STREAK ONE COMPLETED DAY TEST")
    db_path = create_test_db()
    
    try:
        db = Database(db_path)
        db.connect()
        manager = GoalManager(db)
        
        # Set goal to 1 hour
        manager.set_goal(3600)
        
        # Add a completed day (yesterday)
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        session = create_mock_session(date_to_ms(yesterday), 7200)  # 2 hours
        db.insert_coding_session(session)
        
        calculator = StreakCalculator(db)
        
        current = calculator.get_current_streak()
        longest = calculator.get_longest_streak()
        
        print(f"   Current streak: {current} (expected: 0)")
        print(f"   Longest streak: {longest} (expected: 1)")
        assert current == 0, f"Expected current streak 0, got {current}"
        assert longest == 1, f"Expected longest streak 1, got {longest}"
        
        print("   PASS")
        db.close()
    finally:
        delete_test_db(db_path)


def test_streak_consecutive_days():
    """Test streaks with consecutive completed days."""
    print("\n3. STREAK CONSECUTIVE DAYS TEST")
    db_path = create_test_db()
    
    try:
        db = Database(db_path)
        db.connect()
        manager = GoalManager(db)
        
        # Set goal to 1 hour
        manager.set_goal(3600)
        
        # Add 3 consecutive completed days (today, yesterday, day before)
        for i in range(3):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            session = create_mock_session(date_to_ms(date), 7200)  # 2 hours
            db.insert_coding_session(session)
        
        calculator = StreakCalculator(db)
        
        current = calculator.get_current_streak()
        longest = calculator.get_longest_streak()
        
        print(f"   Current streak: {current} (expected: 3)")
        print(f"   Longest streak: {longest} (expected: 3)")
        assert current == 3, f"Expected current streak 3, got {current}"
        assert longest == 3, f"Expected longest streak 3, got {longest}"
        
        print("   PASS")
        db.close()
    finally:
        delete_test_db(db_path)


def test_streak_missed_day():
    """Test streaks with a missed day in between."""
    print("\n4. STREAK MISSED DAY TEST")
    db_path = create_test_db()
    
    try:
        db = Database(db_path)
        db.connect()
        manager = GoalManager(db)
        
        # Set goal to 1 hour
        manager.set_goal(3600)
        
        # Add completed days: today, yesterday (skip day before), day-3
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        day3 = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        
        session = create_mock_session(date_to_ms(today), 7200)
        db.insert_coding_session(session)
        
        session = create_mock_session(date_to_ms(yesterday), 7200)
        db.insert_coding_session(session)
        
        session = create_mock_session(date_to_ms(day3), 7200)
        db.insert_coding_session(session)
        
        calculator = StreakCalculator(db)
        
        current = calculator.get_current_streak()
        longest = calculator.get_longest_streak()
        
        print(f"   Current streak: {current} (expected: 2)")
        print(f"   Longest streak: {longest} (expected: 2)")
        assert current == 2, f"Expected current streak 2, got {current}"
        assert longest == 2, f"Expected longest streak 2, got {longest}"
        
        print("   PASS")
        db.close()
    finally:
        delete_test_db(db_path)


def test_streak_today_incomplete():
    """Test streaks when today's goal is not met."""
    print("\n5. STREAK TODAY INCOMPLETE TEST")
    db_path = create_test_db()
    
    try:
        db = Database(db_path)
        db.connect()
        manager = GoalManager(db)
        
        # Set goal to 1 hour
        manager.set_goal(3600)
        
        # Add completed days: yesterday, day before
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        day2 = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        
        session = create_mock_session(date_to_ms(yesterday), 7200)
        db.insert_coding_session(session)
        
        session = create_mock_session(date_to_ms(day2), 7200)
        db.insert_coding_session(session)
        
        # Today has only 30 minutes (not completed)
        today = datetime.now().strftime("%Y-%m-%d")
        session = create_mock_session(date_to_ms(today), 1800)  # 30 minutes
        db.insert_coding_session(session)
        
        calculator = StreakCalculator(db)
        
        current = calculator.get_current_streak()
        longest = calculator.get_longest_streak()
        
        print(f"   Current streak: {current} (expected: 0)")
        print(f"   Longest streak: {longest} (expected: 2)")
        assert current == 0, f"Expected current streak 0, got {current}"
        assert longest == 2, f"Expected longest streak 2, got {longest}"
        
        print("   PASS")
        db.close()
    finally:
        delete_test_db(db_path)


def test_streak_today_completed():
    """Test streaks when today's goal is met."""
    print("\n6. STREAK TODAY COMPLETED TEST")
    db_path = create_test_db()
    
    try:
        db = Database(db_path)
        db.connect()
        manager = GoalManager(db)
        
        # Set goal to 1 hour
        manager.set_goal(3600)
        
        # Add completed days: today, yesterday
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        session = create_mock_session(date_to_ms(today), 7200)
        db.insert_coding_session(session)
        
        session = create_mock_session(date_to_ms(yesterday), 7200)
        db.insert_coding_session(session)
        
        calculator = StreakCalculator(db)
        
        current = calculator.get_current_streak()
        longest = calculator.get_longest_streak()
        
        print(f"   Current streak: {current} (expected: 2)")
        print(f"   Longest streak: {longest} (expected: 2)")
        assert current == 2, f"Expected current streak 2, got {current}"
        assert longest == 2, f"Expected longest streak 2, got {longest}"
        
        print("   PASS")
        db.close()
    finally:
        delete_test_db(db_path)


def test_streak_goal_change():
    """Test that goal change affects derived status but not coding history."""
    print("\n7. STREAK GOAL CHANGE TEST")
    db_path = create_test_db()
    
    try:
        db = Database(db_path)
        db.connect()
        manager = GoalManager(db)
        
        # Set goal to 2 hours
        manager.set_goal(7200)
        
        # Add a day with 90 minutes coding
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        session = create_mock_session(date_to_ms(yesterday), 5400)  # 90 minutes
        db.insert_coding_session(session)
        
        # With 2 hour goal, not completed
        calculator = StreakCalculator(db)
        status1 = manager.get_status_for_date(yesterday)
        streak1 = calculator.get_current_streak()
        
        print(f"   Goal=2h, coding=90m: goal_met={status1.goal_met}, streak={streak1}")
        assert not status1.goal_met, "Expected goal not met"
        
        # Change goal to 1 hour
        manager.set_goal(3600)
        
        # With 1 hour goal, now completed
        status2 = manager.get_status_for_date(yesterday)
        streak2 = calculator.get_current_streak()
        
        print(f"   Goal=1h, coding=90m: goal_met={status2.goal_met}, streak={streak2}")
        assert status2.goal_met, "Expected goal met"
        
        # Verify coding seconds unchanged
        assert status1.coding_seconds == status2.coding_seconds, "Coding seconds should not change"
        
        print("   PASS")
        db.close()
    finally:
        delete_test_db(db_path)


def test_statistics_basic():
    """Test basic statistics calculations."""
    print("\n8. STATISTICS BASIC TEST")
    db_path = create_test_db()
    
    try:
        db = Database(db_path)
        db.connect()
        manager = GoalManager(db)
        
        # Set goal to 1 hour
        manager.set_goal(3600)
        
        # Add 3 days of coding
        for i in range(3):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            session = create_mock_session(date_to_ms(date), 7200)  # 2 hours
            db.insert_coding_session(session)
        
        calculator = StatisticsCalculator(db)
        stats = calculator.calculate()
        
        print(f"   Total seconds: {stats.total_seconds} (expected: 21600)")
        print(f"   Active days: {stats.active_days} (expected: 3)")
        print(f"   Avg per active day: {stats.avg_per_active_day:.1f} (expected: 7200.0)")
        print(f"   Goal completion: {stats.goal_completion_rate:.1f}% (expected: 100.0%)")
        
        assert stats.total_seconds == 21600, f"Expected total 21600, got {stats.total_seconds}"
        assert stats.active_days == 3, f"Expected active days 3, got {stats.active_days}"
        assert abs(stats.avg_per_active_day - 7200.0) < 0.1, f"Expected avg 7200.0, got {stats.avg_per_active_day}"
        assert abs(stats.goal_completion_rate - 100.0) < 0.1, f"Expected completion 100.0%, got {stats.goal_completion_rate}"
        
        print("   PASS")
        db.close()
    finally:
        delete_test_db(db_path)


def test_statistics_empty():
    """Test statistics with no data."""
    print("\n9. STATISTICS EMPTY TEST")
    db_path = create_test_db()
    
    try:
        db = Database(db_path)
        db.connect()
        
        calculator = StatisticsCalculator(db)
        stats = calculator.calculate()
        
        print(f"   Total seconds: {stats.total_seconds} (expected: 0)")
        print(f"   Active days: {stats.active_days} (expected: 0)")
        print(f"   Goal completion: {stats.goal_completion_rate:.1f}% (expected: 0.0%)")
        
        assert stats.total_seconds == 0, f"Expected total 0, got {stats.total_seconds}"
        assert stats.active_days == 0, f"Expected active days 0, got {stats.active_days}"
        assert abs(stats.goal_completion_rate - 0.0) < 0.1, f"Expected completion 0.0%, got {stats.goal_completion_rate}"
        
        print("   PASS")
        db.close()
    finally:
        delete_test_db(db_path)


def test_statistics_multiple_projects():
    """Test statistics with multiple projects."""
    print("\n10. STATISTICS MULTIPLE PROJECTS TEST")
    db_path = create_test_db()
    
    try:
        db = Database(db_path)
        db.connect()
        
        # Add sessions from different projects (use different hours to avoid duplicate IDs)
        session1 = create_mock_session(date_to_ms("2026-09-11", hour=10), 7200, project="/home/user/project_a")
        session2 = create_mock_session(date_to_ms("2026-09-11", hour=14), 3600, project="/home/user/project_b")
        session3 = create_mock_session(date_to_ms("2026-09-12", hour=10), 5400, project="/home/user/project_a")
        
        db.insert_coding_session(session1)
        db.insert_coding_session(session2)
        db.insert_coding_session(session3)
        
        calculator = StatisticsCalculator(db)
        stats = calculator.calculate()
        
        print(f"   Projects: {len(stats.projects)} (expected: 2)")
        for p in stats.projects:
            proj_name = p['project'].split('/')[-1]
            print(f"     {proj_name}: {format_seconds(p['total_seconds'])}")
        
        assert len(stats.projects) == 2, f"Expected 2 projects, got {len(stats.projects)}"
        
        print("   PASS")
        db.close()
    finally:
        delete_test_db(db_path)


def test_statistics_multiple_languages():
    """Test statistics with multiple languages."""
    print("\n11. STATISTICS MULTIPLE LANGUAGES TEST")
    db_path = create_test_db()
    
    try:
        db = Database(db_path)
        db.connect()
        
        # Add sessions with different languages (use different hours to avoid duplicate IDs)
        session1 = create_mock_session(date_to_ms("2026-09-11", hour=10), 7200, language="python")
        session2 = create_mock_session(date_to_ms("2026-09-11", hour=14), 3600, language="javascript")
        session3 = create_mock_session(date_to_ms("2026-09-12", hour=10), 5400, language="python")
        
        db.insert_coding_session(session1)
        db.insert_coding_session(session2)
        db.insert_coding_session(session3)
        
        calculator = StatisticsCalculator(db)
        stats = calculator.calculate()
        
        print(f"   Languages: {len(stats.languages)} (expected: 2)")
        for l in stats.languages:
            print(f"     {l['language']}: {format_seconds(l['total_seconds'])}")
        
        assert len(stats.languages) == 2, f"Expected 2 languages, got {len(stats.languages)}"
        
        print("   PASS")
        db.close()
    finally:
        delete_test_db(db_path)


def test_real_data():
    """Test against real database."""
    print("\n12. REAL DATA VERIFICATION")
    db_path = Path.home() / ".local" / "share" / "vscode-time" / "vscode-time.db"
    
    if not db_path.exists():
        print("   SKIP: Real database not found")
        return
    
    db = Database(db_path)
    db.connect()
    
    # Test streaks
    calculator = StreakCalculator(db)
    info = calculator.get_streak_info()
    
    session_count = db.get_session_count()
    total_seconds = db.get_total_coding_seconds()
    
    print(f"   Sessions: {session_count} (> 0)")
    print(f"   Total seconds: {total_seconds} (> 0)")
    print(f"   Current streak: {info['current_streak']} (>= 0)")
    print(f"   Longest streak: {info['longest_streak']} (>= 0)")
    
    assert session_count > 0, f"Expected > 0 sessions, got {session_count}"
    assert total_seconds > 0, f"Expected > 0 seconds, got {total_seconds}"
    assert info['current_streak'] >= 0, f"Expected current streak >= 0, got {info['current_streak']}"
    assert info['longest_streak'] >= 0, f"Expected longest streak >= 0, got {info['longest_streak']}"
    
    # Test statistics
    stats_calc = StatisticsCalculator(db)
    stats = stats_calc.calculate()
    
    print(f"   Active days: {stats.active_days} (> 0)")
    print(f"   Goal completion: {stats.goal_completion_rate:.1f}% (>= 0)")
    
    assert stats.active_days > 0, f"Expected active days > 0, got {stats.active_days}"
    assert stats.goal_completion_rate >= 0, f"Expected completion >= 0, got {stats.goal_completion_rate}"
    
    print("   PASS")
    db.close()


def test_format_seconds():
    """Test format_seconds utility."""
    print("\n13. FORMAT SECONDS TEST")
    
    test_cases = [
        (0, "0s"),
        (30, "30s"),
        (300, "5m"),
        (3600, "1h"),
        (3900, "1h 5m"),
        (370000, "102h 46m"),
    ]
    
    for seconds, expected in test_cases:
        result = format_seconds(seconds)
        print(f"   {seconds}s → {result} (expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("   PASS")


def main():
    """Run all tests."""
    print("=" * 70)
    print("PHASE 4B TESTS - STREAKS & STATISTICS")
    print("=" * 70)
    
    try:
        test_streak_no_history()
        test_streak_one_completed_day()
        test_streak_consecutive_days()
        test_streak_missed_day()
        test_streak_today_incomplete()
        test_streak_today_completed()
        test_streak_goal_change()
        test_statistics_basic()
        test_statistics_empty()
        test_statistics_multiple_projects()
        test_statistics_multiple_languages()
        test_format_seconds()
        test_real_data()
        
        print("\n" + "=" * 70)
        print("ALL TESTS PASSED")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
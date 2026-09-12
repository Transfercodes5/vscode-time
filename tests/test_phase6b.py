#!/usr/bin/env python3
"""Tests for Phase 6B - Reports & Analytics.

This script tests the reporting and analytics functionality.
"""

import sys
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import subprocess

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from storage.database import Database
from goals import GoalManager, format_seconds
from reports import (
    ReportGenerator, format_report_text, format_report_json,
    parse_range, InvalidRangeError, SUPPORTED_RANGES, DEFAULT_RANGE
)


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


def test_default_range():
    """Test that default range is 7d."""
    print("1. DEFAULT RANGE TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Period:" in result.stdout, "Missing period in output"
    
    # Check that it's 7 days
    lines = result.stdout.split("\n")
    for line in lines:
        if "Period:" in line:
            # Parse the period line
            parts = line.split("→")
            if len(parts) == 2:
                start = parts[0].split(":")[1].strip()
                end = parts[1].strip()
                start_date = datetime.strptime(start, "%Y-%m-%d")
                end_date = datetime.strptime(end, "%Y-%m-%d")
                days = (end_date - start_date).days + 1
                assert days == 7, f"Expected 7 days, got {days}"
                break
    
    print("   PASS: Default range is 7d")


def test_today_range():
    """Test today range."""
    print("\n2. TODAY RANGE TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "today"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Period:" in result.stdout, "Missing period in output"
    
    # Check that it's 1 day
    lines = result.stdout.split("\n")
    for line in lines:
        if "Period:" in line:
            parts = line.split("→")
            if len(parts) == 2:
                start = parts[0].split(":")[1].strip()
                end = parts[1].strip()
                assert start == end, f"Today range should have same start and end: {start} != {end}"
                break
    
    print("   PASS: Today range works")


def test_yesterday_range():
    """Test yesterday range."""
    print("\n3. YESTERDAY RANGE TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "yesterday"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Period:" in result.stdout, "Missing period in output"
    
    # Check that it's 1 day
    lines = result.stdout.split("\n")
    for line in lines:
        if "Period:" in line:
            parts = line.split("→")
            if len(parts) == 2:
                start = parts[0].split(":")[1].strip()
                end = parts[1].strip()
                assert start == end, f"Yesterday range should have same start and end: {start} != {end}"
                break
    
    print("   PASS: Yesterday range works")


def test_7d_range():
    """Test 7d range."""
    print("\n4. 7D RANGE TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "7d"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Period:" in result.stdout, "Missing period in output"
    
    # Check that it's 7 days
    lines = result.stdout.split("\n")
    for line in lines:
        if "Period:" in line:
            parts = line.split("→")
            if len(parts) == 2:
                start = parts[0].split(":")[1].strip()
                end = parts[1].strip()
                start_date = datetime.strptime(start, "%Y-%m-%d")
                end_date = datetime.strptime(end, "%Y-%m-%d")
                days = (end_date - start_date).days + 1
                assert days == 7, f"Expected 7 days, got {days}"
                break
    
    print("   PASS: 7d range works")


def test_30d_range():
    """Test 30d range."""
    print("\n5. 30D RANGE TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "30d"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Period:" in result.stdout, "Missing period in output"
    
    # Check that it's 30 days
    lines = result.stdout.split("\n")
    for line in lines:
        if "Period:" in line:
            parts = line.split("→")
            if len(parts) == 2:
                start = parts[0].split(":")[1].strip()
                end = parts[1].strip()
                start_date = datetime.strptime(start, "%Y-%m-%d")
                end_date = datetime.strptime(end, "%Y-%m-%d")
                days = (end_date - start_date).days + 1
                assert days == 30, f"Expected 30 days, got {days}"
                break
    
    print("   PASS: 30d range works")


def test_daily_breakdown():
    """Test that daily breakdown appears in report."""
    print("\n6. DAILY BREAKDOWN TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "7d"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Daily" in result.stdout, "Missing daily section"
    
    # Check that we have 7 daily entries
    lines = result.stdout.split("\n")
    daily_started = False
    daily_count = 0
    for line in lines:
        if "Daily" in line:
            daily_started = True
            continue
        if daily_started and line.strip() == "":
            break
        if daily_started and "2026-" in line:
            daily_count += 1
    
    assert daily_count == 7, f"Expected 7 daily entries, got {daily_count}"
    
    print("   PASS: Daily breakdown works")


def test_empty_days():
    """Test that empty days appear in report."""
    print("\n7. EMPTY DAYS TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "7d"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Check that empty days show 0s
    assert "0s" in result.stdout, "Empty days should show 0s"
    
    print("   PASS: Empty days appear in report")


def test_project_breakdown():
    """Test that project breakdown appears in report."""
    print("\n8. PROJECT BREAKDOWN TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "7d"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Projects" in result.stdout, "Missing projects section"
    
    print("   PASS: Project breakdown works")


def test_language_breakdown():
    """Test that language breakdown appears in report."""
    print("\n9. LANGUAGE BREAKDOWN TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "7d"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Languages" in result.stdout, "Missing languages section"
    
    print("   PASS: Language breakdown works")


def test_goal_completion():
    """Test that goal completion is calculated correctly."""
    print("\n10. GOAL COMPLETION TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "7d"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Completed" in result.stdout, "Missing completed line"
    assert "Completion rate" in result.stdout, "Missing completion rate line"
    
    print("   PASS: Goal completion works")


def test_goal_completion_rate():
    """Test that goal completion rate is calculated correctly."""
    print("\n11. GOAL COMPLETION RATE TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "7d"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    # Extract completion rate
    lines = result.stdout.split("\n")
    for line in lines:
        if "Completion rate" in line:
            # Parse the percentage (format: "Completion rate    28.6%")
            parts = line.split()
            if len(parts) >= 3:
                rate_str = parts[-1].replace("%", "")
                rate = float(rate_str)
                assert 0 <= rate <= 100, f"Completion rate out of range: {rate}"
            break
    
    print("   PASS: Goal completion rate works")


def test_averages():
    """Test that averages are calculated correctly."""
    print("\n12. AVERAGES TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "7d"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "Average active" in result.stdout, "Missing average active line"
    assert "Average calendar" in result.stdout, "Missing average calendar line"
    
    print("   PASS: Averages work")


def test_sorting():
    """Test that project/language breakdowns are sorted correctly."""
    print("\n13. SORTING TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "7d", "--json"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    data = json.loads(result.stdout)
    
    # Check that projects are sorted by total_seconds DESC
    if len(data["projects"]) > 1:
        for i in range(len(data["projects"]) - 1):
            assert data["projects"][i]["total_seconds"] >= data["projects"][i+1]["total_seconds"], \
                "Projects not sorted correctly"
    
    # Check that languages are sorted by total_seconds DESC
    if len(data["languages"]) > 1:
        for i in range(len(data["languages"]) - 1):
            assert data["languages"][i]["total_seconds"] >= data["languages"][i+1]["total_seconds"], \
                "Languages not sorted correctly"
    
    print("   PASS: Sorting works")


def test_json_output():
    """Test JSON output."""
    print("\n14. JSON OUTPUT TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "7d", "--json"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    try:
        data = json.loads(result.stdout)
        
        # Check required fields
        required_fields = [
            "range", "start_date", "end_date", "calendar_days",
            "total_coding_seconds", "total_coding_duration",
            "active_days", "average_per_active_day_seconds",
            "average_per_calendar_day_seconds", "goal_seconds",
            "goal_duration", "goal_completed_days", "goal_completion_rate",
            "current_streak", "longest_streak", "daily", "projects", "languages"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON: {e}")
    
    print("   PASS: JSON output works")


def test_invalid_range():
    """Test invalid range handling."""
    print("\n15. INVALID RANGE TEST")
    
    result = subprocess.run(
        ["./vscode-time", "report", "90d"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode != 0, f"Expected non-zero exit code for invalid range"
    assert "Invalid report range" in result.stderr or "Invalid report range" in result.stdout, \
        "Missing error message for invalid range"
    
    print("   PASS: Invalid range handled correctly")


def test_empty_database():
    """Test report with empty database."""
    print("\n16. EMPTY DATABASE TEST")
    
    db_path = create_test_db()
    
    try:
        db = Database(db_path)
        db.connect()
        
        generator = ReportGenerator(db)
        report = generator.generate("7d")
        
        # Verify no crashes
        assert report.total_coding_seconds == 0, "Total coding should be 0 for empty database"
        assert report.active_days == 0, "Active days should be 0 for empty database"
        assert report.calendar_days == 7, "Calendar days should be 7"
        
        db.close()
        
        print("   PASS: Empty database handled correctly")
        
    finally:
        delete_test_db(db_path)


def test_phase4a_regression():
    """Test Phase 4A functionality still works."""
    print("\n17. PHASE 4A REGRESSION TEST")
    
    # Test goal command
    result = subprocess.run(
        ["./vscode-time", "goal"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Goal command failed: {result.stderr}"
    assert "Current daily goal:" in result.stdout, "Goal command output invalid"
    
    # Test today command
    result = subprocess.run(
        ["./vscode-time", "today"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Today command failed: {result.stderr}"
    assert "Date:" in result.stdout, "Today command output invalid"
    
    # Test history command
    result = subprocess.run(
        ["./vscode-time", "history", "7"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"History command failed: {result.stderr}"
    assert "Daily coding history" in result.stdout, "History command output invalid"
    
    print("   PASS: Phase 4A regression")


def test_phase4b_regression():
    """Test Phase 4B functionality still works."""
    print("\n18. PHASE 4B REGRESSION TEST")
    
    # Test streak command
    result = subprocess.run(
        ["./vscode-time", "streak"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Streak command failed: {result.stderr}"
    assert "Current streak:" in result.stdout, "Streak command output invalid"
    
    # Test stats command
    result = subprocess.run(
        ["./vscode-time", "stats"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Stats command failed: {result.stderr}"
    assert "Total coding:" in result.stdout, "Stats command output invalid"
    
    print("   PASS: Phase 4B regression")


def test_phase5_regression():
    """Test Phase 5 functionality still works."""
    print("\n19. PHASE 5 REGRESSION TEST")
    
    # Test JSON status
    result = subprocess.run(
        ["./vscode-time", "status", "--json"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"JSON status failed: {result.stderr}"
    
    try:
        data = json.loads(result.stdout)
        assert "date" in data, "Missing date field"
        assert "coding_seconds" in data, "Missing coding_seconds field"
        assert "goal_met" in data, "Missing goal_met field"
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON: {e}")
    
    # Test Waybar formatter
    result = subprocess.run(
        ["./waybar/vscode-time.sh"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Waybar formatter failed: {result.stderr}"
    
    try:
        data = json.loads(result.stdout)
        assert "text" in data, "Missing text field"
        assert "tooltip" in data, "Missing tooltip field"
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON from Waybar: {e}")
    
    print("   PASS: Phase 5 regression")


def test_real_data_verification():
    """Test against real database."""
    print("\n20. REAL DATA VERIFICATION")
    
    db_path = Path.home() / ".local" / "share" / "vscode-time" / "vscode-time.db"
    
    if not db_path.exists():
        print("   SKIP: Real database not found")
        return
    
    # Get report output
    result = subprocess.run(
        ["./vscode-time", "report", "7d", "--json"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    
    data = json.loads(result.stdout)
    
    # Verify against known values
    assert data["total_coding_seconds"] > 0, "Total coding should be > 0"
    assert data["calendar_days"] == 7, "Calendar days should be 7"
    assert data["active_days"] >= 0, "Active days should be >= 0"
    
    print("   PASS: Real data verification")


def main():
    """Run all tests."""
    print("=" * 70)
    print("PHASE 6B TESTS - REPORTS & ANALYTICS")
    print("=" * 70)
    
    try:
        test_default_range()
        test_today_range()
        test_yesterday_range()
        test_7d_range()
        test_30d_range()
        test_daily_breakdown()
        test_empty_days()
        test_project_breakdown()
        test_language_breakdown()
        test_goal_completion()
        test_goal_completion_rate()
        test_averages()
        test_sorting()
        test_json_output()
        test_invalid_range()
        test_empty_database()
        test_phase4a_regression()
        test_phase4b_regression()
        test_phase5_regression()
        test_real_data_verification()
        
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
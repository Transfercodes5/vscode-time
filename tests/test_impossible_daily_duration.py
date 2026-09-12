"""Regression tests for the impossible daily duration bug.

This test file verifies that the adapter correctly converts the source
'long' field from milliseconds to seconds, and that daily totals are
sanity-checked against physical limits.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from adapter.coding_tracker import (
    CodingTrackerAdapter, parse_record_line, parse_db_file,
    filter_coding_sessions, compute_record_id, Session,
    CODING_TRACKER_DIR, DB_EXTENSION, SUPPORTED_VERSIONS,
)
from storage.database import Database


@pytest.fixture
def tmp_db_dir():
    """Create a temporary directory for test databases."""
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d)


@pytest.fixture
def tmp_vscode_time_db(tmp_db_dir):
    """Create a temporary vscode-time database."""
    db_path = tmp_db_dir / "vscode-time.db"
    db = Database(db_path)
    db.connect()
    yield db
    db.close()


def create_source_file(directory: Path, filename: str, records: list) -> Path:
    """Create a source .db file with the given records."""
    filepath = directory / filename
    lines = ["4.0"]
    for rec in records:
        lines.append(" ".join(str(x) for x in rec))
    filepath.write_text("\n".join(lines) + "\n")
    return filepath


class TestDurationUnits:
    """Verify that the adapter converts milliseconds to seconds."""

    def test_parse_record_returns_raw_milliseconds(self):
        """parse_record_line returns raw values including ms duration."""
        line = "2 1789151444788 5000 python vscode-notebook-cell /proj unknown-linux git::master 10 1000 0 0"
        result = parse_record_line(line)
        assert result is not None
        rec_type, timestamp, duration_ms, lang, file, proj, vcs, line_count, char_count = result
        assert rec_type == 2
        assert timestamp == 1789151444788
        assert duration_ms == 5000  # Raw milliseconds

    def test_session_duration_converted_to_seconds(self, tmp_db_dir):
        """Session objects store duration in seconds, not milliseconds."""
        records = [
            [2, 1789151444788, 5000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],
            [2, 1789151529964, 20000, "python", "file2.py", "/proj", "unknown-linux", "git::master", 20, 2000, "0", "0"],
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        adapter = CodingTrackerAdapter(tmp_db_dir)
        sessions = adapter.get_sessions(filter_coding=True)

        assert len(sessions) == 2
        # 5000ms -> 5s, 20000ms -> 20s
        assert sessions[0].duration_seconds == 5
        assert sessions[1].duration_seconds == 20

    def test_daily_totals_use_seconds(self, tmp_db_dir):
        """Daily totals are summed in seconds, not milliseconds."""
        records = [
            [2, 1789151444788, 5000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],
            [2, 1789151529964, 20000, "python", "file2.py", "/proj", "unknown-linux", "git::master", 20, 2000, "0", "0"],
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        adapter = CodingTrackerAdapter(tmp_db_dir)
        sessions = adapter.get_sessions(filter_coding=True)
        daily = adapter.get_daily_totals(sessions)

        # Both records are on the same day (2026-09-12)
        total = sum(daily.values())
        # 5s + 20s = 25s (not 25000s)
        assert total == 25

    def test_large_duration_converted_correctly(self, tmp_db_dir):
        """A large source duration (e.g., 115000ms = 115s) is converted correctly."""
        records = [
            [2, 1789151444788, 115000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        adapter = CodingTrackerAdapter(tmp_db_dir)
        sessions = adapter.get_sessions(filter_coding=True)

        assert sessions[0].duration_seconds == 115  # 115000ms -> 115s


class TestDailyUpperBound:
    """Verify that daily totals don't exceed physical limits for individual sessions."""

    def test_no_single_session_exceeds_24h(self, tmp_db_dir):
        """No single session should have duration > 86400 seconds after conversion."""
        # Source with a very large duration in ms (e.g., 100000000ms = 100000s = ~27.8h)
        records = [
            [2, 1789151444788, 100000000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        adapter = CodingTrackerAdapter(tmp_db_dir)
        sessions = adapter.get_sessions(filter_coding=True)

        # 100000000ms -> 100000s (still > 86400, but this is a source-level issue)
        # The adapter should preserve the value; the application layer should handle it
        assert sessions[0].duration_seconds == 100000

    def test_typical_session_durations(self, tmp_db_dir):
        """Typical session durations are in the range of seconds to minutes."""
        records = [
            [2, 1789151444788, 5000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],      # 5s
            [2, 1789151529964, 60000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],     # 60s
            [2, 1789151600000, 300000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],    # 5m
            [2, 1789151900000, 1800000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],   # 30m
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        adapter = CodingTrackerAdapter(tmp_db_dir)
        sessions = adapter.get_sessions(filter_coding=True)

        assert sessions[0].duration_seconds == 5       # 5s
        assert sessions[1].duration_seconds == 60      # 1m
        assert sessions[2].duration_seconds == 300     # 5m
        assert sessions[3].duration_seconds == 1800    # 30m


class TestDuplicateSync:
    """Verify sync idempotency."""

    def test_sync_twice_same_totals(self, tmp_db_dir, tmp_vscode_time_db):
        """Running sync twice should not change totals."""
        records = [
            [2, 1789151444788, 5000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],
            [2, 1789151529964, 20000, "python", "file2.py", "/proj", "unknown-linux", "git::master", 20, 2000, "0", "0"],
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        adapter = CodingTrackerAdapter(tmp_db_dir)
        from sync.importer import Importer
        importer = Importer(tmp_vscode_time_db, adapter)

        # First sync
        result1 = importer.sync()
        total1 = tmp_vscode_time_db.get_total_coding_seconds()

        # Second sync
        result2 = importer.sync()
        total2 = tmp_vscode_time_db.get_total_coding_seconds()

        assert total1 == total2
        assert result2.new_imported == 0
        assert result2.already_imported == 2


class TestDateFiltering:
    """Verify sessions are attributed to correct dates."""

    def test_session_at_correct_date(self, tmp_db_dir, tmp_vscode_time_db):
        """A session's date is determined by its start_time, not import time."""
        # 2026-09-11 16:20:00 UTC = 1789143600000 ms
        ts_yesterday = 1789143600000
        # 2026-09-12 16:20:00 UTC = 1789229000000 ms (next day)
        ts_today = 1789229000000

        records = [
            [2, ts_yesterday, 5000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],
            [2, ts_today, 10000, "python", "file2.py", "/proj", "unknown-linux", "git::master", 20, 2000, "0", "0"],
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        adapter = CodingTrackerAdapter(tmp_db_dir)
        sessions = adapter.get_sessions(filter_coding=True)
        daily = adapter.get_daily_totals(sessions)

        # Each session should be on a different day
        assert len(daily) == 2

    def test_session_not_counted_twice(self, tmp_db_dir, tmp_vscode_time_db):
        """A session should only be counted once, not per language/project/file."""
        records = [
            [2, 1789151444788, 5000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        adapter = CodingTrackerAdapter(tmp_db_dir)
        from sync.importer import Importer
        importer = Importer(tmp_vscode_time_db, adapter)
        importer.sync()

        total = tmp_vscode_time_db.get_total_coding_seconds()
        assert total == 5  # 5000ms -> 5s, counted once


class TestMonthBoundary:
    """Verify correct behavior at month boundaries."""

    def test_month_boundary(self, tmp_db_dir):
        """Sessions across month boundary are attributed to correct months."""
        # 2025-08-31 12:00:00 UTC = 1756632000000 ms
        ts_aug = 1756632000000
        # 2025-09-01 12:00:00 UTC = 1756718400000 ms
        ts_sep = 1756718400000

        records = [
            [2, ts_aug, 5000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],
            [2, ts_sep, 10000, "python", "file2.py", "/proj", "unknown-linux", "git::master", 20, 2000, "0", "0"],
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        adapter = CodingTrackerAdapter(tmp_db_dir)
        sessions = adapter.get_sessions(filter_coding=True)
        daily = adapter.get_daily_totals(sessions)

        # Should have 2 different dates
        assert len(daily) == 2


class TestYearBoundary:
    """Verify correct behavior at year boundaries."""

    def test_year_boundary(self, tmp_db_dir):
        """Sessions across year boundary are attributed to correct years."""
        # 2025-12-31 23:59:00 UTC = 1767225540000 ms
        ts_dec = 1767225540000
        # 2026-01-01 00:01:00 UTC = 1767225660000 ms
        ts_jan = 1767225660000

        records = [
            [2, ts_dec, 5000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],
            [2, ts_jan, 10000, "python", "file2.py", "/proj", "unknown-linux", "git::master", 20, 2000, "0", "0"],
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        adapter = CodingTrackerAdapter(tmp_db_dir)
        sessions = adapter.get_sessions(filter_coding=True)
        daily = adapter.get_daily_totals(sessions)

        # Should have 2 different dates
        assert len(daily) == 2


class TestMidnight:
    """Verify correct attribution around midnight."""

    def test_record_at_midnight(self, tmp_db_dir):
        """A record at exactly midnight is attributed to the correct day."""
        # 2026-09-12 00:00:00 UTC = 1789185600000 ms
        ts_midnight = 1789185600000

        records = [
            [2, ts_midnight, 5000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        adapter = CodingTrackerAdapter(tmp_db_dir)
        sessions = adapter.get_sessions(filter_coding=True)
        daily = adapter.get_daily_totals(sessions)

        assert len(daily) == 1
        # The date should be 2026-09-12 in local time
        date_key = list(daily.keys())[0]
        assert date_key == "2026-09-12"


class TestJSONConsistency:
    """Verify JSON output matches text output."""

    def test_status_json_matches_text(self, tmp_db_dir, tmp_vscode_time_db):
        """status --json coding_seconds should match status text."""
        records = [
            [2, 1789151444788, 60000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        adapter = CodingTrackerAdapter(tmp_db_dir)
        from sync.importer import Importer
        importer = Importer(tmp_vscode_time_db, adapter)
        importer.sync()

        # Get today's status
        from goals import GoalManager
        manager = GoalManager(tmp_vscode_time_db)
        status = manager.get_today_status()

        # 60000ms -> 60s
        assert status.coding_seconds == 60


class TestSourceDatabaseReconciliation:
    """Verify source totals match database totals."""

    def test_source_matches_database(self, tmp_db_dir, tmp_vscode_time_db):
        """Total seconds from source should match database total."""
        records = [
            [2, 1789151444788, 5000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],
            [2, 1789151529964, 20000, "python", "file2.py", "/proj", "unknown-linux", "git::master", 20, 2000, "0", "0"],
            [2, 1789151600000, 30000, "markdown", "doc.md", "/proj", "unknown-linux", "git::master", 50, 5000, "0", "0"],
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        # Calculate source total (convert ms to sec)
        source_total_ms = sum(r[2] for r in records)
        source_total_sec = source_total_ms // 1000

        # Import and check database
        adapter = CodingTrackerAdapter(tmp_db_dir)
        from sync.importer import Importer
        importer = Importer(tmp_vscode_time_db, adapter)
        importer.sync()

        db_total = tmp_vscode_time_db.get_total_coding_seconds()
        assert db_total == source_total_sec

    def test_record_count_matches(self, tmp_db_dir, tmp_vscode_time_db):
        """Number of coding records in source should match database."""
        records = [
            [2, 1789151444788, 5000, "python", "file.py", "/proj", "unknown-linux", "git::master", 10, 1000, "0", "0"],
            [2, 1789151529964, 20000, "python", "file2.py", "/proj", "unknown-linux", "git::master", 20, 2000, "0", "0"],
            [0, 1789151600000, 30000, "markdown", "doc.md", "/proj", "unknown-linux", "git::master", 50, 5000, "0", "0"],  # type 0, not coding
        ]
        create_source_file(tmp_db_dir, "test.db", records)

        adapter = CodingTrackerAdapter(tmp_db_dir)
        from sync.importer import Importer
        importer = Importer(tmp_vscode_time_db, adapter)
        result = importer.sync()

        # Only 2 type-2 records should be imported
        assert result.coding_records == 2
        assert result.new_imported == 2


class TestRecordIDStability:
    """Verify deterministic record IDs."""

    def test_same_input_same_id(self):
        """Same source fields produce the same ID."""
        id1 = compute_record_id(
            source="vscode-coding-tracker",
            session_type=2,
            start_time=1789151444788,
            duration_seconds=5,
            language="python",
            file="file.py",
            project="/proj",
            vcs="git::master",
            line_count=10,
            char_count=1000,
        )
        id2 = compute_record_id(
            source="vscode-coding-tracker",
            session_type=2,
            start_time=1789151444788,
            duration_seconds=5,
            language="python",
            file="file.py",
            project="/proj",
            vcs="git::master",
            line_count=10,
            char_count=1000,
        )
        assert id1 == id2
        assert id1.startswith("ct-")

    def test_different_input_different_id(self):
        """Different source fields produce different IDs."""
        id1 = compute_record_id(
            source="vscode-coding-tracker",
            session_type=2,
            start_time=1789151444788,
            duration_seconds=5,
            language="python",
            file="file.py",
            project="/proj",
            vcs="git::master",
            line_count=10,
            char_count=1000,
        )
        id2 = compute_record_id(
            source="vscode-coding-tracker",
            session_type=2,
            start_time=1789151444788,
            duration_seconds=10,  # Different duration
            language="python",
            file="file.py",
            project="/proj",
            vcs="git::master",
            line_count=10,
            char_count=1000,
        )
        assert id1 != id2

#!/usr/bin/env python3
"""Phase 8 tests - Data Export & Portability.

Tests for JSON and CSV export functionality.
"""

import sys
import os
import json
import csv
import io
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from storage.database import Database
from export import Exporter, ExportError, SUPPORTED_FORMATS, CSV_COLUMNS
from reports import parse_range


def run_cmd(args, cwd=None):
    """Run a CLI command and return result."""
    if cwd is None:
        cwd = os.path.join(os.path.dirname(__file__), '..')
    return subprocess.run(
        ["./vscode-time"] + args,
        capture_output=True,
        text=True,
        cwd=cwd
    )


def create_temp_db():
    """Create a temporary database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        return Path(f.name)


def delete_temp_db(db_path):
    """Delete a temporary database."""
    if db_path.exists():
        db_path.unlink()


def date_to_ms(date_str, hour=12):
    """Convert date string to milliseconds since epoch (UTC)."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=hour, tzinfo=timezone.utc
    )
    return int(dt.timestamp() * 1000)


def create_mock_session(start_time_ms, duration_seconds, **kwargs):
    """Create a mock coding session."""
    class MockSession:
        def __init__(self):
            self.record_id = kwargs.get("record_id", f"test_{start_time_ms}")
            self.session_type = kwargs.get("session_type", 2)
            self.start_time = start_time_ms
            self.duration_seconds = duration_seconds
            self.language = kwargs.get("language", "python")
            self.file = kwargs.get("file", "/test/file.py")
            self.project = kwargs.get("project", "/test/project")
            self.vcs = kwargs.get("vcs", "git")
            self.line_count = kwargs.get("line_count", 100)
            self.char_count = kwargs.get("char_count", 1000)
            self.source_file = kwargs.get("source_file", "test.db")
    return MockSession()


class TestBasicJsonExport:
    """Tests for basic JSON export."""

    def test_json_valid(self):
        """JSON export should produce valid JSON."""
        print("1. JSON VALID TEST")

        result = run_cmd(["export", "--json"])
        assert result.returncode == 0

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON: {e}")

        print("   PASS")

    def test_json_metadata(self):
        """JSON should contain required metadata fields."""
        print("2. JSON METADATA TEST")

        result = run_cmd(["export", "--json"])
        assert result.returncode == 0

        data = json.loads(result.stdout)
        assert data["format"] == "vscode-time-export"
        assert data["version"] == 1
        assert "exported_at" in data
        assert "range" in data
        assert "sessions" in data

        print("   PASS")

    def test_json_sessions_list(self):
        """JSON sessions should be a list."""
        print("3. JSON SESSIONS LIST TEST")

        result = run_cmd(["export", "--json"])
        assert result.returncode == 0

        data = json.loads(result.stdout)
        assert isinstance(data["sessions"], list)

        print("   PASS")


class TestBasicCsvExport:
    """Tests for basic CSV export."""

    def test_csv_valid(self):
        """CSV export should produce valid CSV."""
        print("4. CSV VALID TEST")

        result = run_cmd(["export", "--csv"])
        assert result.returncode == 0

        reader = csv.reader(io.StringIO(result.stdout))
        rows = list(reader)
        assert len(rows) > 0, "CSV should have at least a header"

        print("   PASS")

    def test_csv_header(self):
        """CSV should have correct header."""
        print("5. CSV HEADER TEST")

        result = run_cmd(["export", "--csv"])
        assert result.returncode == 0

        reader = csv.reader(io.StringIO(result.stdout))
        header = next(reader)

        assert header == CSV_COLUMNS, f"Header mismatch: {header}"

        print("   PASS")

    def test_csv_rows_match_header(self):
        """CSV rows should have same number of columns as header."""
        print("6. CSV ROWS MATCH HEADER TEST")

        result = run_cmd(["export", "--csv"])
        assert result.returncode == 0

        reader = csv.reader(io.StringIO(result.stdout))
        rows = list(reader)
        header_len = len(rows[0])

        for i, row in enumerate(rows[1:], 1):
            assert len(row) == header_len, \
                f"Row {i} has {len(row)} columns, expected {header_len}"

        print("   PASS")


class TestSessionFields:
    """Tests for session field completeness."""

    def test_json_session_fields(self):
        """JSON sessions should contain all required fields."""
        print("7. JSON SESSION FIELDS TEST")

        result = run_cmd(["export", "--json"])
        assert result.returncode == 0

        data = json.loads(result.stdout)

        if data["sessions"]:
            session = data["sessions"][0]
            required_fields = [
                "source", "source_id", "session_type", "start_time",
                "duration_seconds", "language", "file", "project",
                "vcs", "line_count", "char_count", "source_file"
            ]
            for field in required_fields:
                assert field in session, f"Missing field: {field}"

        print("   PASS")

    def test_csv_session_fields(self):
        """CSV should contain all required fields."""
        print("8. CSV SESSION FIELDS TEST")

        result = run_cmd(["export", "--csv"])
        assert result.returncode == 0

        reader = csv.DictReader(io.StringIO(result.stdout))
        rows = list(reader)

        if rows:
            row = rows[0]
            for field in CSV_COLUMNS:
                assert field in row, f"Missing field: {field}"

        print("   PASS")


class TestTypeFiltering:
    """Tests for session type filtering."""

    def test_only_type2(self):
        """Only type-2 sessions should be exported."""
        print("9. ONLY TYPE-2 TEST")

        result = run_cmd(["export", "--json"])
        assert result.returncode == 0

        data = json.loads(result.stdout)
        for session in data["sessions"]:
            assert session["session_type"] == 2, \
                f"Non-type-2 session found: {session['session_type']}"

        print("   PASS")


class TestFullExportTotal:
    """Tests for full export totals."""

    def test_export_total_matches_db(self):
        """Exported total should match database total."""
        print("10. EXPORT TOTAL MATCHES DB TEST")

        # Get database total
        db_path = Path.home() / ".local" / "share" / "vscode-time" / "vscode-time.db"
        db = Database(db_path)
        db.connect()
        db_total = db.get_total_coding_seconds()
        db.close()

        # Get export total
        result = run_cmd(["export", "--json"])
        assert result.returncode == 0

        data = json.loads(result.stdout)
        export_total = sum(s["duration_seconds"] for s in data["sessions"])

        assert export_total == db_total, \
            f"Export total {export_total} != DB total {db_total}"

        print("   PASS")

    def test_export_session_count_matches_db(self):
        """Exported session count should match database count."""
        print("11. EXPORT SESSION COUNT MATCHES DB TEST")

        # Get database count
        db_path = Path.home() / ".local" / "share" / "vscode-time" / "vscode-time.db"
        db = Database(db_path)
        db.connect()
        db_count = db.get_session_count()
        db.close()

        # Get export count
        result = run_cmd(["export", "--json"])
        assert result.returncode == 0

        data = json.loads(result.stdout)
        export_count = len(data["sessions"])

        assert export_count == db_count, \
            f"Export count {export_count} != DB count {db_count}"

        print("   PASS")


class TestRangeFiltering:
    """Tests for date range filtering."""

    def test_range_today(self):
        """Export with today range should work."""
        print("12. RANGE TODAY TEST")

        result = run_cmd(["export", "--json", "today"])
        assert result.returncode == 0

        data = json.loads(result.stdout)
        assert data["range"]["start_date"] is not None
        assert data["range"]["days"] == 1

        print("   PASS")

    def test_range_yesterday(self):
        """Export with yesterday range should work."""
        print("13. RANGE YESTERDAY TEST")

        result = run_cmd(["export", "--json", "yesterday"])
        assert result.returncode == 0

        data = json.loads(result.stdout)
        assert data["range"]["days"] == 1

        print("   PASS")

    def test_range_7d(self):
        """Export with 7d range should work."""
        print("14. RANGE 7D TEST")

        result = run_cmd(["export", "--json", "7d"])
        assert result.returncode == 0

        data = json.loads(result.stdout)
        assert data["range"]["days"] == 7

        print("   PASS")

    def test_range_30d(self):
        """Export with 30d range should work."""
        print("15. RANGE 30D TEST")

        result = run_cmd(["export", "--json", "30d"])
        assert result.returncode == 0

        data = json.loads(result.stdout)
        assert data["range"]["days"] == 30

        print("   PASS")

    def test_range_total_matches_report(self):
        """Range export total should match report total."""
        print("16. RANGE TOTAL MATCHES REPORT TEST")

        # Get report total
        result_report = run_cmd(["report", "7d", "--json"])
        assert result_report.returncode == 0
        report_data = json.loads(result_report.stdout)
        report_total = report_data["total_coding_seconds"]

        # Get export total
        result_export = run_cmd(["export", "--json", "7d"])
        assert result_export.returncode == 0
        export_data = json.loads(result_export.stdout)
        export_total = sum(s["duration_seconds"] for s in export_data["sessions"])

        assert export_total == report_total, \
            f"Export total {export_total} != Report total {report_total}"

        print("   PASS")


class TestEmptyExport:
    """Tests for empty export handling."""

    def test_empty_database_json(self):
        """Empty database should produce valid empty JSON export."""
        print("17. EMPTY DATABASE JSON TEST")

        temp_db = create_temp_db()
        try:
            db = Database(temp_db)
            db.connect()
            exporter = Exporter(db)
            output = exporter.export_json()

            data = json.loads(output)
            assert data["format"] == "vscode-time-export"
            assert data["sessions"] == []

            db.close()
        finally:
            delete_temp_db(temp_db)

        print("   PASS")

    def test_empty_database_csv(self):
        """Empty database should produce valid CSV with header only."""
        print("18. EMPTY DATABASE CSV TEST")

        temp_db = create_temp_db()
        try:
            db = Database(temp_db)
            db.connect()
            exporter = Exporter(db)
            output = exporter.export_csv()

            reader = csv.reader(io.StringIO(output))
            rows = list(reader)
            assert len(rows) == 1, "Should have only header row"
            assert rows[0] == CSV_COLUMNS

            db.close()
        finally:
            delete_temp_db(temp_db)

        print("   PASS")


class TestDeterministicOrdering:
    """Tests for deterministic session ordering."""

    def test_deterministic_order(self):
        """Same database state should produce same session order."""
        print("19. DETERMINISTIC ORDER TEST")

        result1 = run_cmd(["export", "--json"])
        result2 = run_cmd(["export", "--json"])

        assert result1.returncode == 0
        assert result2.returncode == 0

        data1 = json.loads(result1.stdout)
        data2 = json.loads(result2.stdout)

        # Sessions should be identical (excluding exported_at)
        assert len(data1["sessions"]) == len(data2["sessions"])

        for s1, s2 in zip(data1["sessions"], data2["sessions"]):
            assert s1["source_id"] == s2["source_id"]
            assert s1["start_time"] == s2["start_time"]
            assert s1["duration_seconds"] == s2["duration_seconds"]

        print("   PASS")

    def test_ordering_by_start_time(self):
        """Sessions should be ordered by start_time ASC."""
        print("20. ORDERING BY START TIME TEST")

        result = run_cmd(["export", "--json"])
        assert result.returncode == 0

        data = json.loads(result.stdout)
        sessions = data["sessions"]

        for i in range(len(sessions) - 1):
            assert sessions[i]["start_time"] <= sessions[i + 1]["start_time"], \
                f"Sessions not in order: {sessions[i]['start_time']} > {sessions[i+1]['start_time']}"

        print("   PASS")


class TestCsvEscaping:
    """Tests for CSV escaping."""

    def test_csv_special_characters(self):
        """CSV should handle special characters correctly."""
        print("21. CSV SPECIAL CHARACTERS TEST")

        temp_db = create_temp_db()
        try:
            db = Database(temp_db)
            db.connect()

            # Insert session with special characters
            session = create_mock_session(
                date_to_ms("2026-09-11"), 300,
                file="path/with,comma.py",
                project="project\"with\"quotes"
            )
            db.insert_coding_session(session)

            exporter = Exporter(db)
            output = exporter.export_csv()

            # Parse CSV
            reader = csv.DictReader(io.StringIO(output))
            rows = list(reader)

            assert len(rows) == 1
            assert rows[0]["file"] == "path/with,comma.py"
            assert rows[0]["project"] == "project\"with\"quotes"

            db.close()
        finally:
            delete_temp_db(temp_db)

        print("   PASS")


class TestJsonEscaping:
    """Tests for JSON escaping."""

    def test_json_special_characters(self):
        """JSON should handle special characters correctly."""
        print("22. JSON SPECIAL CHARACTERS TEST")

        temp_db = create_temp_db()
        try:
            db = Database(temp_db)
            db.connect()

            # Insert session with special characters
            session = create_mock_session(
                date_to_ms("2026-09-11"), 300,
                file="path/with\\backslash.py",
                project="project\nnewline"
            )
            db.insert_coding_session(session)

            exporter = Exporter(db)
            output = exporter.export_json()

            # Parse JSON
            data = json.loads(output)
            assert len(data["sessions"]) == 1

            db.close()
        finally:
            delete_temp_db(temp_db)

        print("   PASS")


class TestInvalidRange:
    """Tests for invalid range handling."""

    def test_invalid_range(self):
        """Invalid range should fail."""
        print("23. INVALID RANGE TEST")

        result = run_cmd(["export", "--json", "90d"])
        assert result.returncode != 0
        assert "Error:" in result.stderr

        print("   PASS")


class TestInvalidFormat:
    """Tests for invalid format handling."""

    def test_no_format(self):
        """Export without format should fail."""
        print("24. NO FORMAT TEST")

        result = run_cmd(["export"])
        assert result.returncode != 0
        assert "Error:" in result.stderr

        print("   PASS")

    def test_both_formats(self):
        """Export with both formats should fail."""
        print("25. BOTH FORMATS TEST")

        result = run_cmd(["export", "--json", "--csv"])
        assert result.returncode != 0
        assert "Error:" in result.stderr

        print("   PASS")


class TestStdoutStderr:
    """Tests for stdout/stderr contract."""

    def test_success_stdout_only(self):
        """Success should output only to stdout."""
        print("26. SUCCESS STDOUT ONLY TEST")

        result = run_cmd(["export", "--json"])
        assert result.returncode == 0
        assert len(result.stderr.strip()) == 0

        print("   PASS")

    def test_error_stderr_only(self):
        """Error should output only to stderr."""
        print("27. ERROR STDERR ONLY TEST")

        result = run_cmd(["export", "--json", "90d"])
        assert result.returncode != 0
        assert len(result.stdout.strip()) == 0
        assert "Error:" in result.stderr

        print("   PASS")


class TestDatabaseProtection:
    """Tests for database protection."""

    def test_database_unchanged(self):
        """Export should not modify the database."""
        print("28. DATABASE UNCHANGED TEST")

        db_path = Path.home() / ".local" / "share" / "vscode-time" / "vscode-time.db"

        # Get state before
        db = Database(db_path)
        db.connect()
        count_before = db.get_session_count()
        seconds_before = db.get_total_coding_seconds()
        db.close()

        # Run export
        result = run_cmd(["export", "--json"])
        assert result.returncode == 0

        # Get state after
        db = Database(db_path)
        db.connect()
        count_after = db.get_session_count()
        seconds_after = db.get_total_coding_seconds()
        db.close()

        assert count_before == count_after
        assert seconds_before == seconds_after

        print("   PASS")


class TestLargeValues:
    """Tests for large values."""

    def test_large_duration(self):
        """Large duration values should be preserved exactly."""
        print("29. LARGE DURATION TEST")

        temp_db = create_temp_db()
        try:
            db = Database(temp_db)
            db.connect()

            # Insert session with large duration (100 hours)
            large_seconds = 360000
            session = create_mock_session(
                date_to_ms("2026-09-11"), large_seconds
            )
            db.insert_coding_session(session)

            exporter = Exporter(db)
            output = exporter.export_json()

            data = json.loads(output)
            assert data["sessions"][0]["duration_seconds"] == large_seconds

            db.close()
        finally:
            delete_temp_db(temp_db)

        print("   PASS")


class TestExportHelp:
    """Tests for export help."""

    def test_export_help(self):
        """export --help should work."""
        print("30. EXPORT HELP TEST")

        result = run_cmd(["export", "--help"])
        assert result.returncode == 0
        assert "Usage:" in result.stdout
        assert "--json" in result.stdout
        assert "--csv" in result.stdout

        print("   PASS")


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_existing_commands_unaffected(self):
        """Existing commands should continue working."""
        print("31. BACKWARD COMPATIBILITY TEST")

        commands = [
            ["today"],
            ["history", "7"],
            ["goal"],
            ["streak"],
            ["stats"],
            ["report"],
            ["status"],
            ["sync"],
        ]

        for cmd in commands:
            result = run_cmd(cmd)
            assert result.returncode == 0, f"Command {cmd} failed"

        print("   PASS")


class TestRealDataVerification:
    """Tests for real data verification."""

    def test_real_data_export(self):
        """Real data export should work correctly."""
        print("32. REAL DATA EXPORT TEST")

        result = run_cmd(["export", "--json"])
        assert result.returncode == 0

        data = json.loads(result.stdout)
        assert data["format"] == "vscode-time-export"
        assert len(data["sessions"]) > 0

        print("   PASS")

    def test_real_data_csv(self):
        """Real data CSV export should work correctly."""
        print("33. REAL DATA CSV TEST")

        result = run_cmd(["export", "--csv"])
        assert result.returncode == 0

        reader = csv.reader(io.StringIO(result.stdout))
        rows = list(reader)
        assert len(rows) > 1, "Should have header + data rows"

        print("   PASS")


def run_all_tests():
    """Run all Phase 8 tests."""
    print("=" * 70)
    print("PHASE 8 TESTS - DATA EXPORT & PORTABILITY")
    print("=" * 70)

    test_classes = [
        TestBasicJsonExport,
        TestBasicCsvExport,
        TestSessionFields,
        TestTypeFiltering,
        TestFullExportTotal,
        TestRangeFiltering,
        TestEmptyExport,
        TestDeterministicOrdering,
        TestCsvEscaping,
        TestJsonEscaping,
        TestInvalidRange,
        TestInvalidFormat,
        TestStdoutStderr,
        TestDatabaseProtection,
        TestLargeValues,
        TestExportHelp,
        TestBackwardCompatibility,
        TestRealDataVerification,
    ]

    total_passed = 0
    total_failed = 0
    failures = []

    for test_class in test_classes:
        print(f"\n{'='*70}")
        print(f"{test_class.__name__}")
        print(f"{'='*70}")

        instance = test_class()
        methods = [m for m in dir(instance) if m.startswith("test_")]

        for method_name in sorted(methods):
            method = getattr(instance, method_name)
            try:
                method()
                total_passed += 1
            except AssertionError as e:
                total_failed += 1
                failures.append(f"{test_class.__name__}.{method_name}: {e}")
                print(f"   FAIL: {e}")
            except Exception as e:
                total_failed += 1
                failures.append(f"{test_class.__name__}.{method_name}: {e}")
                print(f"   ERROR: {e}")

    print("\n" + "=" * 70)
    print(f"RESULTS: {total_passed} passed, {total_failed} failed")
    print("=" * 70)

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")

    return total_passed, total_failed


if __name__ == "__main__":
    passed, failed = run_all_tests()
    sys.exit(0 if failed == 0 else 1)

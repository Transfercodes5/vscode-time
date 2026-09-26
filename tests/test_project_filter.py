"""Tests for the project filter feature.

Verifies that when a tracked_project is set, all query methods
(Database, GoalManager, StatisticsCalculator, ReportGenerator, Exporter)
correctly filter results to only the selected project.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from storage.database import Database
from adapter.coding_tracker import Session, compute_record_id
from goals import GoalManager
from statistics import StatisticsCalculator
from reports import ReportGenerator
from export import Exporter
from config import Config, load_config, ConfigValidationError, DEFAULTS, SUPPORTED_KEYS


# Fixtures

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


@pytest.fixture
def tmp_config(tmp_db_dir):
    """Create a temporary config file."""
    config_path = tmp_db_dir / "config.toml"
    config = Config(config_path)
    config.load()
    yield config


def make_session(
    start_time_ms: int,
    duration_seconds: int,
    project: str = "/proj/a",
    language: str = "python",
    session_type: int = 0,
    file: str = "/proj/a/file.py",
    source_file: str = "test.db",
) -> Session:
    """Create a Session object for insertion."""
    session = Session(
        session_type=session_type,
        start_time=start_time_ms,
        duration_seconds=duration_seconds,
        language=language,
        file=file,
        project=project,
        vcs="git::master",
        line_count=10,
        char_count=100,
        record_id="",
        source_file=source_file,
    )
    session.record_id = compute_record_id(
        source="vscode-coding-tracker",
        session_type=session_type,
        start_time=start_time_ms,
        duration_seconds=duration_seconds,
        language=language,
        file=file,
        project=project,
        vcs="git::master",
        line_count=10,
        char_count=100,
    )
    return session


def insert_sessions(db: Database, sessions: list) -> None:
    """Insert sessions into the database."""
    for s in sessions:
        db.insert_coding_session(s)


def date_to_ms(date_str: str, hour: int = 12) -> int:
    """Convert YYYY-MM-DD to epoch ms at given hour (local time)."""
    local_tz = datetime.now().astimezone().tzinfo
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=hour, minute=0, second=0, microsecond=0, tzinfo=local_tz
    )
    return int(dt.timestamp() * 1000)


# Test data setup

def setup_multi_project_db(db: Database) -> None:
    """Insert sessions across two projects on known dates."""
    sessions = [
        # Project A sessions
        make_session(date_to_ms("2026-09-20"), 1800, project="/proj/alpha"),   # 30m
        make_session(date_to_ms("2026-09-21"), 3600, project="/proj/alpha"),   # 60m
        make_session(date_to_ms("2026-09-22"), 900,  project="/proj/alpha"),   # 15m
        # Project B sessions
        make_session(date_to_ms("2026-09-20"), 600, project="/proj/beta"),     # 10m
        make_session(date_to_ms("2026-09-21"), 1800, project="/proj/beta"),    # 30m
        make_session(date_to_ms("2026-09-22"), 3600, project="/proj/beta"),    # 60m
    ]
    insert_sessions(db, sessions)


# Config tests

class TestConfigKey:
    """Verify tracked_project config key works."""

    def test_default_is_empty(self):
        assert DEFAULTS["tracked_project"] == ""

    def test_in_supported_keys(self):
        assert "tracked_project" in SUPPORTED_KEYS

    def test_set_string(self, tmp_config):
        tmp_config.set("tracked_project", "/proj/alpha")
        assert tmp_config.get("tracked_project") == "/proj/alpha"

    def test_set_empty_string(self, tmp_config):
        tmp_config.set("tracked_project", "/proj/alpha")
        tmp_config.set("tracked_project", "")
        assert tmp_config.get("tracked_project") == ""

    def test_reject_non_string(self, tmp_config):
        with pytest.raises(ConfigValidationError):
            tmp_config.set("tracked_project", 123)

    def test_set_from_input_clear(self, tmp_config):
        tmp_config.set("tracked_project", "/proj/alpha")
        tmp_config.set_from_input("tracked_project", "clear")
        assert tmp_config.get("tracked_project") == ""

    def test_set_from_input_all(self, tmp_config):
        tmp_config.set("tracked_project", "/proj/alpha")
        tmp_config.set_from_input("tracked_project", "all")
        assert tmp_config.get("tracked_project") == ""

    def test_set_from_input_value(self, tmp_config):
        tmp_config.set_from_input("tracked_project", "/proj/alpha")
        assert tmp_config.get("tracked_project") == "/proj/alpha"

    def test_save_and_reload(self, tmp_config):
        tmp_config.set("tracked_project", "/proj/alpha")
        tmp_config.save()

        reloaded = Config(tmp_config.config_path)
        reloaded.load()
        assert reloaded.get("tracked_project") == "/proj/alpha"


# Database filter tests

class TestDatabaseFilter:
    """Verify Database query methods respect project_filter."""

    def test_default_no_filter(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        # No filter set — all sessions returned
        assert tmp_vscode_time_db.get_session_count() == 6
        assert tmp_vscode_time_db.get_total_coding_seconds() == 1800 + 3600 + 900 + 600 + 1800 + 3600

    def test_filter_set(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        assert tmp_vscode_time_db.get_session_count() == 3
        assert tmp_vscode_time_db.get_total_coding_seconds() == 1800 + 3600 + 900

    def test_filter_other_project(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/beta"
        assert tmp_vscode_time_db.get_session_count() == 3
        assert tmp_vscode_time_db.get_total_coding_seconds() == 600 + 1800 + 3600

    def test_daily_totals_filtered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        daily = tmp_vscode_time_db.get_daily_totals()
        totals = {d["day"]: d["total_seconds"] for d in daily}
        assert totals["2026-09-20"] == 1800
        assert totals["2026-09-21"] == 3600
        assert totals["2026-09-22"] == 900

    def test_project_totals_filtered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        projects = tmp_vscode_time_db.get_project_totals()
        assert len(projects) == 1
        assert projects[0]["project"] == "/proj/alpha"
        assert projects[0]["total_seconds"] == 6300

    def test_get_coding_sessions_filtered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        sessions = tmp_vscode_time_db.get_coding_sessions()
        assert len(sessions) == 3
        assert all(s["project"] == "/proj/alpha" for s in sessions)

    def test_get_coding_sessions_with_limit(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        sessions = tmp_vscode_time_db.get_coding_sessions(limit=2)
        assert len(sessions) == 2

    def test_get_coding_sessions_by_date_filtered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        sessions = tmp_vscode_time_db.get_coding_sessions_by_date("2026-09-21")
        assert len(sessions) == 1
        assert sessions[0]["duration_seconds"] == 3600

    def test_date_range_filtered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        result = tmp_vscode_time_db.get_date_range()
        assert result == ("2026-09-20", "2026-09-22")

    def test_clear_filter_restores_all(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        assert tmp_vscode_time_db.get_session_count() == 3
        tmp_vscode_time_db.project_filter = None
        assert tmp_vscode_time_db.get_session_count() == 6

    def test_get_projects_unfiltered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        # get_projects should still return all projects
        projects = tmp_vscode_time_db.get_projects()
        assert len(projects) == 2

    def test_empty_db_with_filter(self, tmp_vscode_time_db):
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        assert tmp_vscode_time_db.get_session_count() == 0
        assert tmp_vscode_time_db.get_total_coding_seconds() == 0
        assert tmp_vscode_time_db.get_daily_totals() == []
        assert tmp_vscode_time_db.get_date_range() is None


# GoalManager filter tests

class TestGoalManagerFilter:
    """Verify GoalManager respects project_filter."""

    def test_get_coding_seconds_for_date_filtered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        manager = GoalManager(tmp_vscode_time_db)
        # 2026-09-21: alpha=3600, beta=1800, total filtered=3600
        result = manager._get_coding_seconds_for_date("2026-09-21")
        assert result == 3600

    def test_get_daily_history_filtered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        manager = GoalManager(tmp_vscode_time_db)
        history = manager.get_daily_history("2026-09-20", "2026-09-22")
        assert len(history) == 3
        totals = {s.date: s.coding_seconds for s in history}
        assert totals["2026-09-20"] == 1800
        assert totals["2026-09-21"] == 3600
        assert totals["2026-09-22"] == 900


# Statistics filter tests

class TestStatisticsFilter:
    """Verify StatisticsCalculator respects project_filter."""

    def test_total_seconds_filtered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        calc = StatisticsCalculator(tmp_vscode_time_db)
        stats = calc.calculate()
        assert stats.total_seconds == 6300

    def test_project_breakdown_filtered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        calc = StatisticsCalculator(tmp_vscode_time_db)
        stats = calc.calculate()
        assert len(stats.projects) == 1
        assert stats.projects[0]["project"] == "/proj/alpha"

    def test_language_totals_filtered(self, tmp_vscode_time_db):
        sessions = [
            make_session(date_to_ms("2026-09-21"), 1800, project="/proj/alpha", language="python"),
            make_session(date_to_ms("2026-09-21"), 600, project="/proj/beta", language="javascript"),
        ]
        insert_sessions(tmp_vscode_time_db, sessions)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        calc = StatisticsCalculator(tmp_vscode_time_db)
        langs = calc._get_language_totals()
        assert len(langs) == 1
        assert langs[0]["language"] == "python"


# Report filter tests

class TestReportFilter:
    """Verify ReportGenerator respects project_filter."""

    def test_report_total_filtered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        gen = ReportGenerator(tmp_vscode_time_db)
        report = gen.generate("7d")
        # alpha sessions on 20th/21st/22nd, all within 7d window
        assert report.total_coding_seconds == 6300

    def test_report_project_breakdown_filtered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        gen = ReportGenerator(tmp_vscode_time_db)
        report = gen.generate("7d")
        assert len(report.projects) == 1
        assert report.projects[0].project == "/proj/alpha"

    def test_report_language_breakdown_filtered(self, tmp_vscode_time_db):
        sessions = [
            make_session(date_to_ms("2026-09-21"), 1800, project="/proj/alpha", language="python"),
            make_session(date_to_ms("2026-09-21"), 600, project="/proj/beta", language="javascript"),
        ]
        insert_sessions(tmp_vscode_time_db, sessions)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        gen = ReportGenerator(tmp_vscode_time_db)
        report = gen.generate("7d")
        assert len(report.languages) == 1
        assert report.languages[0].language == "python"


# Export filter tests

class TestExportFilter:
    """Verify Exporter respects project_filter."""

    def test_export_json_filtered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        exporter = Exporter(tmp_vscode_time_db)
        import json
        data = json.loads(exporter.export_json())
        assert len(data["sessions"]) == 3
        assert all(s["project"] == "/proj/alpha" for s in data["sessions"])

    def test_export_csv_filtered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        exporter = Exporter(tmp_vscode_time_db)
        csv_text = exporter.export_csv()
        lines = csv_text.strip().split("\n")
        # header + 3 rows
        assert len(lines) == 4

    def test_export_no_filter_returns_all(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        exporter = Exporter(tmp_vscode_time_db)
        import json
        data = json.loads(exporter.export_json())
        assert len(data["sessions"]) == 6


# End-to-end filter behavior

class TestFilterEndToEnd:
    """Verify filter works across the full query pipeline."""

    def test_filtered_total_differs_from_unfiltered(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)

        # Unfiltered
        unfiltered_total = tmp_vscode_time_db.get_total_coding_seconds()

        # Filtered
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        filtered_total = tmp_vscode_time_db.get_total_coding_seconds()

        assert filtered_total < unfiltered_total
        assert filtered_total == 6300

    def test_no_sessions_for_missing_project(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/nonexistent"
        assert tmp_vscode_time_db.get_session_count() == 0
        assert tmp_vscode_time_db.get_total_coding_seconds() == 0

    def test_filter_does_not_modify_data(self, tmp_vscode_time_db):
        setup_multi_project_db(tmp_vscode_time_db)
        tmp_vscode_time_db.project_filter = "/proj/alpha"
        # Query with filter
        _ = tmp_vscode_time_db.get_total_coding_seconds()
        # Clear filter — original data intact
        tmp_vscode_time_db.project_filter = None
        assert tmp_vscode_time_db.get_session_count() == 6
        assert tmp_vscode_time_db.get_total_coding_seconds() == 12300

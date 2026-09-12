#!/usr/bin/env python3
"""Phase 9 tests - Configuration & User Preferences.

Tests for the configuration layer and its integration with existing modules.
"""

import sys
import os
import json
import tempfile
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import (
    Config, load_config, get_config_value, set_config_value,
    ConfigError, ConfigValidationError, SUPPORTED_KEYS, DEFAULTS, CONFIG_DIR
)
from goals import (
    GoalManager, validate_goal, parse_goal_input, InvalidGoalError,
    DEFAULT_DAILY_GOAL_SECONDS, format_seconds
)
from storage.database import Database


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


def create_temp_config():
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(suffix='.toml', delete=False) as f:
        return Path(f.name)


def delete_temp_config(config_path):
    """Delete a temporary config file."""
    if config_path.exists():
        config_path.unlink()


def create_temp_db():
    """Create a temporary database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        return Path(f.name)


def delete_temp_db(db_path):
    """Delete a temporary database."""
    if db_path.exists():
        db_path.unlink()


class TestDefaults:
    """Tests for default configuration."""

    def test_missing_config_file(self):
        """Missing config file should use defaults."""
        print("1. MISSING CONFIG FILE TEST")

        temp_path = create_temp_config().parent / "nonexistent_config.toml"
        try:
            config = Config(temp_path)
            config.load()

            assert config.get("daily_goal_seconds") == DEFAULT_DAILY_GOAL_SECONDS
        finally:
            pass  # File doesn't exist, nothing to delete

        print("   PASS")

    def test_default_daily_goal(self):
        """Default daily goal should be 7200 seconds (2 hours)."""
        print("2. DEFAULT DAILY GOAL TEST")

        assert DEFAULT_DAILY_GOAL_SECONDS == 7200

        print("   PASS")

    def test_config_directory_creation(self):
        """Config directory should be created if missing."""
        print("3. CONFIG DIRECTORY CREATION TEST")

        temp_dir = Path(tempfile.mkdtemp())
        temp_config = temp_dir / "subdir" / "config.toml"

        try:
            config = Config(temp_config)
            config.set("daily_goal_seconds", 3600)
            config.save()

            assert temp_config.exists()
            assert temp_config.parent.exists()
        finally:
            import shutil
            shutil.rmtree(temp_dir)

        print("   PASS")


class TestValidConfiguration:
    """Tests for valid configuration."""

    def test_valid_toml(self):
        """Valid TOML should be parsed correctly."""
        print("4. VALID TOML TEST")

        temp_config = create_temp_config()
        try:
            temp_config.write_text('daily_goal_seconds = 3600\n')

            config = Config(temp_config)
            config.load()

            assert config.get("daily_goal_seconds") == 3600
        finally:
            delete_temp_config(temp_config)

        print("   PASS")

    def test_valid_goal(self):
        """Valid goal values should be accepted."""
        print("5. VALID GOAL TEST")

        valid_goals = [60, 3600, 7200, 86400]
        for goal in valid_goals:
            assert validate_goal(goal) is True

        print("   PASS")

    def test_reading_existing_config(self):
        """Existing configuration should be readable."""
        print("6. READING EXISTING CONFIG TEST")

        temp_config = create_temp_config()
        try:
            temp_config.write_text('daily_goal_seconds = 1800\n')

            config = Config(temp_config)
            config.load()

            assert config.get("daily_goal_seconds") == 1800
        finally:
            delete_temp_config(temp_config)

        print("   PASS")


class TestInvalidConfiguration:
    """Tests for invalid configuration."""

    def test_malformed_toml(self):
        """Malformed TOML should raise error."""
        print("7. MALFORMED TOML TEST")

        temp_config = create_temp_config()
        try:
            temp_config.write_text('this is not valid {{{ toml\n')

            config = Config(temp_config)
            try:
                config.load()
                assert False, "Should have raised ConfigError"
            except ConfigError as e:
                assert "Malformed" in str(e)
        finally:
            delete_temp_config(temp_config)

        print("   PASS")

    def test_invalid_goal(self):
        """Invalid goal values should be rejected."""
        print("8. INVALID GOAL TEST")

        invalid_goals = [-1, -3600, 86401, 999999]
        for goal in invalid_goals:
            try:
                validate_goal(goal)
                assert False, f"Should have rejected {goal}"
            except InvalidGoalError:
                pass  # Expected

        print("   PASS")

    def test_negative_goal(self):
        """Negative goals should be rejected."""
        print("9. NEGATIVE GOAL TEST")

        try:
            validate_goal(-1)
            assert False, "Should have rejected -1"
        except InvalidGoalError:
            pass  # Expected

        print("   PASS")


class TestUpdates:
    """Tests for configuration updates."""

    def test_changing_goal(self):
        """Goal should be changeable."""
        print("10. CHANGING GOAL TEST")

        temp_config = create_temp_config()
        try:
            config = Config(temp_config)
            config.load()

            config.set("daily_goal_seconds", 3600)
            config.save()

            config2 = Config(temp_config)
            config2.load()

            assert config2.get("daily_goal_seconds") == 3600
        finally:
            delete_temp_config(temp_config)

        print("   PASS")

    def test_preserving_unrelated_settings(self):
        """Unrelated settings should be preserved."""
        print("11. PRESERVING UNRELATED SETTINGS TEST")

        temp_config = create_temp_config()
        try:
            temp_config.write_text('daily_goal_seconds = 3600\nsome_other_key = "value"\n')

            config = Config(temp_config)
            config.load()

            config.set("daily_goal_seconds", 7200)
            config.save()

            # Read raw file to check preservation
            content = temp_config.read_text()
            assert 'some_other_key = "value"' in content
        finally:
            delete_temp_config(temp_config)

        print("   PASS")

    def test_repeated_updates(self):
        """Repeated updates should work correctly."""
        print("12. REPEATED UPDATES TEST")

        temp_config = create_temp_config()
        try:
            config = Config(temp_config)
            config.load()

            for goal in [3600, 7200, 1800, 5400]:
                config.set("daily_goal_seconds", goal)
                config.save()

                config2 = Config(temp_config)
                config2.load()
                assert config2.get("daily_goal_seconds") == goal
        finally:
            delete_temp_config(temp_config)

        print("   PASS")

    def test_idempotent_writes(self):
        """Writing the same value should be idempotent."""
        print("13. IDEMPOTENT WRITES TEST")

        temp_config = create_temp_config()
        try:
            config = Config(temp_config)
            config.load()

            config.set("daily_goal_seconds", 3600)
            config.save()

            content1 = temp_config.read_text()

            config.save()
            content2 = temp_config.read_text()

            assert content1 == content2
        finally:
            delete_temp_config(temp_config)

        print("   PASS")


class TestMigration:
    """Tests for goal migration."""

    def test_migration_from_db(self):
        """Goal should be migrated from database."""
        print("14. MIGRATION FROM DB TEST")

        temp_db = create_temp_db()
        temp_config = create_temp_config()

        try:
            db = Database(temp_db)
            db.connect()

            # Set goal in database
            db.set_setting("daily_goal_seconds", "3600")

            # Migrate
            from config import migrate_goal_from_db
            goal = migrate_goal_from_db(3600, temp_config)

            assert goal == 3600

            # Verify config file
            config = Config(temp_config)
            config.load()
            assert config.get("daily_goal_seconds") == 3600

            db.close()
        finally:
            delete_temp_db(temp_db)
            delete_temp_config(temp_config)

        print("   PASS")

    def test_migration_only_when_needed(self):
        """Migration should only happen when needed."""
        print("15. MIGRATION ONLY WHEN NEEDED TEST")

        temp_config = create_temp_config()
        try:
            # Set a non-default value in config
            temp_config.write_text('daily_goal_seconds = 1800\n')

            from config import migrate_goal_from_db

            # Should not change existing non-default value
            goal = migrate_goal_from_db(3600, temp_config)

            assert goal == 1800  # Config takes precedence

            config = Config(temp_config)
            config.load()
            assert config.get("daily_goal_seconds") == 1800
        finally:
            delete_temp_config(temp_config)

        print("   PASS")

    def test_repeated_migration_safe(self):
        """Repeated migration should be safe."""
        print("16. REPEATED MIGRATION SAFE TEST")

        temp_config = create_temp_config()

        try:
            from config import migrate_goal_from_db

            migrate_goal_from_db(3600, temp_config)
            migrate_goal_from_db(3600, temp_config)
            migrate_goal_from_db(3600, temp_config)

            config = Config(temp_config)
            config.load()
            assert config.get("daily_goal_seconds") == 3600
        finally:
            delete_temp_config(temp_config)

        print("   PASS")

    def test_no_coding_sessions_modified(self):
        """Migration should not modify coding sessions."""
        print("17. NO CODING SESSIONS MODIFIED TEST")

        temp_db = create_temp_db()
        temp_config = create_temp_config()

        try:
            db = Database(temp_db)
            db.connect()

            # Insert a session
            session = type('Session', (), {
                'record_id': 'test_123',
                'session_type': 2,
                'start_time': 1694500000000,
                'duration_seconds': 300,
                'language': 'python',
                'file': '/test/file.py',
                'project': '/test/project',
                'vcs': 'git',
                'line_count': 100,
                'char_count': 1000,
                'source_file': 'test.db',
            })()

            db.insert_coding_session(session)
            count_before = db.get_session_count()

            # Migrate
            from config import migrate_goal_from_db
            migrate_goal_from_db(3600, temp_config)

            count_after = db.get_session_count()
            assert count_before == count_after

            db.close()
        finally:
            delete_temp_db(temp_db)
            delete_temp_config(temp_config)

        print("   PASS")


class TestCLI:
    """Tests for CLI commands."""

    def test_config_command(self):
        """config command should work."""
        print("18. CONFIG COMMAND TEST")

        result = run_cmd(["config"])
        assert result.returncode == 0
        assert "Configuration" in result.stdout
        assert "Daily goal:" in result.stdout

        print("   PASS")

    def test_config_goal_command(self):
        """config daily_goal_seconds should show goal."""
        print("19. CONFIG GOAL COMMAND TEST")

        result = run_cmd(["config", "daily_goal_seconds"])
        assert result.returncode == 0

        print("   PASS")

    def test_goal_command(self):
        """goal command should show current goal."""
        print("20. GOAL COMMAND TEST")

        result = run_cmd(["goal"])
        assert result.returncode == 0
        assert "Current daily goal:" in result.stdout

        print("   PASS")


class TestIntegration:
    """Tests for integration with existing modules."""

    def test_goal_manager_uses_config(self):
        """GoalManager should use config for goal."""
        print("21. GOAL MANAGER USES CONFIG TEST")

        temp_db = create_temp_db()

        try:
            db = Database(temp_db)
            db.connect()

            # GoalManager reads from the default config file
            # This test verifies it doesn't crash and returns a valid goal
            manager = GoalManager(db)
            goal = manager.get_goal()

            # Goal should be a valid positive integer
            assert isinstance(goal, int)
            assert goal > 0
            assert goal <= 86400

            db.close()
        finally:
            delete_temp_db(temp_db)

        print("   PASS")


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_existing_commands_unaffected(self):
        """Existing commands should continue working."""
        print("22. BACKWARD COMPATIBILITY TEST")

        commands = [
            ["today"],
            ["history", "7"],
            ["goal"],
            ["streak"],
            ["stats"],
            ["report"],
            ["status"],
            ["sync"],
            ["export", "--json"],
        ]

        for cmd in commands:
            result = run_cmd(cmd)
            assert result.returncode == 0, f"Command {cmd} failed"

        print("   PASS")


class TestRealDataVerification:
    """Tests for real data verification."""

    def test_real_data_config(self):
        """Real data config should work."""
        print("23. REAL DATA CONFIG TEST")

        result = run_cmd(["config"])
        assert result.returncode == 0
        assert "Configuration" in result.stdout

        print("   PASS")

    def test_real_data_goal(self):
        """Real data goal should work."""
        print("24. REAL DATA GOAL TEST")

        result = run_cmd(["goal"])
        assert result.returncode == 0
        assert "Current daily goal:" in result.stdout

        print("   PASS")


def run_all_tests():
    """Run all Phase 9 tests."""
    print("=" * 70)
    print("PHASE 9 TESTS - CONFIGURATION & USER PREFERENCES")
    print("=" * 70)

    test_classes = [
        TestDefaults,
        TestValidConfiguration,
        TestInvalidConfiguration,
        TestUpdates,
        TestMigration,
        TestCLI,
        TestIntegration,
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

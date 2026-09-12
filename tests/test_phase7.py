#!/usr/bin/env python3
"""Phase 7 tests - CLI/UX Refinement & Interface Stability.

Tests for CLI behavior, help, errors, exit codes, and UX consistency.
"""

import sys
import os
import json
import subprocess
from pathlib import Path


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


class TestHelp:
    """Tests for help output."""

    def test_top_level_help(self):
        """Top-level --help should work."""
        print("1. TOP-LEVEL HELP TEST")

        result = run_cmd(["--help"])
        assert result.returncode == 0, f"Exit code: {result.returncode}"
        assert "Usage:" in result.stdout, "Missing Usage line"
        assert "Commands:" in result.stdout, "Missing Commands section"
        assert "sync" in result.stdout, "Missing sync command"
        assert "today" in result.stdout, "Missing today command"
        assert "history" in result.stdout, "Missing history command"
        assert "goal" in result.stdout, "Missing goal command"
        assert "streak" in result.stdout, "Missing streak command"
        assert "stats" in result.stdout, "Missing stats command"
        assert "report" in result.stdout, "Missing report command"
        assert "status" in result.stdout, "Missing status command"

        print("   PASS")

    def test_short_help(self):
        """Short -h flag should work."""
        print("2. SHORT HELP TEST")

        result = run_cmd(["-h"])
        assert result.returncode == 0
        assert "Usage:" in result.stdout

        print("   PASS")

    def test_help_flag(self):
        """--help flag should work."""
        print("3. HELP FLAG TEST")

        result = run_cmd(["--help"])
        assert result.returncode == 0
        assert "Usage:" in result.stdout

        print("   PASS")

    def test_command_help_report(self):
        """report --help should show command-specific help."""
        print("4. COMMAND HELP REPORT TEST")

        result = run_cmd(["report", "--help"])
        assert result.returncode == 0
        assert "Usage:" in result.stdout
        assert "range" in result.stdout.lower()

        print("   PASS")

    def test_command_help_goal(self):
        """goal --help should show command-specific help."""
        print("5. COMMAND HELP GOAL TEST")

        result = run_cmd(["goal", "--help"])
        assert result.returncode == 0
        assert "Usage:" in result.stdout

        print("   PASS")

    def test_command_help_sync(self):
        """sync --help should show command-specific help."""
        print("6. COMMAND HELP SYNC TEST")

        result = run_cmd(["sync", "--help"])
        assert result.returncode == 0
        assert "Usage:" in result.stdout

        print("   PASS")


class TestVersion:
    """Tests for version output."""

    def test_version(self):
        """--version should work."""
        print("7. VERSION TEST")

        result = run_cmd(["--version"])
        assert result.returncode == 0
        assert "vscode-time" in result.stdout
        assert "0.1.0" in result.stdout

        print("   PASS")

    def test_short_version(self):
        """-v should work."""
        print("8. SHORT VERSION TEST")

        result = run_cmd(["-v"])
        assert result.returncode == 0
        assert "vscode-time" in result.stdout

        print("   PASS")


class TestValidCommands:
    """Tests for valid commands."""

    def test_today(self):
        """today command should work."""
        print("9. TODAY TEST")

        result = run_cmd(["today"])
        assert result.returncode == 0
        assert "Date:" in result.stdout
        assert "Goal:" in result.stdout
        assert "Coding:" in result.stdout
        assert "Status:" in result.stdout

        print("   PASS")

    def test_history(self):
        """history command should work."""
        print("10. HISTORY TEST")

        result = run_cmd(["history", "7"])
        assert result.returncode == 0
        assert "Daily coding history" in result.stdout

        print("   PASS")

    def test_goal(self):
        """goal command should work."""
        print("11. GOAL TEST")

        result = run_cmd(["goal"])
        assert result.returncode == 0
        assert "Current daily goal:" in result.stdout

        print("   PASS")

    def test_streak(self):
        """streak command should work."""
        print("12. STREAK TEST")

        result = run_cmd(["streak"])
        assert result.returncode == 0
        assert "Current streak:" in result.stdout
        assert "Longest streak:" in result.stdout

        print("   PASS")

    def test_stats(self):
        """stats command should work."""
        print("13. STATS TEST")

        result = run_cmd(["stats"])
        assert result.returncode == 0
        assert "Total coding:" in result.stdout
        assert "Active days:" in result.stdout

        print("   PASS")

    def test_report(self):
        """report command should work."""
        print("14. REPORT TEST")

        result = run_cmd(["report"])
        assert result.returncode == 0
        assert "Coding Report" in result.stdout

        print("   PASS")

    def test_status(self):
        """status command should work."""
        print("15. STATUS TEST")

        result = run_cmd(["status"])
        assert result.returncode == 0
        assert "Today" in result.stdout
        assert "Coding:" in result.stdout
        assert "Goal:" in result.stdout

        print("   PASS")

    def test_sync(self):
        """sync command should work."""
        print("16. SYNC TEST")

        result = run_cmd(["sync"])
        assert result.returncode == 0
        assert "Sync complete" in result.stdout

        print("   PASS")


class TestInvalidCommands:
    """Tests for invalid commands."""

    def test_unknown_command(self):
        """Unknown command should fail."""
        print("17. UNKNOWN COMMAND TEST")

        result = run_cmd(["something"])
        assert result.returncode != 0
        assert "Error:" in result.stderr
        assert "unknown command" in result.stderr.lower()

        print("   PASS")

    def test_invalid_report_range(self):
        """Invalid report range should fail."""
        print("18. INVALID REPORT RANGE TEST")

        result = run_cmd(["report", "90d"])
        assert result.returncode != 0
        assert "Error:" in result.stderr
        assert "90d" in result.stderr

        print("   PASS")

    def test_invalid_goal(self):
        """Invalid goal should fail."""
        print("19. INVALID GOAL TEST")

        result = run_cmd(["goal", "-1h"])
        assert result.returncode != 0
        assert "Error:" in result.stderr

        print("   PASS")

    def test_invalid_history_days(self):
        """Invalid history days should fail."""
        print("20. INVALID HISTORY DAYS TEST")

        result = run_cmd(["history", "abc"])
        assert result.returncode != 0
        assert "Error:" in result.stderr

        print("   PASS")


class TestExitCodes:
    """Tests for exit codes."""

    def test_valid_command_exit_0(self):
        """Valid commands should return 0."""
        print("21. VALID COMMAND EXIT CODE TEST")

        valid_commands = [
            ["today"],
            ["history", "7"],
            ["goal"],
            ["streak"],
            ["stats"],
            ["report"],
            ["status"],
            ["sync"],
            ["--help"],
            ["--version"],
        ]

        for cmd in valid_commands:
            result = run_cmd(cmd)
            assert result.returncode == 0, f"Command {cmd} returned {result.returncode}"

        print("   PASS")

    def test_invalid_command_exit_nonzero(self):
        """Invalid commands should return non-zero."""
        print("22. INVALID COMMAND EXIT CODE TEST")

        invalid_commands = [
            ["something"],
            ["report", "90d"],
            ["goal", "-1h"],
            ["history", "abc"],
        ]

        for cmd in invalid_commands:
            result = run_cmd(cmd)
            assert result.returncode != 0, f"Command {cmd} should return non-zero"

        print("   PASS")


class TestErrorStreams:
    """Tests for stdout/stderr separation."""

    def test_errors_to_stderr(self):
        """Errors should go to stderr."""
        print("23. ERRORS TO STDERR TEST")

        result = run_cmd(["report", "90d"])
        assert result.returncode != 0
        assert len(result.stdout.strip()) == 0, f"stdout should be empty: {result.stdout}"
        assert "Error:" in result.stderr

        print("   PASS")

    def test_success_to_stdout(self):
        """Success output should go to stdout."""
        print("24. SUCCESS TO STDOUT TEST")

        result = run_cmd(["today"])
        assert result.returncode == 0
        assert len(result.stderr.strip()) == 0, f"stderr should be empty: {result.stderr}"
        assert "Date:" in result.stdout

        print("   PASS")


class TestJSONOutput:
    """Tests for JSON output."""

    def test_status_json_valid(self):
        """status --json should produce valid JSON."""
        print("25. STATUS JSON VALID TEST")

        result = run_cmd(["status", "--json"])
        assert result.returncode == 0

        try:
            data = json.loads(result.stdout)
            assert "date" in data
            assert "coding_seconds" in data
            assert "goal_met" in data
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON: {e}")

        print("   PASS")

    def test_report_json_valid(self):
        """report --json should produce valid JSON."""
        print("26. REPORT JSON VALID TEST")

        result = run_cmd(["report", "--json"])
        assert result.returncode == 0

        try:
            data = json.loads(result.stdout)
            assert "total_coding_seconds" in data
            assert "daily" in data
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON: {e}")

        print("   PASS")

    def test_json_no_decorative_text(self):
        """JSON output should not contain decorative text."""
        print("27. JSON NO DECORATIVE TEXT TEST")

        result = run_cmd(["status", "--json"])
        assert result.returncode == 0

        # Should not contain common decorative patterns
        assert "──" not in result.stdout
        assert "══" not in result.stdout

        print("   PASS")


class TestBackwardCompatibility:
    """Tests for backward compatibility."""

    def test_existing_commands_work(self):
        """All existing commands should continue working."""
        print("28. BACKWARD COMPATIBILITY TEST")

        commands = [
            ["today"],
            ["history", "7"],
            ["goal"],
            ["goal", "1h"],
            ["streak"],
            ["stats"],
            ["report"],
            ["report", "7d"],
            ["report", "--json"],
            ["status"],
            ["status", "--json"],
            ["sync"],
            ["--version"],
        ]

        for cmd in commands:
            result = run_cmd(cmd)
            assert result.returncode == 0, f"Command {cmd} failed: {result.stderr}"

        print("   PASS")


class TestConsistency:
    """Tests for cross-command consistency."""

    def test_today_status_consistency(self):
        """today and status should show same coding time."""
        print("29. TODAY-STATUS CONSISTENCY TEST")

        result_today = run_cmd(["today"])
        result_status = run_cmd(["status"])

        assert result_today.returncode == 0
        assert result_status.returncode == 0

        # Extract coding times
        today_coding = None
        status_coding = None

        for line in result_today.stdout.split("\n"):
            if "Coding:" in line:
                today_coding = line.split(":")[1].strip()
                break

        for line in result_status.stdout.split("\n"):
            if "Coding:" in line:
                status_coding = line.split(":")[1].strip()
                break

        assert today_coding == status_coding, \
            f"Coding times differ: today={today_coding}, status={status_coding}"

        print("   PASS")


class TestShellScripting:
    """Tests for shell scripting compatibility."""

    def test_json_pipeline(self):
        """JSON should work in pipelines."""
        print("30. JSON PIPELINE TEST")

        result = subprocess.run(
            "cd /home/taksh/Work/vscode-time && ./vscode-time status --json | python3 -m json.tool > /dev/null",
            shell=True,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

        print("   PASS")

    def test_json_file_redirect(self):
        """JSON should work with file redirection."""
        print("31. JSON FILE REDIRECT TEST")

        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            result = subprocess.run(
                f"cd /home/taksh/Work/vscode-time && ./vscode-time report --json > {temp_path}",
                shell=True,
                capture_output=True,
                text=True
            )
            assert result.returncode == 0

            with open(temp_path) as f:
                data = json.load(f)
            assert "total_coding_seconds" in data
        finally:
            os.unlink(temp_path)

        print("   PASS")


class TestExitCodeHelp:
    """Tests for help/version exit codes."""

    def test_help_exit_code_0(self):
        """--help should return 0."""
        print("32. HELP EXIT CODE TEST")

        result = run_cmd(["--help"])
        assert result.returncode == 0

        print("   PASS")

    def test_version_exit_code_0(self):
        """--version should return 0."""
        print("33. VERSION EXIT CODE TEST")

        result = run_cmd(["--version"])
        assert result.returncode == 0

        print("   PASS")


def run_all_tests():
    """Run all Phase 7 tests."""
    print("=" * 70)
    print("PHASE 7 TESTS - CLI/UX REFINEMENT & INTERFACE STABILITY")
    print("=" * 70)

    test_classes = [
        TestHelp,
        TestVersion,
        TestValidCommands,
        TestInvalidCommands,
        TestExitCodes,
        TestErrorStreams,
        TestJSONOutput,
        TestBackwardCompatibility,
        TestConsistency,
        TestShellScripting,
        TestExitCodeHelp,
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

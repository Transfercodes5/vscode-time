#!/usr/bin/env python3
"""Tests for Phase 6A - Installation & Packaging.

This script tests the installation and uninstallation mechanisms.
"""

import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_version():
    """Test that --version flag works."""
    print("1. VERSION TEST")
    
    result = subprocess.run(
        ["./vscode-time", "--version"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert "vscode-time 0.1.0" in result.stdout, f"Version output invalid: {result.stdout}"
    
    print("   PASS: --version works")


def test_cli_outside_repository():
    """Test that CLI works outside the repository."""
    print("\n2. CLI OUTSIDE REPOSITORY TEST")
    
    # Create a temporary directory and run vscode-time from there
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [os.path.join(os.path.dirname(__file__), '..', 'vscode-time'), "--version"],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )
        
        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert "vscode-time 0.1.0" in result.stdout, f"Version output invalid: {result.stdout}"
    
    print("   PASS: CLI works outside repository")


def test_json_outside_repository():
    """Test that JSON output works outside the repository."""
    print("\n3. JSON OUTSIDE REPOSITORY TEST")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [os.path.join(os.path.dirname(__file__), '..', 'vscode-time'), "status", "--json"],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )
        
        assert result.returncode == 0, f"Command failed: {result.stderr}"
        
        import json
        try:
            data = json.loads(result.stdout)
            assert "date" in data, "Missing date field"
            assert "coding_seconds" in data, "Missing coding_seconds field"
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON: {e}")
    
    print("   PASS: JSON works outside repository")


def test_waybar_outside_repository():
    """Test that Waybar formatter works outside the repository."""
    print("\n4. WAYBAR OUTSIDE REPOSITORY TEST")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [os.path.join(os.path.dirname(__file__), '..', 'waybar', 'vscode-time.sh')],
            capture_output=True,
            text=True,
            cwd=tmpdir
        )
        
        assert result.returncode == 0, f"Command failed: {result.stderr}"
        
        import json
        try:
            data = json.loads(result.stdout)
            assert "text" in data, "Missing text field"
            assert "tooltip" in data, "Missing tooltip field"
            assert "class" in data, "Missing class field"
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON: {e}")
    
    print("   PASS: Waybar formatter works outside repository")


def test_installation_idempotent():
    """Test that running install twice doesn't duplicate files."""
    print("\n5. INSTALLATION IDEMPOTENT TEST")
    
    # Run installation twice
    result1 = subprocess.run(
        ["./install.sh"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    result2 = subprocess.run(
        ["./install.sh"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result1.returncode == 0, f"First installation failed: {result1.stderr}"
    assert result2.returncode == 0, f"Second installation failed: {result2.stderr}"
    
    # Verify files exist
    local_bin = Path.home() / ".local" / "bin"
    assert (local_bin / "vscode-time").exists(), "vscode-time not installed"
    assert (local_bin / "vscode-time-waybar").exists(), "vscode-time-waybar not installed"
    
    print("   PASS: Installation is idempotent")


def test_data_preservation():
    """Test that installation/uninstallation preserves user data."""
    print("\n6. DATA PRESERVATION TEST")
    
    # Check that database exists
    db_path = Path.home() / ".local" / "share" / "vscode-time" / "vscode-time.db"
    db_exists_before = db_path.exists()
    
    # Run installation
    result = subprocess.run(
        ["./install.sh"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Installation failed: {result.stderr}"
    
    # Check that database still exists
    db_exists_after = db_path.exists()
    
    assert db_exists_before == db_exists_after, "Database existence changed after installation"
    
    print("   PASS: Data preservation verified")


def test_uninstallation():
    """Test that uninstallation removes installed files."""
    print("\n7. UNINSTALLATION TEST")
    
    # Run uninstallation
    result = subprocess.run(
        ["./uninstall.sh"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Uninstallation failed: {result.stderr}"
    
    # Verify files are removed
    local_bin = Path.home() / ".local" / "bin"
    local_lib = Path.home() / ".local" / "lib" / "vscode-time"
    
    assert not (local_bin / "vscode-time").exists(), "vscode-time still exists after uninstall"
    assert not (local_bin / "vscode-time-waybar").exists(), "vscode-time-waybar still exists after uninstall"
    assert not local_lib.exists(), "vscode-time library still exists after uninstall"
    
    # Verify database is preserved
    db_path = Path.home() / ".local" / "share" / "vscode-time" / "vscode-time.db"
    assert db_path.exists(), "Database was deleted during uninstallation"
    
    print("   PASS: Uninstallation works correctly")


def test_reinstall_and_verify():
    """Test that reinstalling works and history is preserved."""
    print("\n8. REINSTALL AND VERIFY TEST")
    
    # Reinstall
    result = subprocess.run(
        ["./install.sh"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"Reinstallation failed: {result.stderr}"
    
    # Verify CLI works
    result = subprocess.run(
        [str(Path.home() / ".local" / "bin" / "vscode-time"), "--version"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "vscode-time 0.1.0" in result.stdout, f"Version output invalid: {result.stdout}"
    
    # Verify stats show historical data
    result = subprocess.run(
        [str(Path.home() / ".local" / "bin" / "vscode-time"), "stats"],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Stats command failed: {result.stderr}"
    assert "Total coding:" in result.stdout, "Stats output invalid"
    
    print("   PASS: Reinstall and verify")


def test_phase4a_regression():
    """Test Phase 4A functionality still works."""
    print("\n9. PHASE 4A REGRESSION TEST")
    
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
    print("\n10. PHASE 4B REGRESSION TEST")
    
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
    print("\n11. PHASE 5 REGRESSION TEST")
    
    # Test JSON status
    result = subprocess.run(
        ["./vscode-time", "status", "--json"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    
    assert result.returncode == 0, f"JSON status failed: {result.stderr}"
    
    import json
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


def main():
    """Run all tests."""
    print("=" * 70)
    print("PHASE 6A TESTS - INSTALLATION & PACKAGING")
    print("=" * 70)
    
    try:
        test_version()
        test_cli_outside_repository()
        test_json_outside_repository()
        test_waybar_outside_repository()
        test_installation_idempotent()
        test_data_preservation()
        test_uninstallation()
        test_reinstall_and_verify()
        test_phase4a_regression()
        test_phase4b_regression()
        test_phase5_regression()
        
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
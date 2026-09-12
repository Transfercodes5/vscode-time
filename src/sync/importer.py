"""Sync module for importing coding records from vscode-coding-tracker.

This module coordinates the import of coding sessions from the source
extension's database files into the vscode-time SQLite database.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from adapter.coding_tracker import (
    CodingTrackerAdapter,
    Session,
    discover_db_files,
    parse_db_file,
    filter_coding_sessions,
)
from storage.database import Database


class ImportResult:
    """Result of an import operation."""

    def __init__(self):
        self.source_files: int = 0
        self.source_records: int = 0
        self.coding_records: int = 0
        self.new_imported: int = 0
        self.already_imported: int = 0
        self.rejected: int = 0
        self.errors: List[str] = []

    def __repr__(self):
        return (
            f"ImportResult(files={self.source_files}, "
            f"records={self.source_records}, coding={self.coding_records}, "
            f"new={self.new_imported}, existing={self.already_imported}, "
            f"rejected={self.rejected})"
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary for reporting."""
        return {
            "source_files": self.source_files,
            "source_records": self.source_records,
            "coding_records": self.coding_records,
            "new_imported": self.new_imported,
            "already_imported": self.already_imported,
            "rejected": self.rejected,
            "errors": self.errors,
        }


class Importer:
    """Importer for coding records from vscode-coding-tracker."""

    def __init__(self, db: Database, adapter: Optional[CodingTrackerAdapter] = None):
        self.db = db
        self.adapter = adapter or CodingTrackerAdapter()

    def sync(self, source_dir: Optional[Path] = None) -> ImportResult:
        """Import coding records from source files.

        This is the main sync operation. It:
        1. Discovers source files
        2. Parses them through the adapter
        3. Filters to type-2 coding records
        4. Generates deterministic IDs
        5. Inserts new records (ignores duplicates)

        Args:
            source_dir: Optional override for source directory.

        Returns:
            ImportResult with statistics about the import.
        """
        result = ImportResult()

        # Override adapter source directory if provided
        if source_dir:
            self.adapter = CodingTrackerAdapter(source_dir)

        # 1. Discover source files
        db_files = self.adapter.get_files()
        result.source_files = len(db_files)

        if not db_files:
            result.errors.append("No source files found in ~/.coding-tracker/")
            return result

        # 2. Parse all source files
        all_sessions: List[Session] = []
        for db_file in db_files:
            try:
                sessions, valid, rejected = parse_db_file(db_file)
                all_sessions.extend(sessions)
                result.source_records += valid
                result.rejected += rejected
            except Exception as e:
                result.errors.append(f"Error parsing {db_file.name}: {str(e)}")

        # 3. Filter to coding records only (type 2)
        coding_sessions = filter_coding_sessions(all_sessions)
        result.coding_records = len(coding_sessions)

        # 4. Insert into database (batch operation with duplicate handling)
        if coding_sessions:
            inserted, duplicates = self.db.insert_coding_sessions_batch(coding_sessions)
            result.new_imported = inserted
            result.already_imported = duplicates

        # 5. Update sync state
        if db_files:
            last_file = max(db_files, key=lambda f: f.stat().st_mtime)
            last_record = coding_sessions[-1].record_id if coding_sessions else ""
            self.db.update_sync_state(
                source="vscode-coding-tracker",
                last_sync_time=datetime.now(timezone.utc).isoformat(),
                last_seen_file=last_file.name,
                last_seen_record=last_record,
                records_imported=result.new_imported,
            )

        return result

    def get_summary(self) -> Dict:
        """Get a summary of the current database state."""
        return {
            "schema_version": self.db.get_schema_version(),
            "session_count": self.db.get_session_count(),
            "total_coding_seconds": self.db.get_total_coding_seconds(),
            "date_range": self.db.get_date_range(),
            "daily_totals": self.db.get_daily_totals(),
            "project_totals": self.db.get_project_totals(),
        }
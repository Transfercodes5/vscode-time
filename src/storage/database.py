"""SQLite database for vscode-time persistent storage.

This module manages the local SQLite database that stores coding sessions,
sync state, and application settings. The database is the persistent
foundation for goals, streaks, and statistics.
"""

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

# Database schema version
SCHEMA_VERSION = 1

# Default database location
DEFAULT_DB_DIR = Path.home() / ".local" / "share" / "vscode-time"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "vscode-time.db"


class Database:
    """SQLite database for vscode-time persistent storage."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Open database connection and ensure schema exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _create_schema(self) -> None:
        """Create database schema if not exists."""
        cursor = self._conn.cursor()

        # Schema version table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)

        # Check if schema exists
        cursor.execute("SELECT version FROM schema_version LIMIT 1")
        row = cursor.fetchone()

        if row is None:
            # New database - create schema
            self._create_tables(cursor)
            cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
            self._conn.commit()
        elif row["version"] < SCHEMA_VERSION:
            # Schema needs migration
            self._migrate_schema(cursor, row["version"])
            cursor.execute("UPDATE schema_version SET version = ?", (SCHEMA_VERSION,))
            self._conn.commit()

    def _create_tables(self, cursor: sqlite3.Cursor) -> None:
        """Create all database tables."""
        # Coding sessions table
        cursor.execute("""
            CREATE TABLE coding_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                session_type INTEGER NOT NULL,
                start_time INTEGER NOT NULL,
                duration_seconds INTEGER NOT NULL,
                language TEXT NOT NULL,
                file TEXT NOT NULL,
                project TEXT NOT NULL,
                vcs TEXT NOT NULL,
                line_count INTEGER NOT NULL,
                char_count INTEGER NOT NULL,
                source_file TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                UNIQUE(source, source_id)
            )
        """)

        # Sync state table
        cursor.execute("""
            CREATE TABLE sync_state (
                source TEXT PRIMARY KEY,
                last_sync_time TEXT NOT NULL,
                last_seen_file TEXT NOT NULL,
                last_seen_record TEXT NOT NULL,
                records_imported INTEGER NOT NULL
            )
        """)

        # Settings table
        cursor.execute("""
            CREATE TABLE settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Indexes for performance
        cursor.execute("""
            CREATE INDEX idx_sessions_start ON coding_sessions(start_time)
        """)
        cursor.execute("""
            CREATE INDEX idx_sessions_project ON coding_sessions(project)
        """)
        cursor.execute("""
            CREATE INDEX idx_sessions_language ON coding_sessions(language)
        """)
        cursor.execute("""
            CREATE INDEX idx_sessions_imported ON coding_sessions(imported_at)
        """)

    def _migrate_schema(self, cursor: sqlite3.Cursor, current_version: int) -> None:
        """Migrate schema from current_version to SCHEMA_VERSION.

        Future migrations would be implemented here.
        For now, this is a placeholder for when schema evolves.
        """
        # Example migration pattern:
        # if current_version < 2:
        #     cursor.execute("ALTER TABLE coding_sessions ADD COLUMN new_field TEXT")
        #     current_version = 2
        pass

    def get_schema_version(self) -> int:
        """Get current schema version."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT version FROM schema_version LIMIT 1")
        row = cursor.fetchone()
        return row["version"] if row else 0

    def insert_coding_session(self, session: Any) -> bool:
        """Insert a coding session.

        Returns True if inserted, False if duplicate (already exists).
        """
        cursor = self._conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO coding_sessions (
                    source, source_id, session_type, start_time,
                    duration_seconds, language, file, project,
                    vcs, line_count, char_count, source_file, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "vscode-coding-tracker",
                session.record_id,
                session.session_type,
                session.start_time,
                session.duration_seconds,
                session.language,
                session.file,
                session.project,
                session.vcs,
                session.line_count,
                session.char_count,
                session.source_file,
                datetime.now(timezone.utc).isoformat(),
            ))
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            # Duplicate record - ignore
            return False

    def insert_coding_sessions_batch(self, sessions: List[Any]) -> Tuple[int, int]:
        """Insert multiple coding sessions in a transaction.

        Returns:
            (inserted_count, duplicate_count)
        """
        inserted = 0
        duplicates = 0

        cursor = self._conn.cursor()
        cursor.execute("BEGIN")

        try:
            for session in sessions:
                try:
                    cursor.execute("""
                        INSERT INTO coding_sessions (
                            source, source_id, session_type, start_time,
                            duration_seconds, language, file, project,
                            vcs, line_count, char_count, source_file, imported_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        "vscode-coding-tracker",
                        session.record_id,
                        session.session_type,
                        session.start_time,
                        session.duration_seconds,
                        session.language,
                        session.file,
                        session.project,
                        session.vcs,
                        session.line_count,
                        session.char_count,
                        session.source_file,
                        datetime.now(timezone.utc).isoformat(),
                    ))
                    inserted += 1
                except sqlite3.IntegrityError:
                    duplicates += 1

            self._conn.commit()
            return inserted, duplicates

        except Exception as e:
            self._conn.rollback()
            raise e

    def get_coding_sessions(self, limit: Optional[int] = None) -> List[Dict]:
        """Get all coding sessions."""
        cursor = self._conn.cursor()
        if limit:
            cursor.execute(
                "SELECT * FROM coding_sessions ORDER BY start_time DESC LIMIT ?",
                (limit,)
            )
        else:
            cursor.execute("SELECT * FROM coding_sessions ORDER BY start_time DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_coding_sessions_by_date(self, date_str: str) -> List[Dict]:
        """Get coding sessions for a specific date (YYYY-MM-DD)."""
        cursor = self._conn.cursor()
        # Convert date string to epoch ms range using local timezone
        local_tz = datetime.now().astimezone().tzinfo
        dt_start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=local_tz)
        dt_end = dt_start + timedelta(days=1)

        start_ms = int(dt_start.timestamp() * 1000)
        end_ms = int(dt_end.timestamp() * 1000)

        cursor.execute(
            "SELECT * FROM coding_sessions WHERE start_time >= ? AND start_time < ? ORDER BY start_time",
            (start_ms, end_ms)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_daily_totals(self) -> List[Dict]:
        """Get total coding seconds per calendar day (using local timezone)."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT
                date(start_time / 1000, 'unixepoch', 'localtime') as day,
                SUM(duration_seconds) as total_seconds,
                COUNT(*) as session_count
            FROM coding_sessions
            GROUP BY day
            ORDER BY day DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_project_totals(self) -> List[Dict]:
        """Get total coding seconds per project."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT
                project,
                SUM(duration_seconds) as total_seconds,
                COUNT(*) as session_count
            FROM coding_sessions
            GROUP BY project
            ORDER BY total_seconds DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_total_coding_seconds(self) -> int:
        """Get total coding seconds across all sessions."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(duration_seconds), 0) as total FROM coding_sessions")
        row = cursor.fetchone()
        return row["total"]

    def get_session_count(self) -> int:
        """Get total number of coding sessions."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM coding_sessions")
        row = cursor.fetchone()
        return row["count"]

    def get_date_range(self) -> Optional[Tuple[str, str]]:
        """Get the date range of coding sessions (local timezone)."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT
                date(MIN(start_time) / 1000, 'unixepoch', 'localtime') as earliest,
                date(MAX(start_time) / 1000, 'unixepoch', 'localtime') as latest
            FROM coding_sessions
        """)
        row = cursor.fetchone()
        if row and row["earliest"] and row["latest"]:
            return (row["earliest"], row["latest"])
        return None

    def update_sync_state(self, source: str, last_sync_time: str,
                          last_seen_file: str, last_seen_record: str,
                          records_imported: int) -> None:
        """Update sync state for a source."""
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sync_state (
                source, last_sync_time, last_seen_file,
                last_seen_record, records_imported
            ) VALUES (?, ?, ?, ?, ?)
        """, (source, last_sync_time, last_seen_file, last_seen_record, records_imported))
        self._conn.commit()

    def get_sync_state(self, source: str) -> Optional[Dict]:
        """Get sync state for a source."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM sync_state WHERE source = ?", (source,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def set_setting(self, key: str, value: str) -> None:
        """Set a configuration setting."""
        cursor = self._conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        self._conn.commit()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a configuration setting."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default
"""Data export for vscode-time.

This module provides export functionality for coding session data.
It supports JSON and CSV formats with optional date range filtering.

Export is read-only and does not modify the database or source files.
"""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from storage.database import Database
from reports import parse_range, TimeRange, InvalidRangeError, SUPPORTED_RANGES


# Export format version
EXPORT_VERSION = 1

# Supported export formats
SUPPORTED_FORMATS = ["json", "csv"]

# CSV columns in export order
CSV_COLUMNS = [
    "source",
    "source_id",
    "session_type",
    "start_time",
    "duration_seconds",
    "language",
    "file",
    "project",
    "vcs",
    "line_count",
    "char_count",
    "source_file",
]


class ExportError(Exception):
    """Error during export operation."""
    pass


class Exporter:
    """Exporter for coding session data."""

    def __init__(self, db: Database):
        self.db = db

    def get_sessions(
        self,
        range_str: Optional[str] = None,
    ) -> List[Dict]:
        """Get coding sessions for export.

        Args:
            range_str: Optional time range ("today", "yesterday", "7d", "30d").
                       If None, exports all sessions.

        Returns:
            List of session dictionaries ordered deterministically.
        """
        cursor = self.db._conn.cursor()

        if range_str:
            try:
                time_range = parse_range(range_str)
            except InvalidRangeError:
                raise

            # Convert date range to epoch ms using local timezone
            local_tz = datetime.now().astimezone().tzinfo
            dt_start = datetime.strptime(time_range.start_date, "%Y-%m-%d").replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=local_tz
            )
            dt_end = datetime.strptime(time_range.end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=local_tz
            )

            start_ms = int(dt_start.timestamp() * 1000)
            end_ms = int(dt_end.timestamp() * 1000)

            cursor.execute("""
                SELECT
                    source, source_id, session_type, start_time,
                    duration_seconds, language, file, project,
                    vcs, line_count, char_count, source_file
                FROM coding_sessions
                WHERE session_type = 2
                  AND start_time >= ? AND start_time <= ?
                ORDER BY start_time ASC, source ASC, source_id ASC
            """, (start_ms, end_ms))
        else:
            cursor.execute("""
                SELECT
                    source, source_id, session_type, start_time,
                    duration_seconds, language, file, project,
                    vcs, line_count, char_count, source_file
                FROM coding_sessions
                WHERE session_type = 2
                ORDER BY start_time ASC, source ASC, source_id ASC
            """)

        return [dict(row) for row in cursor.fetchall()]

    def export_json(
        self,
        range_str: Optional[str] = None,
    ) -> str:
        """Export sessions as JSON.

        Args:
            range_str: Optional time range filter.

        Returns:
            JSON string with metadata and sessions.
        """
        sessions = self.get_sessions(range_str)

        # Build range metadata
        if range_str:
            try:
                time_range = parse_range(range_str)
                range_meta = {
                    "start_date": time_range.start_date,
                    "end_date": time_range.end_date,
                    "days": time_range.days,
                }
            except InvalidRangeError:
                raise
        else:
            range_meta = {
                "start_date": None,
                "end_date": None,
                "days": None,
            }

        export_data = {
            "format": "vscode-time-export",
            "version": EXPORT_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "range": range_meta,
            "sessions": sessions,
        }

        return json.dumps(export_data, indent=2)

    def export_csv(
        self,
        range_str: Optional[str] = None,
    ) -> str:
        """Export sessions as CSV.

        Args:
            range_str: Optional time range filter.

        Returns:
            CSV string with header and session rows.
        """
        sessions = self.get_sessions(range_str)

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=CSV_COLUMNS,
            extrasaction='ignore',
        )

        writer.writeheader()
        for session in sessions:
            writer.writerow(session)

        return output.getvalue()

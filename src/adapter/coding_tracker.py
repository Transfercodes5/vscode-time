"""Adapter for hangxingliu.vscode-coding-tracker database files.

This module reads the extension's plain-text .db files and normalizes
records into Session objects. It filters for type-2 (coding/editing)
records only, as established by Phase 2.5 duration semantics verification.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple, Dict


CODING_TRACKER_DIR = Path.home() / ".coding-tracker"
DB_EXTENSION = ".db"

# Supported storage format versions
SUPPORTED_VERSIONS = {"4.0", "3.0"}

# Record fields in storage format v4.0
RECORD_FIELDS = 12

# Only import type-2 (coding/editing) records
IMPORT_RECORD_TYPES = {2}


class CodingTrackerError(Exception):
    """Base error for adapter."""
    pass


class UnsupportedFormatError(CodingTrackerError):
    """Raised when the storage format version is unsupported."""
    pass


class Session:
    """Normalized coding session from the extension's database."""

    __slots__ = (
        "session_type",
        "start_time",
        "duration_seconds",
        "language",
        "file",
        "project",
        "vcs",
        "line_count",
        "char_count",
        "record_id",
        "source_file",
    )

    def __init__(
        self,
        session_type: int,
        start_time: int,
        duration_seconds: int,
        language: str,
        file: str,
        project: str,
        vcs: str,
        line_count: int,
        char_count: int,
        record_id: str,
        source_file: str = "",
    ):
        self.session_type = session_type
        self.start_time = start_time
        self.duration_seconds = duration_seconds
        self.language = language
        self.file = file
        self.project = project
        self.vcs = vcs
        self.line_count = line_count
        self.char_count = char_count
        self.record_id = record_id
        self.source_file = source_file

    def __repr__(self):
        return (
            f"Session(type={self.session_type}, start={self.start_time}, "
            f"dur={self.duration_seconds}s, lang={self.language}, "
            f"file={self.file}, proj={self.project})"
        )

    def start_datetime(self) -> datetime:
        """Convert epoch ms to UTC datetime."""
        return datetime.fromtimestamp(self.start_time / 1000.0, tz=timezone.utc)


def compute_record_id(
    source: str,
    session_type: int,
    start_time: int,
    duration_seconds: int,
    language: str,
    file: str,
    project: str,
    vcs: str,
    line_count: int,
    char_count: int,
) -> str:
    """Deterministic hash based on stable source record fields.

    Uses SHA-256 truncated to 16 hex characters for stability.
    The hash includes all fields that define a unique source record.
    """
    # Canonical representation: sorted fields for consistency
    canonical = (
        f"{source}|"
        f"{session_type}|"
        f"{start_time}|"
        f"{duration_seconds}|"
        f"{language}|"
        f"{file}|"
        f"{project}|"
        f"{vcs}|"
        f"{line_count}|"
        f"{char_count}"
    )
    h = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"ct-{h}"


def _detect_version(lines: List[str]) -> Tuple[Optional[str], bool]:
    """Detect and validate the storage format version.

    Returns:
        (version_string, is_supported)
    """
    for line in lines:
        stripped = line.strip()
        if stripped == "4.0":
            return stripped, True
        if stripped == "3.0":
            return stripped, True
        # Check if this looks like a version header but is unsupported
        parts = stripped.split()
        if len(parts) == 1 and "." in stripped:
            return stripped, False
    return None, True  # No version header; treat as supported


def parse_record_line(line: str) -> Optional[Tuple[int, int, int, str, str, str, str, int, int]]:
    """Parse a single record line.

    Returns:
        (type, time, long_ms, lang, file, proj, pcid, vcs, line, char)
        where long_ms is duration in milliseconds.
        or None if malformed.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # Skip version headers
    if line in ("4.0", "3.0"):
        return None

    parts = line.split()
    if len(parts) < RECORD_FIELDS:
        return None

    try:
        record_type = int(parts[0])
    except ValueError:
        return None

    if record_type not in (0, 1, 2):
        return None

    try:
        timestamp = int(parts[1])
    except ValueError:
        return None

    try:
        duration = int(parts[2])
    except ValueError:
        return None

    if duration < 0:
        return None

    language = parts[3]
    file = parts[4]
    project = parts[5]
    vcs = parts[7]

    try:
        line_count = int(parts[8])
    except ValueError:
        line_count = 0

    try:
        char_count = int(parts[9])
    except ValueError:
        char_count = 0

    return (record_type, timestamp, duration, language, file, project, vcs, line_count, char_count)


def discover_db_files(directory: Path = CODING_TRACKER_DIR) -> List[Path]:
    """Discover all .db files in the coding-tracker data directory."""
    if not directory.exists():
        return []
    return sorted(
        entry for entry in directory.iterdir()
        if entry.is_file() and entry.suffix == DB_EXTENSION
    )


def parse_db_file(filepath: Path) -> Tuple[List[Session], int, int]:
    """Parse a single .db file and return normalized sessions.

    Returns:
        (sessions, valid_count, rejected_count)
    """
    sessions = []
    valid_count = 0
    rejected_count = 0

    lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return [], 0, 0

    # Validate version header
    version, is_supported = _detect_version(lines)
    if version is not None and not is_supported:
        raise UnsupportedFormatError(
            f"Unsupported storage format version: {version}. "
            "This adapter supports versions 4.0 and 3.0 only."
        )

    for line in lines:
        parsed = parse_record_line(line)
        if parsed is None:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and stripped not in ("4.0", "3.0"):
                rejected_count += 1
            continue

        rec_type, timestamp, duration_ms, language, file, project, vcs, line_count, char_count = parsed

        # Source 'long' field is in milliseconds; convert to seconds for storage.
        duration_seconds = duration_ms // 1000

        record_id = compute_record_id(
            source="vscode-coding-tracker",
            session_type=rec_type,
            start_time=timestamp,
            duration_seconds=duration_seconds,
            language=language,
            file=file,
            project=project,
            vcs=vcs,
            line_count=line_count,
            char_count=char_count,
        )

        session = Session(
            session_type=rec_type,
            start_time=timestamp,
            duration_seconds=duration_seconds,
            language=language,
            file=file,
            project=project,
            vcs=vcs,
            line_count=line_count,
            char_count=char_count,
            record_id=record_id,
            source_file=str(filepath.name),
        )
        sessions.append(session)
        valid_count += 1

    return sessions, valid_count, rejected_count


def filter_coding_sessions(sessions: List[Session]) -> List[Session]:
    """Filter to only type-2 (coding/editing) records.

    Phase 2.5 established that only type-2 records represent actual
    coding activity. Type-0 records are watching/open time.
    """
    return [s for s in sessions if s.session_type in IMPORT_RECORD_TYPES]


class CodingTrackerAdapter:
    """Adapter for reading hangxingliu.vscode-coding-tracker data."""

    def __init__(self, source_dir: Path = CODING_TRACKER_DIR):
        self.source_dir = source_dir

    def get_files(self) -> List[Path]:
        """Discover all .db files in the source directory."""
        return discover_db_files(self.source_dir)

    def get_sessions(self, filter_coding: bool = True) -> List[Session]:
        """Get all sessions from all source files.

        Args:
            filter_coding: If True, only return type-2 coding records.
        """
        all_sessions = []
        for db_file in self.get_files():
            sessions, _, _ = parse_db_file(db_file)
            all_sessions.extend(sessions)

        if filter_coding:
            return filter_coding_sessions(all_sessions)
        return all_sessions

    def get_daily_totals(self, sessions: List[Session]) -> Dict[str, int]:
        """Calculate total coding seconds per calendar day (UTC).

        Note: The source 'long' field is a cumulative accumulator, not an
        elapsed interval. We attribute the full duration to the start date.
        """
        daily: Dict[str, int] = {}
        for session in sessions:
            date_str = session.start_datetime().strftime("%Y-%m-%d")
            daily[date_str] = daily.get(date_str, 0) + session.duration_seconds
        return daily

    def get_project_totals(self, sessions: List[Session]) -> Dict[str, int]:
        """Calculate total coding seconds per project."""
        project_totals: Dict[str, int] = {}
        for session in sessions:
            proj = session.project if session.project else "(no project)"
            project_totals[proj] = project_totals.get(proj, 0) + session.duration_seconds
        return project_totals
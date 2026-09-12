# Changelog

## v1.0.0

Initial release of vscode-time.

### Features

- **Source adapter** for `hangxingliu.vscode-coding-tracker` v4.0 and v3.0
- **Persistent storage** with SQLite (schema v1)
- **Incremental synchronization** with duplicate protection
- **Daily goals** with progress tracking and validation
- **Daily history** with configurable date ranges
- **Streak tracking** (current and longest streaks)
- **Statistics** (totals, averages, projects, languages)
- **Reports** for today, yesterday, 7d, and 30d ranges
- **Status** with human-readable and JSON output
- **JSON/CSV export** with range filtering
- **Waybar integration** with CSS class support
- **TOML configuration** with atomic writes
- **Installation/uninstallation** scripts
- **CLI** with --help, --version, and error handling

### Data Quality

- Deterministic source IDs (SHA-256 truncated)
- Unique record constraint with batch transactions
- Local timezone handling for date aggregation
- Month/year boundary handling
- Time semantics: accumulated activity, not wall-clock time
- Source files never modified

### Testing

- 200 tests across 8 test suites
- Coverage: adapter, storage, sync, goals, streaks, statistics, reports, export, configuration, CLI, Waybar, installation, correctness hardening

### Documentation

- User guide with complete usage documentation
- README with quick start
- Waybar integration guide
- CLI reference

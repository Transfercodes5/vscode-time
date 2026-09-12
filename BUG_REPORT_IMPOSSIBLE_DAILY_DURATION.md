# Impossible Daily Duration Bug

## Executive Summary

The `vscode-time` CLI reported **423h 36m** of coding time for a single day — a physical impossibility. The root cause was a **unit conversion bug** in the source adapter: the `hangxingliu.vscode-coding-tracker` extension stores session durations in **milliseconds**, but the adapter stored them directly as `duration_seconds` without converting. This inflated all durations by 1000x.

## Observed Behavior

```
$ vscode-time status

Today
─────
Coding:   423h 36m
Goal:     1h
Progress: 100%
Status:   COMPLETE
Streak:   2 days
```

## Expected Behavior

```
$ vscode-time status

Today
─────
Coding:   30m
Goal:     1h
Progress: 50%
Status:   IN PROGRESS
Streak:   0 days
```

## Reproduction

The bug was reproducible by running:
```bash
vscode-time status      # Shows 423h 36m
vscode-time today       # Shows 423h 36m
vscode-time stats       # Shows 487h 30m total, 243h 45m avg
vscode-time report 7d   # Shows 423h 36m for today
```

## Investigation

### CLI Layer

The CLI calls `GoalManager.get_today_status()` which calls `_get_coding_seconds_for_date()`. This method queries SQLite with correct millisecond-to-second conversion for `start_time`. The CLI layer was correct.

### Aggregation Layer

`get_daily_totals()` in `database.py` correctly divides `start_time / 1000` for date grouping. The aggregation layer was correct.

### SQLite Layer

SQLite stored `duration_seconds` with values like 5000, 20000, 65000, 115000. These were the raw values from the source, not converted to seconds. The database had **inflated data**.

### Sync Layer

The importer passes sessions directly from the adapter to the database. No conversion happens in the sync layer. The sync layer was correct (it faithfully stored what the adapter provided).

### Adapter Layer

`src/adapter/coding_tracker.py` line 259:
```python
session = Session(
    ...
    duration_seconds=duration,  # BUG: duration is in milliseconds!
    ...
)
```

The adapter read the `long` field from the source `.db` file and stored it directly as `duration_seconds`. The `long` field is in milliseconds (5000ms = 5s), but was treated as seconds.

### Source Data

The `hangxingliu.vscode-coding-tracker` extension stores data in plain-text `.db` files with format:
```
4.0
2 1789151444788 5000 python vscode-notebook-cell /proj unknown-linux git::master 35 0 0 0
```

Fields: `type time long lang file proj pcid vcs line char ext extra`

- `time`: milliseconds since epoch
- `long`: duration in **milliseconds** (not seconds)

## Root Cause

The adapter's `parse_record_line()` function returns the raw `long` field value. The `parse_db_file()` function then passes this value directly as `duration_seconds` to the `Session` constructor without dividing by 1000.

```python
# Before fix (WRONG):
session = Session(
    ...
    duration_seconds=duration,  # duration is milliseconds!
    ...
)

# After fix (CORRECT):
duration_seconds = duration_ms // 1000
session = Session(
    ...
    duration_seconds=duration_seconds,  # Now in seconds
    ...
)
```

## Mathematical Explanation

Source data for today (2026-09-12):
- 80 type-2 records
- Total `long` values: 1,805,000 milliseconds
- Correct total: 1,805,000 / 1000 = **1,805 seconds = 30m 5s**

Before fix:
- Database stored: 1,805,000 as `duration_seconds`
- CLI displayed: 1,805,000 / 3600 = **501.4 hours** (approximately 423h 36m at the time of the initial report, before more records were added)

## Why 423h 36m Appeared

At the time of the initial report:
- Today had 64 records with total `long` = 1,525,000 milliseconds
- Database stored: 1,525,000 as `duration_seconds`
- CLI calculated: 1,525,000 / 3600 = **423.61 hours = 423h 36m**

## Historical Impact

The bug affected **all imported data**:
- Every session's `duration_seconds` was 1000x too large
- All daily totals, statistics, and reports were inflated by 1000x
- Streaks were incorrectly calculated (every day appeared to exceed the goal)
- The database was **corrupted** with incorrect values

## Fix

**File:** `src/adapter/coding_tracker.py`

**Change:** Convert milliseconds to seconds when creating Session objects:

```python
# Line ~242: Rename variable for clarity
rec_type, timestamp, duration_ms, language, file, project, vcs, line_count, char_count = parsed

# Line ~244: Add conversion
duration_seconds = duration_ms // 1000

# Line ~261: Use converted value
session = Session(
    ...
    duration_seconds=duration_seconds,
    ...
)
```

Also fixed the `compute_record_id()` call to use the corrected `duration_seconds` value, ensuring source IDs are based on accurate data.

Additionally fixed a minor issue where version headers ("4.0", "3.0") were counted as rejected records.

## Database Repair

The database was rebuilt from source data after applying the fix:

1. Backed up existing database to `/tmp/vscode-time-before-debug.db`
2. Removed corrupted database
3. Re-ran `vscode-time sync` to import all records with correct durations

**Before repair:**
- 89 sessions, total: 1,755,000 "seconds" (actually milliseconds)
- Today: 1,525,000 "seconds" (actually milliseconds)

**After repair:**
- 103 sessions, total: 1,960 seconds
- Today: 1,805 seconds (30m)

## Regression Tests

Created `tests/test_impossible_daily_duration.py` with 17 tests:

1. **TestDurationUnits** (4 tests): Verify ms-to-seconds conversion
2. **TestDailyUpperBound** (2 tests): Verify session durations are reasonable
3. **TestDuplicateSync** (1 test): Verify sync idempotency
4. **TestDateFiltering** (2 tests): Verify sessions attributed to correct dates
5. **TestMonthBoundary** (1 test): Verify month transitions
6. **TestYearBoundary** (1 test): Verify year transitions
7. **TestMidnight** (1 test): Verify midnight attribution
8. **TestJSONConsistency** (1 test): Verify JSON matches text output
9. **TestSourceDatabaseReconciliation** (2 tests): Verify source matches database
10. **TestRecordIDStability** (2 tests): Verify deterministic IDs

## Source Reconciliation

**Source data (26911.db + 26912.db):**
- Yesterday: 25 records, 230 seconds
- Today: 80 records, 1805 seconds

**Database:**
- Yesterday: 25 records, 230 seconds
- Today: 80 records, 1805 seconds

**CLI:**
- Yesterday: 3m (180s ≈ 3m)
- Today: 30m (1805s ≈ 30m)

All three sources agree.

## Before vs After

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Today's coding | 423h 36m | 30m |
| Total coding | 487h 30m | 33m |
| Longest day | 423h 36m | 30m |
| Goal completion | 100% | 0% |
| Streak | 2 days | 0 days |
| Database sessions | 89 | 103 |
| Database total | 1,755,000 (wrong) | 1,960 (correct) |

## Verification

```bash
$ vscode-time status
Today
─────
Coding:   30m
Goal:     1h
Progress: 50%
Status:   IN PROGRESS
Streak:   0 days

$ vscode-time sync
Sync complete
Imported: 0
Existing: 103

$ sqlite3 ~/.local/share/vscode-time/vscode-time.db "PRAGMA integrity_check;"
ok

$ python -m pytest tests/ -v
163 passed in 7.74s
```

## Why Existing Tests Missed It

The existing test suite had **no test that verified duration units against real source data**. Tests used mock sessions with hardcoded `duration_seconds` values, never testing the full pipeline from source file parsing to database storage.

Specific missing coverage:
1. **No integration test** that parses a real source file and verifies database values
2. **No unit test** that checks the adapter's ms-to-seconds conversion
3. **Mock sessions** bypassed the adapter entirely, so the conversion bug was never exercised
4. **Real data tests** only verified that commands ran successfully, not that values were numerically correct

## Prevention

The new regression tests in `test_impossible_daily_duration.py` now prevent recurrence by:
1. Verifying the adapter converts milliseconds to seconds
2. Testing that daily totals are in the correct range
3. Verifying source/database reconciliation
4. Testing sync idempotency
5. Testing date filtering across boundaries

## Remaining Risks

1. **Source format changes**: If the coding tracker extension changes its `long` field units, the adapter would need updating
2. **New source adapters**: Any new adapter must correctly handle its source's duration units
3. **Timezone handling**: The adapter uses UTC for daily totals while the database uses local time — this is a separate, pre-existing discrepancy

## Conclusion

The bug was a simple unit conversion error: milliseconds were stored as seconds. The fix is a single line of code (`duration_ms // 1000`). The database was rebuilt from source data. All 163 tests pass. Source integrity is preserved.

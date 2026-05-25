# PostgreSQL Backup Restore Verification Report

This report documents the verification process for the PostgreSQL database backups of the `microSchedule v2` application.

## Summary

On 2026-05-25, the Tier 2 verification agent performed a restoration test of the latest PostgreSQL backup. The backup file was restored to a temporary test database, and the record counts were compared against the primary active database to verify the integrity and completeness of the backup data.

## Backup File Tested

- **Path**: `C:\Users\os\Desktop\Tools\VC_microSchedule_home_v2\backups\backup_20260525_163742.dump`
- **Size**: 70,206 bytes
- **Backup Timestamp**: 2026-05-25 16:37:42

## Commands Run

The following sequence of commands was executed:

1. **Verify if temporary database already exists**:
   ```sql
   SELECT datname FROM pg_database WHERE datname = 'microschedule_v2_restore_test';
   ```
2. **Create the temporary database**:
   ```powershell
   $env:PGPASSWORD="<password>"
   createdb -h localhost -p 5432 -U postgres microschedule_v2_restore_test
   ```
3. **Restore the dump file into the temporary database**:
   ```powershell
   $env:PGPASSWORD="<password>"
   pg_restore -h localhost -p 5432 -U postgres -d microschedule_v2_restore_test -v "C:\Users\os\Desktop\Tools\VC_microSchedule_home_v2\backups\backup_20260525_163742.dump"
   ```
4. **Compare row counts between databases**:
   Executed a database comparison script querying the tables in both `microschedule_v2` and `microschedule_v2_restore_test`.
5. **Drop the temporary database (Cleanup)**:
   ```powershell
   $env:PGPASSWORD="<password>"
   dropdb -h localhost -p 5432 -U postgres microschedule_v2_restore_test
   ```

## Count Comparison

Below is the record count comparison between the primary database and the restored temporary database:

| Table | Primary (`microschedule_v2`) | Restored (`microschedule_v2_restore_test`) | Match? | Note |
| :--- | :---: | :---: | :---: | :--- |
| `tasks` | 87 | 87 | **YES** | Matches migration counts and current state. |
| `task_items` | 55 | 55 | **YES** | Matches migration counts and current state. |
| `notes` | 29 | 29 | **YES** | Matches migration counts and current state. |
| `note_items` | 26 | 26 | **YES** | Matches migration counts and current state. |
| `calendar_sources` | 3 | 3 | **YES** | Matches migration counts and current state. |
| `calendar_source_versions` | 3 | 3 | **YES** | Matches migration counts and current state. |
| `calendar_events` | 442 | 442 | **YES** | Matches migration counts and current state. |
| `app_settings` | 8 | 8 | **YES** | Matches migration counts and current state. |
| `backup_runs` | 1 | 0 | *NO* | **Expected discrepancy**: The row in `backup_runs` is logged in the primary database *after* the `pg_dump` stream has successfully completed writing. Therefore, the backup stream itself did not contain this final entry. |

## Cleanup Result

The temporary database `microschedule_v2_restore_test` was successfully dropped after verification. No temporary databases or dangling resources remain on the local PostgreSQL server.

## Verdict

**PASS**

The PostgreSQL backup `.dump` file is structurally sound and can be restored cleanly. All user data (including tasks, task items, notes, note items, calendars, events, and application settings) was restored completely without errors or warnings.

## Risks/Follow-ups

- **Risks**: None. The pg_restore ran successfully and without error.
- **Follow-ups**: Ensure routine automated testing is put in place if database schemas undergo migrations or structural changes in future releases.

# WS0/WS1 Contract - microSchedule v2

Ngay khoa: 2026-05-25
Pham vi: WS0 Architecture contract va WS1 PostgreSQL schema + migration.
Nguon quyet dinh: `docs/V2_DECISION_BRIEF.md`.

## 1. Muc Tieu

WS0 khoa cac contract chung de cac workstream sau khong tu y doi schema/API. WS1 implement schema PostgreSQL moi va migration one-shot tu SQLite v1 sang PostgreSQL v2.

Khong sua, xoa, reset, hay migrate in-place SQLite v1 tai:

```text
C:\Users\os\Desktop\Tools\VC_microSchedule_home\todo.db
```

## 2. Quyet Dinh Da Khoa

- Database v2 la PostgreSQL database `microschedule_v2`.
- Schema v2 la schema moi, khong port nguyen SQLite v1.
- Migration SQLite v1 chi doc read-only va ghi PostgreSQL trong transaction.
- Incomplete overdue tasks migrate thanh `notes`; subtasks cua chung migrate thanh `note_items`.
- Khong luu `source_task_id` trong `notes` va khong mark migrated trong DB v2.
- Existing SQLite `schedule` migrate thanh mot calendar source rieng ten `v1_sqlite_schedule`.
- Moi calendar event v2 bat buoc thuoc `source_id` va `source_version_id`.
- Main calendar chi doc events thuoc active version: `calendar_sources.current_version_id = calendar_events.source_version_id`.
- Import/update source tao source version moi; khong ghi de event cua version cu.
- AI write/admin tools ve sau bat buoc co dry-run, confirm, audit log, va backup/checkpoint cho thao tac rui ro.

## 3. Schema Contract

Tier 2 WS1 duoc them cot ky thuat neu can cho PostgreSQL an toan hon, nhung khong duoc doi y nghia bang/cot duoi day neu khong viet proposal.

### Calendar

`calendar_sources`

- `id uuid primary key`
- `display_name text not null unique`
- `kind text not null`
- `academic_year integer null`
- `term text null`
- `sort_start_date date null`
- `color text not null`
- `is_visible boolean not null default true`
- `current_version_id uuid null`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

`kind` allowed values for phase 1/2:

- `study_schedule`
- `exam_schedule`
- `manual_task_calendar`
- `holiday`
- `other`
- `legacy_v1`

`calendar_source_versions`

- `id uuid primary key`
- `source_id uuid not null references calendar_sources(id)`
- `version_number integer not null`
- `file_name text null`
- `file_sha256 text null`
- `imported_at timestamptz not null default now()`
- `parser_version text not null`
- `status text not null`
- `summary_json jsonb not null default '{}'::jsonb`

Required constraints/indexes:

- unique `(source_id, version_number)`
- unique `(source_id, file_sha256)` where `file_sha256 is not null`
- `status` values: `active`, `duplicate_noop`, `failed`, `superseded`

`calendar_events`

- `id uuid primary key`
- `source_id uuid not null references calendar_sources(id)`
- `source_version_id uuid not null references calendar_source_versions(id)`
- `external_uid text null`
- `content_hash text not null`
- `title text not null`
- `description text null`
- `starts_at timestamptz not null`
- `ends_at timestamptz not null`
- `location text null`
- `event_type text not null`
- `status text not null default 'active'`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

Required constraints/indexes:

- unique `(source_version_id, external_uid)` where `external_uid is not null`
- index `(source_id, source_version_id)`
- index `(starts_at, ends_at)`
- `event_type` values: `class`, `exam`, `manual`, `holiday`, `other`, `legacy`
- `status` values: `active`, `cancelled`, `tentative`
- `ends_at > starts_at`

### Tasks And Notes

`priorities`

- `id uuid primary key`
- `name text not null unique`
- `label text not null`
- `color text not null`
- `icon text null`
- `sort_order integer not null`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

`tasks`

- `id uuid primary key`
- `title text not null`
- `note text null`
- `priority_id uuid null references priorities(id)`
- `due_at timestamptz null`
- `status text not null`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`
- `completed_at timestamptz null`

`status` values: `open`, `completed`, `archived`.

`task_items`

- `id uuid primary key`
- `task_id uuid not null references tasks(id) on delete cascade`
- `content text not null`
- `is_completed boolean not null default false`
- `position integer not null default 0`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

`notes`

- `id uuid primary key`
- `title text not null`
- `body text null`
- `priority_id uuid null references priorities(id)`
- `pinned boolean not null default false`
- `archived_at timestamptz null`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

`note_items`

- `id uuid primary key`
- `note_id uuid not null references notes(id) on delete cascade`
- `content text not null`
- `is_done boolean not null default false`
- `position integer not null default 0`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

### System Tables

`app_settings`

- `key text primary key`
- `value_json jsonb not null`
- `updated_at timestamptz not null default now()`

`backup_runs`

- `id uuid primary key`
- `kind text not null`
- `status text not null`
- `artifact_path text null`
- `started_at timestamptz not null default now()`
- `finished_at timestamptz null`
- `message text null`

`agent_action_log`

- `id uuid primary key`
- `actor text not null`
- `action_type text not null`
- `tool_name text not null`
- `permission_scope text not null`
- `status text not null`
- `target_summary_json jsonb not null default '{}'::jsonb`
- `before_json jsonb null`
- `after_json jsonb null`
- `rollback_json jsonb null`
- `created_at timestamptz not null default now()`

## 4. Repository/Service Boundary

WS1 chi can tao DB/config/migration. Neu tao repository skeleton, chi tao cac ham doc/ghi can cho migration va de workstream sau dung contract:

- `app/config.py`: load `.env`, return config object, never print secrets.
- `app/db/postgres.py`: connect PostgreSQL, transaction helper, schema apply helper.
- `app/db/schema.sql`: authoritative v2 DDL.
- `app/migration/analyze_v1_sqlite.py`: read-only analyzer.
- `app/migration/migrate_sqlite_to_postgres.py`: dry-run/apply migration CLI.

Khong sua `main.py` va `database.py` trong WS1 tru khi Tier 1 giao rieng integration task. V1 app phai tiep tuc chay tren SQLite cho den khi co integration phase.

## 5. Migration Contract

Input SQLite v1:

- `tasks`: 116 rows hien tai
- `subtasks`: 81 rows hien tai
- `schedule`: 295 rows hien tai
- `settings`: 4 rows hien tai
- incomplete overdue tasks tai ngay 2026-05-25: 29 rows

Rules:

- Analyzer khong ghi PostgreSQL.
- Migration apply chay trong mot transaction; loi thi rollback toan bo.
- SQLite open read-only bang URI `mode=ro`.
- Target default phai la `microschedule_v2`.
- `--reset-dev-db` chi duoc drop/truncate khi target DB name dung bang `microschedule_v2`.
- Neu target khac `microschedule_v2`, fail fast tru khi co flag `--allow-non-dev-target`.
- Khong log password, API key, full `.env`, hoac connection string co secret.
- Migration report phai ghi count truoc/sau, danh sach 29 task convert thanh notes, rows skipped, schema timestamp.

Mapping:

- Completed v1 tasks -> `tasks.status = 'completed'`, `completed_at` set theo migration time neu v1 khong co timestamp.
- Incomplete overdue v1 tasks -> `notes`, note title from task title, body from task note.
- Subtasks cua task -> `task_items` hoac `note_items` theo parent da migrate vao task/note.
- Future/incomplete non-overdue v1 tasks -> `tasks.status = 'open'`.
- v1 schedule -> source `v1_sqlite_schedule`, kind `legacy_v1`, version 1, events `event_type = 'legacy'`.
- v1 settings -> `app_settings.value_json`.
- Priorities seed tu settings neu parse duoc; neu khong parse duoc, seed defaults tu v1 decision docs va report warning.

## 6. WS1 Task Breakdown

1. Branch/setup
   - Check `git status --short --branch`.
   - Create/switch `feat/v2-postgres-migration` from `develop` only if user permits implementation.

2. Config and DB base
   - Add `python-dotenv` and `psycopg[binary]` if used.
   - Implement `.env` loading without printing secrets.
   - Validate target DB name safety.

3. Schema
   - Create `app/db/schema.sql`.
   - Include all tables and constraints above.
   - Make schema application idempotent for dev.

4. Analyzer
   - Read SQLite v1 read-only.
   - Produce counts and note-conversion candidates.
   - Write/refresh `docs/V2_MIGRATION_REPORT.md` in dry-run format.

5. Migration
   - Implement dry-run and apply modes.
   - Use transaction.
   - Implement reset safety guard.
   - Seed priorities/settings/source/version/events/tasks/notes/items.

6. Verification/report
   - Run analyzer.
   - Run dry-run.
   - Run apply only after user/Tier 1 approval if real DB mutation is in scope.
   - Report counts, commands, risks, and any schema proposal needed.

## 7. Acceptance Criteria

- V1 SQLite file is unchanged.
- `app/db/schema.sql` creates all required v2 tables.
- Analyzer can run without PostgreSQL writes.
- Dry-run shows deterministic migration plan and note-conversion list.
- Apply mode writes PostgreSQL in one transaction.
- Re-run with `--reset-dev-db` works only for `microschedule_v2`.
- Existing v1 schedule rows are under `v1_sqlite_schedule` source/version.
- Notes are separate from tasks; overdue note-like tasks no longer appear as tasks in v2 data.
- No secret appears in code, docs, logs, report, or test output.

## 8. Verification Plan

Minimum commands for Tier 2 report:

```powershell
git status --short --branch
.\venv\Scripts\python.exe app\migration\analyze_v1_sqlite.py
.\venv\Scripts\python.exe app\migration\migrate_sqlite_to_postgres.py --dry-run
.\venv\Scripts\python.exe app\migration\migrate_sqlite_to_postgres.py --apply
```

Recommended DB checks after apply:

```sql
select count(*) from tasks;
select count(*) from notes;
select count(*) from calendar_sources;
select count(*) from calendar_source_versions;
select count(*) from calendar_events;
select display_name, current_version_id from calendar_sources;
```

If tests are added:

```powershell
.\venv\Scripts\python.exe -m pytest
```

## 9. Risks And Open Questions

- Current repo docs `README.md`, `docs/SYSTEM_ARCHITECTURE.md`, and `docs/DATABASE_SCHEMA.md` describe v1 SQLite. They are valid v1 references, not v2 contract sources.
- Current local `develop` is ahead of `origin/develop` by 3 commits and another branch name points at the same commit. Tier 2 should not assume remote has these docs until branch coordination is resolved.
- `due_at` conversion from v1 `date_str` has no timezone/time-of-day in source data. Default should be local date at start of day or a documented app convention; Tier 2 must report the chosen convention.
- v1 has no created/updated timestamps. Migration-generated timestamps are acceptable but must be reported.
- Applying migration mutates PostgreSQL v2. Run apply only when the user/Tier 1 confirms the target DB can be reset or populated.

# Tier 2 Handoff - microSchedule v2 Implementation Plan

Vai trò: tài liệu giao việc cho model Tier 2, ưu tiên Gemini Flash 3.5.  
Nguyên tắc: Tier 2 chỉ implement theo quyết định đã duyệt trong `docs/V2_DECISION_BRIEF.md`. Nếu gặp conflict, dừng và report.

## Required Reading

Tier 2 phải đọc theo thứ tự:

1. `docs/V2_DECISION_BRIEF.md`
2. `agent_workflow_doc/KINH_NGHIEM.md`
3. `agent_workflow_doc/GIT_WORKFLOW_GUIDE.md`
4. `README.md`
5. `docs/SYSTEM_ARCHITECTURE.md`
6. `docs/DATABASE_SCHEMA.md`
7. `database.py`
8. `main.py`

Nếu đọc file tiếng Việt bằng PowerShell, dùng:

```powershell
Get-Content -Raw -Encoding UTF8 <path>
```

## Global Constraints

Không được:

- Sửa/xóa SQLite v1 tại `C:\Users\os\Desktop\Tools\VC_microSchedule_home\todo.db`.
- Hardcode secret vào code, docs, test.
- Commit `.env`.
- Import schedule kiểu insert mù không tracking source/import batch.
- Cho AI agent ghi DB nếu chưa có user confirmation.
- Rewrite full web/backend nếu task chỉ yêu cầu phase incremental.

Phải:

- Làm trên nhánh feature từ `develop`.
- Giữ main như app v1 tạm thời.
- Viết report sau mỗi phase: changed files, migration counts, tests run, known risks.
- Dùng `.env`/`.env.example` cho config.
- Tạo backup/dry-run trước migration thật.

## Current Local Facts

- Current branch base: `develop`.
- PostgreSQL local có sẵn.
- Database rỗng đã tạo: `microschedule_v2`.
- SQLite v1 data:
  - tasks: 116
  - subtasks: 81
  - schedule: 295
  - settings: 4
  - incomplete overdue tasks: 29
- New calendar files in repo root:
  - `TKB-QLDT20252.ics`: 139 VEVENT
  - `LichThi-QLDT-20252.ics`: 8 VEVENT
  - `LichThi.xlsx`: 8 rows, but some date cells read ambiguously by openpyxl

## Phase 1 Task - PostgreSQL Schema + Migration Dry Run

### Goal

Create v2 schema and migration tooling without destroying v1.

### Suggested Branch

`feat/v2-postgres-migration`

### Files To Create

- `app/__init__.py`
- `app/config.py`
- `app/db/__init__.py`
- `app/db/postgres.py`
- `app/db/schema.sql`
- `app/migration/__init__.py`
- `app/migration/migrate_sqlite_to_postgres.py`
- `app/migration/analyze_v1_sqlite.py`
- `docs/V2_MIGRATION_REPORT.md`

### Files To Modify

- `requirements.txt`
- Possibly `README.md` with v2 setup note only

### Required Dependencies

Add only if used:

```text
python-dotenv
psycopg[binary]
```

### Schema Required

Implement at minimum:

```sql
calendar_sources
import_batches
calendar_events
priorities
tasks
task_items
notes
note_items
app_settings
backup_runs
```

Use:

- `timestamptz` for timestamps.
- `text` for flexible text.
- `jsonb` for settings/summary payloads.
- FK constraints with `ON DELETE CASCADE` only for child rows like task_items/note_items.
- Unique indexes:
  - `calendar_sources(name)`
  - `calendar_events(source_id, external_uid, superseded_by_batch_id)` where usable
  - `app_settings(key)`

### Migration Rules

Read SQLite v1 read-only.

Tasks:

- If `is_completed = 0 AND date_str < current_date`, migrate to `notes`.
- Subtasks of migrated notes become `note_items`.
- Completed tasks migrate to `tasks` with `status='completed'`.
- Future/incomplete non-overdue tasks migrate to `tasks` with `status='open'`.
- Preserve original id in `legacy_sqlite_id` column or `metadata` JSON if the schema uses metadata.

Schedule:

- Existing SQLite `schedule` rows migrate into a source named `v1_sqlite_schedule`.
- New ICS imports are not part of SQLite migration unless the task explicitly includes import.

Settings:

- Migrate existing settings to `app_settings`.
- Seed priorities from existing settings if present.

### Dry Run Output

`docs/V2_MIGRATION_REPORT.md` must include:

- Source SQLite path.
- Target PostgreSQL database name only, not password.
- Count before/after.
- List of tasks converted to notes: id, title, old date.
- Any rows skipped and why.
- SQL/schema version timestamp.

### Acceptance Criteria

- Running analyzer does not write to PostgreSQL.
- Running migration writes to PostgreSQL in one transaction.
- Re-running migration with `--reset-dev-db` works only for `microschedule_v2`, never any other DB.
- Migration fails fast if target DB is not `microschedule_v2` unless `--allow-non-dev-target` is explicitly passed.
- No `.env` content printed in logs.

### Suggested Commands

```powershell
.\venv\Scripts\python.exe app\migration\analyze_v1_sqlite.py
.\venv\Scripts\python.exe app\migration\migrate_sqlite_to_postgres.py --dry-run
.\venv\Scripts\python.exe app\migration\migrate_sqlite_to_postgres.py --apply
```

## Phase 2 Task - Import Versioning

### Goal

Implement ICS/Excel import into v2 calendar schema with source and batch tracking.

### Suggested Branch

`feat/v2-import-versioning`

### Files To Create

- `app/importers/__init__.py`
- `app/importers/ics_importer.py`
- `app/importers/excel_exam_importer.py`
- `app/services/calendar_import_service.py`
- `tests/test_calendar_import_service.py`

### Required Behavior

ICS:

- Parse folded lines.
- Preserve UID, SUMMARY, DESCRIPTION, LOCATION, DTSTART, DTEND, DTSTAMP if present.
- Compute `content_hash` from normalized title, description, start/end, location, event_type.
- Source type:
  - `study_schedule` for `TKB-QLDT20252.ics`
  - `exam_schedule` for `LichThi-QLDT-20252.ics`

Excel:

- Treat as fallback source.
- Detect header.
- Prefer string dates `dd/mm/yyyy`.
- If openpyxl returns datetime with suspicious `mm-dd-yy` format, write warning in import summary.
- Do not silently override ICS exam events.

Versioning:

- Same file checksum imported again creates an import batch with status `duplicate` or skips with clear message.
- Same UID + same hash: no new event.
- Same UID + changed hash: old event gets `superseded_by_batch_id`, new event inserted.
- Old active UID missing from latest batch: mark as `missing_in_latest`, not hard delete.

### Acceptance Criteria

- Import `TKB-QLDT20252.ics` creates 139 active events.
- Import `LichThi-QLDT-20252.ics` creates 8 active exam events.
- Re-importing same file does not duplicate active events.
- Import summary includes added/changed/unchanged/missing counts.
- Unit tests cover unchanged and changed event cases.

## Phase 3 Task - Export Markdown/JSON

### Goal

Create canonical export DTO and render Markdown default, JSON optional.

### Suggested Branch

`feat/v2-export-markdown`

### Files To Create

- `app/exporters/__init__.py`
- `app/exporters/planner_dto.py`
- `app/exporters/markdown_exporter.py`
- `app/exporters/json_exporter.py`
- `app/services/export_service.py`
- `tests/test_export_service.py`

### Required Behavior

DTO contains:

- metadata
- calendar_events grouped by date/source
- tasks open/upcoming
- notes pinned/recent
- warnings/conflicts if detected

Markdown sections:

```markdown
# microSchedule Export

## Metadata
## Upcoming Schedule
## Open Tasks
## Notes
## Suggested AI Instructions
```

Settings:

- `export.default_format = markdown`
- `export.include_notes = true`
- `export.include_completed = false`

### Acceptance Criteria

- Markdown export is deterministic for same input.
- JSON export uses same DTO.
- Completed tasks excluded by default.
- Notes are included but not treated as overdue tasks.

## Phase 4 Task - UI Notes

### Goal

Add Notes tab and remove note-like data from task pressure.

### Suggested Branch

`feat/v2-notes-ui`

### Required UI

Notes tab:

- List notes sorted by pinned, updated_at desc.
- Quick add note title.
- Detail/edit dialog with title, body, priority, note_items.
- Archive note.
- Toggle note item done.

Constraints:

- Notes have no required due date.
- Notes do not appear in Day View as overdue tasks.
- Priority is optional.

### Acceptance Criteria

- Migrated notes visible in Notes tab.
- Existing incomplete overdue v1 notes do not appear as tasks after v2 migration.
- CRUD works against PostgreSQL, not SQLite.

## Phase 5 Task - Continuous Calendar UI

### Goal

Replace fixed month grid with Outlook Classic style continuous scrolling multi-week calendar and left sidebar.

### Suggested Branch

`feat/v2-continuous-calendar`

### Required UI

Left sidebar:

- Mini month navigator.
- Previous/next month.
- Click date scrolls main calendar to week containing date.
- Highlight today.
- Highlight selected date/current visible week range.
- Calendar source checkboxes with source colors.

Main calendar:

- Scrollable list of full week rows.
- Weeks continue across month boundaries.
- Header updates based on visible range.
- Events colored by source.
- Filters show/hide event source.

Data:

- Query events by visible range with buffer.
- Do not query DB per day cell in tight loops if avoidable; prefetch by range.

### Acceptance Criteria

- Week row always has 7 days.
- No blank month-boundary cells.
- Toggling "Lịch học" hides/shows study events.
- Toggling "Lịch thi" hides/shows exam events.
- Today and selected date are visually distinct.

## Phase 6 Task - PostgreSQL Backup

### Goal

Implement v2 backup using `pg_dump`.

### Suggested Branch

`feat/v2-postgres-backup`

### Required Behavior

- Dump `microschedule_v2` using `pg_dump -Fc`.
- Write to temp file then atomic rename.
- Retention:
  - Keep 48 latest backups.
  - Keep 30 daily snapshots if implemented.
- Log each run in `backup_runs`.
- Provide restore command in docs.

### Acceptance Criteria

- Backup command succeeds locally.
- Restore to temp DB succeeds in test docs.
- App does not crash if backup fails; it shows/logs error.

## Phase 7 Task - AI Chat/RAG Read-only

### Goal

Add AI assistant foundation without DB write tools.

### Suggested Branch

`feat/v2-ai-chat-rag`

### Files To Create

- `app/ai/__init__.py`
- `app/ai/llm_client.py`
- `app/ai/model_registry.py`
- `app/ai/rag_service.py`
- `app/services/ai_chat_service.py`

### Required Behavior

- Read `NINE_ROUTER_URL` and key from `.env`.
- `/models` call should be optional and failure-tolerant.
- Chat works only when router is available.
- If router is unavailable, UI shows config/status error.
- RAG is read-only over notes/tasks/calendar.
- No create/update/delete tool in phase 7.

### Library Choice

Preferred:

- LiteLLM if it works cleanly with the OpenAI-compatible router.
- Otherwise minimal `httpx` OpenAI-compatible client.

Do not use LangGraph until agent/tool mutation phase.

### Acceptance Criteria

- Router off does not crash app.
- Provider config never logs secret.
- Chat response can cite note/task/event ids used as context.

## Reporting Template

Each Tier 2 task report must include:

```markdown
## Summary

## Changed Files

## Commands Run

## Verification Output

## Migration/DB Counts

## Known Risks

## Questions For Tier 1
```


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
9. `agent_workflow_doc/tier2_task_specs/V2_PARALLEL_EXECUTION_BOARD.md`

Nếu đọc file tiếng Việt bằng PowerShell, dùng:

```powershell
Get-Content -Raw -Encoding UTF8 <path>
```

## Global Constraints

Không được:

- Sửa/xóa SQLite v1 tại `C:\Users\os\Desktop\Tools\VC_microSchedule_home\todo.db`.
- Hardcode secret vào code, docs, test.
- Commit `.env`.
- Import schedule kiểu insert mù không tracking source/source version.
- Cho AI agent ghi DB nếu chưa có dry-run, user confirmation, audit log và backup/checkpoint khi thao tác rủi ro.
- Rewrite full web/backend nếu task chỉ yêu cầu phase incremental.

Phải:

- Làm trên nhánh feature từ `develop`.
- Giữ main như app v1 tạm thời.
- Viết report sau mỗi phase: changed files, migration counts, tests run, known risks.
- Dùng `.env`/`.env.example` cho config.
- Tạo backup/dry-run trước migration thật.

## Parallel Execution

Không bắt buộc một model làm hết. Khi chia cho nhiều Tier 2 chạy song song, dùng `V2_PARALLEL_EXECUTION_BOARD.md` làm nguồn điều phối chính:

- Mỗi model nhận đúng một workstream.
- Mỗi workstream có branch và file ownership riêng.
- Workstream có thể làm parser/formatter/backup độc lập trước, nhưng không tự đổi schema contract.
- Các phần cross-cutting như schema, migration, AI write tools và integration nên giao Codex/strong model ở chat riêng.

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
- v2 data/backup folder: `C:\Users\os\Desktop\Tools\VC_microSchedule_home_v2` and user has synced it with Google Drive.

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
calendar_source_versions
calendar_events
priorities
tasks
task_items
notes
note_items
app_settings
backup_runs
agent_action_log
```

Use:

- `timestamptz` for timestamps.
- `text` for flexible text.
- `jsonb` for settings/summary payloads.
- FK constraints with `ON DELETE CASCADE` only for child rows like task_items/note_items.
- Unique indexes:
  - `calendar_sources(display_name)`
  - `calendar_source_versions(source_id, version_number)`
  - `calendar_source_versions(source_id, file_sha256)`
  - `calendar_events(source_version_id, external_uid)` where UID exists
  - `app_settings(key)`

### Migration Rules

Read SQLite v1 read-only.

Tasks:

- If `is_completed = 0 AND date_str < current_date`, migrate to `notes`.
- Subtasks of migrated notes become `note_items`.
- Completed tasks migrate to `tasks` with `status='completed'`.
- Future/incomplete non-overdue tasks migrate to `tasks` with `status='open'`.
- Do not preserve `source_task_id` in `notes`; user explicitly does not need it.
- Do not mark original task as `migrated` in PostgreSQL.

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

## Phase 2 Task - Source-level Import Versioning

### Goal

Implement ICS/Excel import into v2 calendar schema with source and source-version tracking.

### Suggested Branch

`feat/v2-import-versioning`

### Files To Create

- `app/importers/__init__.py`
- `app/importers/ics_importer.py`
- `app/importers/excel_exam_importer.py`
- `app/services/calendar_source_service.py`
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

Source UI/service behavior:

- Existing sources are listed by `sort_start_date`, `academic_year`, `term`, then name. Example display names: "Lịch học 2025 kỳ 2", "Lịch thi 2025 kỳ 2".
- Each existing source has an "Update schedule" action.
- There is an "Import new schedule" action.
- Import new schedule requires user-provided `display_name` and `kind`.
- Source has color and visibility flag for calendar filters.

Versioning:

- Same file checksum imported again for the same source creates no duplicate active events and returns duplicate/no-op summary.
- Updating a source creates a new `calendar_source_versions` row and imports all parsed events into that version.
- After successful import, `calendar_sources.current_version_id` points to the new version.
- The main calendar only reads events whose `source_version_id = calendar_sources.current_version_id`.
- Old source versions and their events are kept for rollback/diff, not hard deleted.
- Do not implement event-level supersede unless Tier 1 explicitly changes the architecture.

### Acceptance Criteria

- Import `TKB-QLDT20252.ics` creates 139 active events.
- Import `LichThi-QLDT-20252.ics` creates 8 active exam events.
- Re-importing same file does not duplicate active events.
- Import summary includes source, version_number, parsed_count, active_count, duplicate/no-op status.
- Unit tests cover duplicate same-file import and update-source creates a new active version.

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
- Store backups under `C:\Users\os\Desktop\Tools\VC_microSchedule_home_v2\backups` by default, configurable via `.env`.
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

## Phase 7 Task - AI Agent/RAG/Internal Tools/MCP

### Goal

Add AI assistant foundation with RAG, internal tools, MCP boundary, permission gates, audit logs, and recoverable write workflows.

### Suggested Branch

`feat/v2-ai-agent-tools`

### Files To Create

- `app/ai/__init__.py`
- `app/ai/llm_client.py`
- `app/ai/model_registry.py`
- `app/ai/rag_service.py`
- `app/ai/tool_registry.py`
- `app/ai/permission_policy.py`
- `app/ai/agent_orchestrator.py`
- `app/services/audit_service.py`
- `app/services/ai_chat_service.py`

### Required Behavior

- Read `NINE_ROUTER_URL` and key from `.env`.
- `/models` call should be optional and failure-tolerant.
- Chat/agent works only when router is available.
- If router is unavailable, UI shows config/status error.
- RAG can read notes/tasks/calendar.
- Internal tools are grouped by permission scope:
  - `read_only`: list/search/read notes, tasks, events, sources.
  - `propose_only`: propose study plan, propose task changes, propose import changes.
  - `write_with_confirm`: create/update task, create/update note, update source visibility, run approved import.
  - `admin`: delete/bulk update/rollback/restore; requires explicit confirmation and backup checkpoint.
- Every write tool must produce dry-run/proposal output first.
- Every confirmed write tool logs to `agent_action_log`.
- Bulk/destructive/admin tools must create a backup/checkpoint before mutation.
- Write tools must return affected ids and rollback/recovery instructions.

### Library Choice

Preferred:

- LiteLLM if it works cleanly with the OpenAI-compatible router.
- LangGraph for multi-step agent orchestration, permission gate, tool call state, rollback/approval flow.
- Otherwise minimal `httpx` OpenAI-compatible client only for the LLM adapter.

Do not let LangGraph or tool-calling bypass the permission/audit layer.

### Acceptance Criteria

- Router off does not crash app.
- Provider config never logs secret.
- Chat response can cite note/task/event ids used as context.
- Read-only tools can run without confirm.
- Write tools cannot mutate without dry-run + explicit confirm.
- Confirmed write tools create audit records.
- Bulk/destructive tools create a backup/checkpoint before mutation.

## Phase 8 Task - Docs Reconciliation

### Goal

Sync README and docs with the code that has actually been merged, without changing schema/API/runtime behavior.

### Suggested Branch

`docs/v2-docs-sync`

### Files To Modify

- `README.md`
- `docs/V2_CURRENT_STATE.md`
- `docs/SYSTEM_ARCHITECTURE.md`
- `docs/DATABASE_SCHEMA.md`
- `docs/IMPORT_GUIDE.md`
- `docs/EXPORT_GUIDE.md`
- `docs/UI_GUIDE.md`
- `docs/V2_BACKUP_RESTORE.md` only for clarification/consistency

### Required Behavior

- Treat `develop` as the v2 line and `main` as preserved v1 legacy.
- State clearly which `main.py` paths have already moved to PostgreSQL v2 services and which paths remain legacy pending WS6/refactor.
- Document implemented v2 foundation modules under `app/`.
- Do not claim continuous calendar UI or AI agent/tools are implemented until their workstreams merge.
- Treat `docs/V2_DECISION_BRIEF.md`, `docs/v2_contracts/WS0_WS1_CONTRACT.md`, and `app/db/schema.sql` as v2 contract sources.
- Do not edit `.env`, SQLite v1, schema SQL, app code, or tests.

### Acceptance Criteria

- README points readers to the correct v1/v2 current-state docs.
- Architecture docs are v2-first and mention v1 only as preserved legacy on `main`.
- Database docs label SQLite as v1 legacy and link/summarize PostgreSQL v2 schema.
- Import docs explain source/source_version versioning and duplicate no-op.
- Export docs explain `PlannerExportDTO`, Markdown default, JSON optional.
- UI docs say Notes UI is done, while continuous calendar and AI UI remain pending.

### Verification

```powershell
git status --short --branch
python -m pytest
rg "SQLite|todo.db|JSON|15 backup|2 giờ|database.py|main.py|Month View|Export JSON" README.md docs -n
rg "DATABASE_URL|NINE_ROUTER|password|secret|api_key" README.md docs -n
```

Stale v1 references may remain only when clearly labeled as legacy or archive.

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

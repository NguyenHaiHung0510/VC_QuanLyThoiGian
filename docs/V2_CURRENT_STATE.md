# microSchedule v2 - Current State

Ngày cập nhật: 2026-05-25

Tài liệu này là bản đồ trạng thái hiện tại sau khi v2 foundation đã được merge vào `develop`. Nó không thay thế `docs/V2_DECISION_BRIEF.md`; decision brief vẫn là nguồn quyết định kiến trúc cấp Tier 1.

## 1. Trạng Thái Tổng Quan

Repo hiện đã chuyển sang hướng `develop = v2`:

| Track | Trạng thái | Ghi chú |
|---|---|---|
| v1 desktop app | Bảo lưu trên `main` | Không động vào `main`; legacy docs nằm trong `docs/archive/v1_legacy/` |
| v2 foundation | Đã merge | PostgreSQL schema/migration, import source versioning, export DTO Markdown/JSON, backup service |
| v2 UI integration | Đang refactor dần | Notes UI đã merge; continuous calendar vẫn là workstream riêng |
| v2 AI agent/tools | Chưa merge | Chỉ mới có schema/audit contract, chưa có implementation tool safety |

Điều quan trọng: không đọc các docs v1 cũ như contract v2. Schema/API v2 phải theo decision brief, contract docs và code trong `app/`.

## 2. Nguồn Sự Thật Hiện Tại

| Mục đích | Source |
|---|---|
| Quyết định kiến trúc v2 | `docs/V2_DECISION_BRIEF.md` |
| Contract WS0/WS1 | `docs/v2_contracts/WS0_WS1_CONTRACT.md` |
| PostgreSQL DDL v2 | `app/db/schema.sql` |
| Migration report và counts | `docs/V2_MIGRATION_REPORT.md` |
| Backup/restore v2 | `docs/V2_BACKUP_RESTORE.md` |
| Flet shell / UI integration | `main.py`, `docs/UI_GUIDE.md` |

## 3. V2 Foundation Đã Có Trong Code

Đã merge trong commit `8c08620`:

- `app/config.py`: load `.env`, validate target database, redact connection string.
- `app/db/postgres.py`: helper kết nối PostgreSQL, transaction, apply schema, reset public schema có guard.
- `app/db/schema.sql`: schema PostgreSQL v2 gồm calendar source/version/events, tasks, notes, priorities, app settings, backup runs, agent action log.
- `app/migration/analyze_v1_sqlite.py`: analyzer read-only cho SQLite v1.
- `app/migration/migrate_sqlite_to_postgres.py`: migration dry-run/apply từ SQLite v1 sang PostgreSQL v2.
- `app/importers/*`: parser ICS và Excel exam fallback.
- `app/services/calendar_source_service.py`: CRUD/service cơ bản cho calendar sources.
- `app/services/calendar_import_service.py`: import file theo source-level versioning, duplicate checksum no-op.
- `app/exporters/*` và `app/services/export_service.py`: canonical `PlannerExportDTO`, Markdown exporter, JSON exporter.
- `app/services/backup_service.py`: backup PostgreSQL bằng `pg_dump -Fc`, temp file rồi atomic rename, retention, log `backup_runs`.
- `app/services/notes_service.py`: PostgreSQL-backed Notes CRUD và note items.
- `main.py`: đã có tab `GHI CHÚ` dùng NotesService; các phần lịch/task legacy còn cần refactor tiếp.

## 4. Kết Quả Hiện Có

Theo `docs/V2_MIGRATION_REPORT.md`:

- SQLite v1 source counts: 116 tasks, 81 subtasks, 295 schedule rows, 4 settings.
- Migration đã chuyển 29 incomplete overdue tasks thành notes.
- PostgreSQL v2 sau migration/import/backup test:
  - 87 tasks
  - 29 notes
  - 442 calendar events
  - 3 calendar sources
  - 3 calendar source versions
  - 1 backup run
- Import kết quả:
  - `TKB-QLDT20252.ics`: 139 active study events.
  - `LichThi-QLDT-20252.ics`: 8 active exam events.
  - Re-import cùng file trả `duplicate_noop`.
- Restore verification:
  - Latest dump đã restore vào database tạm.
  - Count các bảng chính match.
  - Database tạm đã được drop.

## 5. Workstream Chưa Xong

- WS6 Continuous Calendar UI: `main.py` vẫn dùng UI v1; docs không được nói Outlook-style continuous calendar đã thay thế month grid.
- WS7 AI Agent/Tools: chưa có `app/ai/*`; mọi write/admin tool tương lai phải có dry-run, confirm, audit log và backup/checkpoint.
- Full app integration: các phần task/calendar/settings trong `main.py` chưa được refactor hết sang PostgreSQL v2 services.

## 6. Lệnh Kiểm Chứng Hữu Ích

```powershell
python -m pytest
python app\migration\analyze_v1_sqlite.py
python app\migration\migrate_sqlite_to_postgres.py --dry-run
python app\migration\migrate_sqlite_to_postgres.py --apply
```

Khi thao tác với PostgreSQL thật, không in `.env`, không log password, và không sửa/xóa SQLite v1 tại:

```text
C:\Users\os\Desktop\Tools\VC_microSchedule_home\todo.db
```

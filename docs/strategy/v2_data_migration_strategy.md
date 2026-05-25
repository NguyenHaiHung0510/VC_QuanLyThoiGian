# v2 Data Migration Strategy

## Boi Canh

Du lieu v1 co tasks, subtasks, schedule va settings trong SQLite. Thuc te 29 incomplete overdue tasks dang la notes/ideas, nen neu migrate thang thanh tasks se lam roi lich on thi.

## Quyet Dinh

- Migration one-shot tu SQLite v1 sang PostgreSQL v2.
- SQLite v1 chi doc read-only.
- 29 incomplete overdue tasks migrate thanh `notes`.
- Subtasks di theo parent: task -> `task_items`, note -> `note_items`.
- Existing v1 schedule migrate thanh source `v1_sqlite_schedule`.
- Lich hoc/thi moi import thanh source rieng voi source-level versioning.

## Trade-off

- Khong giu `source_task_id` trong notes: data v2 sach hon, doi lai trace chi nam trong migration report.
- Source-level versioning du dung cho lich truong; khong lam event-level supersede de giam phuc tap.
- Reset dev DB chi cho phep voi DB name `microschedule_v2`.

## Tac Dong

- Calendar query chi lay events thuoc `calendar_sources.current_version_id`.
- Notes khong bi tinh la overdue tasks.
- Backup/restore phai verify PostgreSQL, khong copy data directory.

## Quality Gates

- Analyzer/dry-run deterministic.
- Apply migration transactionally.
- Count report nam trong `docs/V2_MIGRATION_REPORT.md`.
- Restore latest dump vao DB tam va compare counts.
- Khong log password/full connection string.

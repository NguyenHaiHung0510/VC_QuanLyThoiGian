# microSchedule v2 - Parallel Tier 2 Execution Board

Mục tiêu: chia v2 thành nhiều workstream có thể chạy song song, giảm conflict, và giữ các quyết định kiến trúc ở Tier 1/Codex.

## Coordination Rules

- Tất cả workstream rẽ nhánh từ `develop`.
- Mỗi workstream chỉ sửa file trong ownership của mình, trừ khi task spec cho phép.
- Workstream nào cần đổi schema/API contract phải viết proposal và dừng, không tự sửa rộng.
- Không merge workstream UI/AI vào `develop` trước khi schema + repository contract đã ổn.
- Mỗi workstream trả report theo template trong `V2_TIER2_IMPLEMENTATION_PLAN.md`.
- Nếu hai model cần cùng sửa một file, Tier 1/Codex phải tách contract trước hoặc gom task đó về một model.

## Recommended Parallel Split

| Workstream | Status | Suggested owner | Depends on | Branch | Scope |
|---|---|---:|---|---|---|
| WS0 Architecture contract | Done | Codex / strong Tier 1 | None | merged | Lock schema, repository interfaces, shared DTOs |
| WS1 PostgreSQL schema + migration | Done | Codex / strong Tier 2 | WS0 | merged | Schema SQL, config, SQLite migration, migration report |
| WS2 Import parser + source versioning | Done | Gemini Flash 3.5 | WS0/WS1 | merged | ICS/Excel parser, source/version service, import tests |
| WS3 Export Markdown/JSON | Done | Gemini Flash 3.5 | WS0/WS1 | merged | Export DTO, Markdown renderer, JSON renderer, tests |
| WS4 PostgreSQL backup/restore | Done | Gemini Flash 3.5 | DB schema | merged | pg_dump, retention, restore docs, backup log |
| Restore verification | Done | Tier 2 verification | WS4 backup | merged | Restore latest dump into temp DB, compare counts, cleanup |
| WS5 Notes UI | Done | Gemini Flash 3.5 or Sonnet | WS1 repositories | merged | Notes tab CRUD, note items, no due date |
| WS6 Continuous calendar UI | Next | Sonnet / Codex / strong Tier 2 | WS1 + WS2 services | `feat/v2-continuous-calendar` | Outlook-style scrolling weeks + sidebar filters |
| WS7 AI agent + safety | Later | Codex / strong model in separate chat | WS0 + backup/audit contract | `feat/v2-ai-agent-tools` | LangGraph/LiteLLM, tools, permission gates, audit, rollback |
| WS8 Docs reconciliation | Done | Gemini Flash 3.5 | Merged code | merged | README/docs sync for implemented v2 foundation and Notes UI |

## Current Next Work

1. WS6 continuous calendar UI.
2. WS7 AI agent/tools after WS6 or after a dedicated safety design pass.
3. Final docs sync after WS6/WS7.

## Work That Should Wait

- Continuous calendar UI waits until source/version query service exists.
- AI write tools wait until backup, audit log, and permission policy are implemented.
- Any destructive admin tool waits until restore has been tested on a temp DB.

## Suggested Merge Order

Completed through WS5 and restore verification. Remaining recommended order:

1. WS6 continuous calendar UI.
2. WS7 AI agent/tools.
3. WS8 docs reconciliation rerun after WS6/WS7.

## Files By Ownership

WS0:
- `docs/V2_DECISION_BRIEF.md`
- `agent_workflow_doc/tier2_task_specs/*.md`
- contract docs under `docs/v2_contracts/`

WS1:
- `app/config.py`
- `app/db/*`
- `app/migration/*`
- `docs/V2_MIGRATION_REPORT.md`
- `requirements.txt`

WS2:
- `app/importers/*`
- `app/services/calendar_source_service.py`
- `app/services/calendar_import_service.py`
- `tests/test_calendar_import_service.py`

WS3:
- `app/exporters/*`
- `app/services/export_service.py`
- `tests/test_export_service.py`

WS4:
- `app/services/backup_service.py`
- `app/db/backup_runs_repository.py` if repository split exists
- `docs/V2_BACKUP_RESTORE.md`
- `tests/test_backup_service.py` where feasible

WS5:
- `app/ui/notes*`
- Notes repository/service only if not already created by WS1

WS6:
- `app/ui/calendar*`
- Calendar query/view-model service if not already created by WS2

WS7:
- `app/ai/*`
- `app/services/audit_service.py`
- `app/services/agent_action_service.py`
- tests for permission/audit/tool safety

WS8:
- `README.md`
- `docs/V2_CURRENT_STATE.md`
- `docs/SYSTEM_ARCHITECTURE.md`
- `docs/DATABASE_SCHEMA.md`
- `docs/IMPORT_GUIDE.md`
- `docs/EXPORT_GUIDE.md`
- `docs/UI_GUIDE.md`
- `docs/V2_BACKUP_RESTORE.md` only for clarification/consistency
- `agent_workflow_doc/tier2_task_specs/*.md` only for docs coordination notes

## Tasks Best Kept For Codex In A Separate Chat

Use Codex/strong model for:

- Final schema contract and migration review.
- Cross-workstream integration after WS1/WS2/WS3 merge.
- Continuous calendar if Flet scroll behavior becomes tricky.
- AI agent safety implementation, especially write tools, audit log, backup checkpoints, rollback/recovery.
- Final review before any migration touches real data.

## Tier 2 Prompt Header

Use this header when assigning a workstream:

```text
Bạn là Tier 2 implementer cho microSchedule v2.
Đọc theo thứ tự:
1. docs/V2_DECISION_BRIEF.md
2. agent_workflow_doc/tier2_task_specs/V2_TIER2_IMPLEMENTATION_PLAN.md
3. agent_workflow_doc/tier2_task_specs/V2_PARALLEL_EXECUTION_BOARD.md

Bạn chỉ làm workstream: <WS name>.
Không sửa file ngoài ownership nếu chưa hỏi.
Nếu phát hiện cần đổi schema/API contract, dừng và viết proposal.
Trả report theo template cuối V2_TIER2_IMPLEMENTATION_PLAN.md.
```

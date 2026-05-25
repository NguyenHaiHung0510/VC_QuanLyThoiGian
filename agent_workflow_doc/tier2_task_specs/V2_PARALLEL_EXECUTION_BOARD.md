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

| Workstream | Suggested owner | Can start now? | Depends on | Branch | Scope |
|---|---|---:|---|---|---|
| WS0 Architecture contract | Codex / strong Tier 1 | Yes | None | `docs/v2-contract-lock` | Lock schema, repository interfaces, shared DTOs |
| WS1 PostgreSQL schema + migration | Codex / strong Tier 2 | Yes | WS0 draft | `feat/v2-postgres-migration` | Schema SQL, config, SQLite migration, migration report |
| WS2 Import parser + source versioning | Gemini Flash 3.5 | Partial | WS0 schema names | `feat/v2-import-versioning` | ICS/Excel parser, source/version service, import tests |
| WS3 Export Markdown/JSON | Gemini Flash 3.5 | Partial | WS0 DTO/repo interfaces | `feat/v2-export-markdown` | Export DTO, Markdown renderer, JSON renderer, tests |
| WS4 PostgreSQL backup/restore | Gemini Flash 3.5 | Yes | `.env` path, DB name | `feat/v2-postgres-backup` | pg_dump, retention, restore docs, backup log |
| WS5 Notes UI | Gemini Flash 3.5 or Sonnet | No | WS1 repositories | `feat/v2-notes-ui` | Notes tab CRUD, note items, no due date |
| WS6 Continuous calendar UI | Sonnet / Codex / strong Tier 2 | No | WS1 + WS2 services | `feat/v2-continuous-calendar` | Outlook-style scrolling weeks + sidebar filters |
| WS7 AI agent + safety | Codex / strong model in separate chat | Partial design only | WS0 + backup/audit contract | `feat/v2-ai-agent-tools` | LangGraph/LiteLLM, tools, permission gates, audit, rollback |
| WS8 Docs reconciliation | Gemini Flash 3.5 | Yes for v2 foundation docs | WS1-WS4 merged code | `docs/v2-docs-sync` | README/docs sync for implemented v2 foundation; do not claim WS5/WS6/WS7 runtime features are done |

## What Can Run In Parallel Immediately

1. WS0 by Codex: lock shared contracts.
2. WS1 by Codex/strong Tier 2: schema + migration.
3. WS4 by Gemini Flash: backup service can be implemented against current `microschedule_v2` and `.env` path with minimal schema dependency.
4. WS2 parser-only slice by Gemini Flash: parse ICS/Excel into normalized dataclasses without writing DB yet.
5. WS3 formatter-only slice by Gemini Flash: Markdown/JSON renderers using fixture DTOs.
6. WS7 design-only slice by Codex/strong model: permission matrix, audit schema, tool registry design.

## Work That Should Wait

- Notes UI waits until notes repository/service exists.
- Continuous calendar UI waits until source/version query service exists.
- AI write tools wait until backup, audit log, and permission policy are implemented.
- Any destructive admin tool waits until restore has been tested on a temp DB.

## Suggested Merge Order

1. WS0 contract doc/schema interface.
2. WS1 schema + migration.
3. WS2 import versioning.
4. WS3 export service.
5. WS4 backup service.
6. WS5 Notes UI.
7. WS6 continuous calendar UI.
8. WS7 AI agent/tools.
9. WS8 docs reconciliation.

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

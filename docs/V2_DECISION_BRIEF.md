# microSchedule v2 - Decision Brief

Ngày khảo sát: 2026-05-25  
Vai trò tài liệu: Tier 1 strategy, dùng để bạn chọn hướng trước khi giao Tier 2 implement.

## Executive Summary

Khuyến nghị chiến lược: làm v2 theo hướng "PostgreSQL + schema mới + Flet UI được tách service layer", chưa vội rewrite full web/backend. Lý do: app hiện nhỏ, dùng cá nhân, nhưng nhu cầu mới đòi hỏi data model chắc hơn, import có versioning, note tách khỏi task, và lịch cuộn kiểu Outlook. Tách backend/frontend hoàn toàn nên để sau khi data model ổn.

Các quyết định nên chốt trước khi giao Tier 2:

| Nhóm | Khuyến nghị Tier 1 | Lựa chọn cần bạn duyệt |
|---|---|---|
| Import lịch học/thi | Dùng `calendar_sources` + `import_batches` + `calendar_events`, upsert theo UID/hash, không insert mù | Chọn "batch versioning + supersede" |
| Task vs Note | Tạo module Notes riêng, migrate 29 task chưa hoàn thành quá hạn sang note | Chọn rule migrate tự động hay review tay |
| Calendar UI | Thay month grid bằng continuous multi-week view + left sidebar | Chốt Flet incremental hay rewrite UI |
| Export | Markdown là mặc định, JSON vẫn giữ như tuỳ chọn setting | Chọn format mặc định: Markdown |
| Database | PostgreSQL `microschedule_v2`, schema mới, không reuse schema SQLite cũ | Duyệt schema migration |
| Backup | Dùng `pg_dump` theo lịch + retention; backup app config riêng | Chọn policy backup |
| AI | Giai đoạn đầu làm Chat + RAG + internal tools read-only, chưa cho agent mutate DB | Chọn mức tự động hoá AI |

Hiện trạng đã chuẩn bị:
- Đã switch sang nhánh `develop`.
- Đã tạo `.env` local và `.env.example`; `.env` đã được đưa vào `.gitignore`.
- Đã tạo database PostgreSQL rỗng `microschedule_v2`.
- Chưa migrate dữ liệu và chưa tạo schema vì cần duyệt quyết định.

## 1. Hiện Trạng V1

### Codebase

App hiện là desktop app Flet tự chứa:
- `main.py`: UI + state + một phần query/export.
- `database.py`: SQLite DAL, import ICS/Excel, settings, backup.
- SQLite path đang hardcode: `C:\Users\os\Desktop\Tools\VC_microSchedule_home\todo.db`.
- Backup v1 là copy file SQLite mỗi 2 giờ, giữ 15 bản.

Điểm code quan trọng:
- Schema SQLite tạo trực tiếp trong `database.py` dòng 34-44.
- Backup copy file ở `database.py` dòng 104-127.
- Import ICS insert thẳng vào `schedule` ở `database.py` dòng 181-240.
- Import Excel insert thẳng vào `schedule` ở `database.py` dòng 245-340.
- Month view hiện dùng `calendar.monthcalendar` cố định theo tháng ở `main.py` dòng 716-915.
- Task dialog có edit task/subtask sẵn ở `main.py` dòng 1170-1361.

### Dữ liệu v1 thực tế

SQLite hiện có:

| Bảng | Số dòng |
|---|---:|
| `tasks` | 116 |
| `subtasks` | 81 |
| `schedule` | 295 |
| `settings` | 4 |

Task chưa hoàn thành:
- 29 task chưa hoàn thành.
- 29/29 đều quá hạn so với ngày khảo sát 2026-05-25.
- Mẫu dữ liệu gần nhất là các note/ý tưởng về AI như "Flow to make video?", "code wiki", "hermes agent", "Mấy model Trung Quốc".

Kết luận: nhận định "task đang bị dùng như note" là đúng với dữ liệu hiện tại.

### File lịch mới

| File | Loại | Số event/dòng đọc được | Ghi chú |
|---|---|---:|---|
| `TKB-QLDT20252.ics` | Lịch học | 139 VEVENT | Có UID dạng `*@qldt.ptit.edu.vn-20252` |
| `LichThi-QLDT-20252.ics` | Lịch thi | 8 VEVENT | Có UID dạng `*@qldt.ptit.edu.vn-LichThi-20252` |
| `LichThi.xlsx` | Lịch thi | 8 dòng dữ liệu | Có vài ô ngày bị openpyxl đọc lệch do format `mm-dd-yy` |

Khuyến nghị: với lịch thi kỳ này, ưu tiên ICS làm source chuẩn. Excel chỉ dùng để đối chiếu hoặc fallback vì 3 dòng có nguy cơ hiểu nhầm ngày/tháng.

## 2. Quyết Định 1 - Import Versioning

Vấn đề v1: import hiện tại insert thẳng vào `schedule`, không biết event đến từ file nào, lần import nào, UID nào, và không phát hiện lịch bị đổi/hủy.

### Option A - Replace theo source

Mỗi source như "Lịch học 20252" hoặc "Lịch thi 20252" chỉ có một bản active. Import mới sẽ archive toàn bộ event active cũ của source rồi insert bản mới.

Ưu:
- Dễ implement.
- Ít lỗi duplicate.
- Phù hợp nếu chỉ cần "trạng thái mới nhất".

Nhược:
- Không thấy diff chi tiết từng event.
- Không giữ lifecycle event tốt nếu muốn biết môn nào bị đổi phòng/giờ.

### Option B - Batch versioning + supersede (khuyến nghị)

Tạo các bảng:
- `calendar_sources`: nguồn lịch, ví dụ `school_schedule_20252`, `exam_schedule_20252`.
- `import_batches`: mỗi lần import một file, lưu file name, checksum, imported_at, source_id.
- `calendar_events`: event normalized, có `external_uid`, `content_hash`, `valid_from_batch_id`, `superseded_by_batch_id`, `status`.

Import mới:
- Parse file thành normalized events.
- Match theo `source_id + external_uid` nếu có UID.
- Nếu không có UID thì match theo fingerprint như subject/date/time/location.
- Nếu cùng UID nhưng hash đổi: mark event cũ superseded, insert event mới.
- Nếu event cũ không còn trong file mới: mark `missing_in_latest` hoặc `cancelled_by_import`.
- Không hard delete khi import.

Ưu:
- Giải quyết đúng bài toán lịch trường thay đổi.
- Có audit trail.
- Có thể build UI "import diff" sau này.

Nhược:
- Schema phức hơn.
- Tier 2 phải có test migration/import kỹ.

### Option C - Import diff approval UI

Giống Option B nhưng trước khi commit import, UI hiển thị diff: added/changed/removed, bạn bấm accept.

Ưu:
- Kiểm soát cao nhất.

Nhược:
- Tốn UI effort, chưa cần ở phase đầu.

### Tier 1 chọn

Chọn Option B cho v2 core. UI diff có thể để phase sau. Đây là điểm không nên giao Tier 2 làm kiểu "insert ignore" vì sẽ khóa sai data model.

## 3. Quyết Định 2 - Tách Notes Khỏi Tasks

Vấn đề v1: task có deadline bắt buộc theo UX, nên note bị coi là overdue task.

### Option A - Thêm type vào `tasks`

Một bảng `tasks`, thêm `kind = task|note`; note có `date_str` nullable.

Ưu:
- Migrate nhanh.
- Ít sửa code query ban đầu.

Nhược:
- Dễ tiếp tục lẫn logic task/note.
- Calendar/export phải filter nhiều nơi.

### Option B - Tạo module Notes riêng (khuyến nghị)

Tạo bảng riêng:
- `notes`: title, body, priority_id nullable, created_at, updated_at, archived_at, pinned, source_task_id.
- `note_items`: note_id, content, is_done, position, created_at.
- Có thể thêm `tags` sau.

Migration:
- Mặc định chuyển các task `is_completed = 0 AND date_str < current_date` sang notes.
- Subtasks của task chuyển thành `note_items`.
- Giữ `source_task_id` để trace về v1.
- Có thể mark task cũ là migrated trong bảng migration log, không cần giữ trong v2 tasks.

Ưu:
- Sạch khái niệm: task = có deadline/action; note = tri thức/ý tưởng.
- Calendar không còn bị rối bởi note.
- Rất hợp workflow note nhanh + subnote.

Nhược:
- Cần UI tab Notes mới.
- Export phải biết cả tasks lẫn notes.

### Option C - Notes dạng outline/block

Thay `note_items` bằng block tree để hỗ trợ nhiều tầng.

Ưu:
- Mạnh hơn cho knowledge/RAG.

Nhược:
- Quá tay cho v2 phase đầu.

### Tier 1 chọn

Chọn Option B. Rule migrate mặc định: chuyển 29 incomplete overdue tasks hiện tại sang notes. Nếu bạn lo có task thật bị chuyển nhầm, thêm file report `migration_review_notes.md` trước khi apply.

## 4. Quyết Định 3 - Continuous Calendar + Sidebar

Vấn đề v1: month view cố định theo tháng, tuần bị ngắt ở boundary, và task/note bị trộn.

### Option A - Flet incremental continuous calendar (khuyến nghị phase đầu)

Giữ Flet, thay `load_month_view()` bằng:
- Left sidebar:
  - Mini month navigator.
  - Checkbox filters theo source.
  - Source color.
- Main area:
  - `ListView`/scrollable column các week rows liên tục.
  - Mỗi row là đủ 7 ngày, không split month.
  - Header update theo visible range.
  - Click mini date scroll tới week chứa date.

Ưu:
- Phù hợp app hiện tại.
- Không rewrite stack.
- Tier 2 có thể làm theo spec từng phần.

Nhược:
- Flet scroll position/virtualization có thể cần workaround.
- Header theo visible range không mượt bằng web.

### Option B - FastAPI backend + web frontend calendar

Tách backend FastAPI, frontend web dùng React/Vue/Svelte và thư viện calendar hoặc tự render.

Ưu:
- Calendar UI dễ mạnh và mượt hơn.
- AI/agent tools dễ gọi API.

Nhược:
- Rewrite lớn, rủi ro tăng.
- Không cần ngay nếu app cá nhân desktop.

### Option C - Flet v2 nhưng calendar là custom webview

Giữ Flet shell, nhúng calendar HTML/JS.

Ưu:
- Calendar linh hoạt hơn Flet thuần.

Nhược:
- Tăng độ phức tạp debug.

### Tier 1 chọn

Chọn Option A trước. Nếu Flet không đáp ứng scroll/header tốt sau prototype, lúc đó mới nâng lên Option B.

## 5. Quyết Định 4 - Export Markdown/JSON

Vấn đề v1: JSON tốt cho tool, nhưng Markdown thường dễ đọc hơn cho chat AI và bạn đang dùng AI thủ công nhiều.

### Option A - Markdown default + JSON optional (khuyến nghị)

Settings:
- `export.default_format = markdown`
- `export.include_notes = true`
- `export.include_completed = false`
- `export.lookahead_days = 30`

Export Markdown nên có section:
- Metadata.
- Lịch thi/lịch học sắp tới.
- Tasks có deadline.
- Notes/pinned notes.
- Context cho AI lập kế hoạch.

JSON vẫn giữ để tool/agent đọc.

Ưu:
- Hợp với ChatGPT/Claude/Gemini.
- Không mất khả năng machine-readable.

Nhược:
- Cần maintain 2 formatter.

### Option B - Chỉ Markdown

Ưu:
- Đơn giản.

Nhược:
- Mất API/tool export có cấu trúc.

### Option C - JSON canonical, Markdown render từ JSON

Tạo object export chuẩn rồi render ra Markdown/JSON.

Ưu:
- Ít drift giữa 2 format.

Nhược:
- Cần thiết kế export DTO tử tế.

### Tier 1 chọn

Chọn Option C về implementation, Option A về UX. Nghĩa là internal build `PlannerExportDTO`, sau đó render Markdown mặc định hoặc JSON theo setting.

## 6. Quyết Định 5 - PostgreSQL + Migration

Vấn đề v1: SQLite file backup đủ dùng, nhưng data model mới cần versioning, audit, RAG/AI query, và backup đáng tin cậy hơn.

### Option A - PostgreSQL schema mới, migrate one-shot (khuyến nghị)

Tạo schema v2 và script migrate:
- Đọc SQLite v1 read-only.
- Ghi PostgreSQL v2 trong transaction.
- Tạo report count trước/sau.
- Không sửa `todo.db`.

Ưu:
- Sạch, rõ.
- Bảo toàn v1.
- Dễ test.

Nhược:
- Cần viết migration script có kiểm thử.

### Option B - Compatibility schema gần giống SQLite

Port bảng cũ sang PostgreSQL gần như nguyên trạng, rồi migrate dần.

Ưu:
- Nhanh.

Nhược:
- Mang nợ schema cũ sang v2.

### Option C - Giữ SQLite, chỉ refactor

Ưu:
- Ít thay đổi hạ tầng.

Nhược:
- Không đúng mong muốn v2 và AI/RAG dài hạn.

### Tier 1 chọn

Chọn Option A. Database `microschedule_v2` đã tạo rỗng, nhưng chưa tạo schema.

Schema khởi điểm đề xuất:

```sql
calendar_sources(id, name, kind, color, is_visible, created_at, updated_at)
import_batches(id, source_id, file_name, file_sha256, imported_at, parser_version, status, summary_json)
calendar_events(id, source_id, external_uid, content_hash, title, description, starts_at, ends_at, location, event_type, status, valid_from_batch_id, superseded_by_batch_id, created_at, updated_at)

tasks(id, title, note, priority_id, due_at, status, created_at, updated_at, completed_at)
task_items(id, task_id, content, is_completed, position, created_at, updated_at)

notes(id, title, body, priority_id, pinned, archived_at, source_task_id, created_at, updated_at)
note_items(id, note_id, content, is_done, position, created_at, updated_at)

priorities(id, name, label, color, icon, sort_order, created_at, updated_at)
app_settings(key, value_json, updated_at)
backup_runs(id, kind, status, artifact_path, started_at, finished_at, message)
```

## 7. Quyết Định 6 - Backup System

PostgreSQL không nên backup bằng copy file data directory. Nên dùng `pg_dump`.

### Kịch bản A - Local `pg_dump` scheduled, retention đơn giản

Tự động chạy:
- Backup mỗi 6 giờ hoặc khi app start nếu quá hạn.
- `pg_dump -Fc microschedule_v2` ra folder v2 backup.
- Giữ 30 daily/latest hoặc theo dung lượng.
- Ghi log vào `backup_runs`.

Ưu:
- Dễ tự động hóa.
- Restore bằng `pg_restore`.
- Đủ cho app cá nhân.

Nhược:
- Nếu ổ đĩa hỏng thì mất cả app lẫn backup.

### Kịch bản B - Local + cloud sync folder (khuyến nghị)

Giống A, nhưng backup folder nằm trong thư mục được Google Drive/OneDrive sync hoặc có job copy sang cloud folder.

Ưu:
- Vẫn đơn giản, tăng an toàn thực tế.
- Hợp single-user.

Nhược:
- Phụ thuộc sync client.
- Cần tránh sync file đang ghi dở bằng cách dump ra temp rồi rename.

### Kịch bản C - Point-in-time recovery / WAL archive

Bật WAL archiving hoặc dùng công cụ backup Postgres chuyên hơn.

Ưu:
- Mạnh nhất.

Nhược:
- Quá nặng cho app cá nhân.

### Tier 1 chọn

Chọn Kịch bản B. App v2 backup riêng tại `VC_microSchedule_v2_home\backups`, dump ra file temp rồi rename. Retention đề xuất: giữ 48 bản gần nhất + 30 daily snapshot.

## 8. Quyết Định 7 - Có Nên Tách Backend/Frontend?

### Option A - Giữ desktop monolith nhưng tách layer (khuyến nghị ngay)

Structure:

```text
app/
  main.py                 # Flet entry
  ui/
  services/
  repositories/
  importers/
  exporters/
  ai/
  db/
```

Ưu:
- Tăng reliability mà không rewrite.
- Test service/import/export được.
- Tier 2 dễ làm theo module.

Nhược:
- UI vẫn là Flet desktop.

### Option B - FastAPI backend + Flet frontend

Ưu:
- API rõ, AI tools gọi được.
- Sau này web/mobile dễ hơn.

Nhược:
- Thêm server process, auth/local config, deployment.

### Option C - Full web app

Ưu:
- UI calendar/AI chat dễ đẹp.

Nhược:
- Rewrite lớn nhất.

### Tier 1 chọn

Chọn Option A cho v2 phase 1-3. Khi AI agent cần mutate data qua tools hoặc bạn muốn dùng app từ nhiều device, nâng lên Option B.

## 9. Quyết Định 8 - AI Trong App

Nguồn LLM:
- Dùng endpoint OpenAI-compatible qua `NINE_ROUTER_URL`.
- Key đọc từ `.env`, không hardcode.
- Script list model từ FANG hiện chưa chạy được vì service tại `localhost:20128` đang từ chối kết nối.

### Option A - Chat + context export

AI chat trong app, mỗi lần gửi kèm Markdown context hiện tại.

Ưu:
- Dễ làm.
- Ít rủi ro.

Nhược:
- Không có memory/RAG thật.

### Option B - Chat + RAG notes/schedule/tasks (khuyến nghị phase đầu AI)

Tạo local index cho notes/tasks/schedule:
- Embed notes và task text.
- Query RAG theo câu hỏi.
- LLM trả lời trong app.
- Có citation nội bộ theo note/task/event id.

Ưu:
- Phục vụ đúng nhu cầu note AI.
- Không cho AI tự sửa dữ liệu nên an toàn.

Nhược:
- Cần chọn embedding model và storage vector.

### Option C - Agent + internal tools + MCP

Agent có tools:
- read calendar/tasks/notes.
- propose study plan.
- create/update tasks.
- import/reconcile calendar.
- export markdown.

Ưu:
- Mạnh nhất, đúng hướng "agent hỗ trợ sâu".

Nhược:
- Rủi ro mutate sai data.
- Cần permission model, audit log, dry-run/confirm.

### Tier 1 chọn

Chọn Option B trước, thiết kế sẵn boundary để lên Option C. Mọi tool ghi DB phải có dry-run + user confirm ở phase đầu.

Thư viện:
- Khuyến nghị không dùng LangChain cho phase đầu nếu chỉ chat/RAG đơn giản; viết adapter OpenAI-compatible bằng `httpx` hoặc dùng LiteLLM.
- Dùng LiteLLM nếu muốn đổi model/router dễ.
- Dùng LangGraph khi thật sự làm agent multi-step có state, tool call, rollback/approval.

Model policy đề xuất:
- `AI_DEFAULT_FAST_MODEL`: Gemini Flash qua 9Router khi router bật.
- `AI_DEFAULT_REASONING_MODEL`: model mạnh hơn qua 9Router/OpenRouter nếu có.
- Không hardcode tên model cho đến khi `/models` chạy được; lưu model id trong settings sau.

## 10. Roadmap Giao Tier 2

### Phase 0 - Safety & baseline

Mục tiêu:
- Không phá v1.
- Thiết lập config, docs, database target.
- Tạo migration dry-run report.

Output:
- `.env.example`, `.env` local.
- `microschedule_v2` exists.
- Migration analyzer report.

### Phase 1 - PostgreSQL schema + migration

Mục tiêu:
- Tạo schema v2.
- Migrate SQLite v1 sang Postgres.
- Chuyển 29 incomplete overdue tasks thành notes theo rule đã duyệt.
- Import file lịch mới vào schema versioning.

Acceptance:
- Count report trước/sau.
- Không duplicate events nếu import lại cùng file.
- Event thay đổi tạo version mới, không ghi đè mất lịch sử.

### Phase 2 - Service layer + export Markdown/JSON

Mục tiêu:
- Tách repository/service.
- Export DTO canonical.
- Markdown default, JSON optional.

Acceptance:
- Export Markdown có schedule, tasks, notes.
- JSON giữ đủ cấu trúc cho tool.

### Phase 3 - UI Notes + continuous calendar

Mục tiêu:
- Tab Notes riêng.
- Calendar continuous week rows.
- Sidebar mini month + filters.

Acceptance:
- Notes không xuất hiện như overdue task.
- Week không bị split tại ranh giới tháng.
- Toggle source ẩn/hiện event đúng.

### Phase 4 - Backup v2

Mục tiêu:
- `pg_dump` automation.
- Retention.
- Restore guide.

Acceptance:
- Có backup run thành công.
- Có command restore test trên DB temp.

### Phase 5 - AI chat/RAG

Mục tiêu:
- Chat UI.
- LLM provider config qua `.env`.
- RAG read-only trên notes/tasks/events.

Acceptance:
- Router off thì app báo lỗi cấu hình, không crash.
- Router on thì list model và chat được.
- Không có DB write tool ở phase đầu.

## 11. Những Điều Tier 2 Không Được Tự Quyết

Tier 2 không được tự:
- Đổi rule migrate note/task nếu chưa được duyệt.
- Xóa hoặc sửa SQLite v1.
- Hardcode API key/connection string vào code/docs.
- Chọn rewrite full web khi chưa được duyệt.
- Cho AI agent tự ghi DB không cần confirm.
- Import lịch bằng cách insert mù vào bảng event active.

Nếu phát hiện conflict, Tier 2 phải viết report và dừng ở boundary đó.

## 12. Câu Hỏi Cần Bạn Chốt

1. Import versioning: duyệt Option B `batch versioning + supersede` chứ?
2. Notes migration: tự động chuyển 29 incomplete overdue tasks sang notes, hay xuất review report trước?
3. Calendar UI: chấp nhận Flet incremental phase đầu chứ?
4. Export default: Markdown mặc định, JSON giữ tùy chọn chứ?
5. Backup: chọn kịch bản B local `pg_dump` + cloud-sync folder?
6. AI: phase đầu chỉ Chat + RAG read-only, chưa agent ghi DB chứ?


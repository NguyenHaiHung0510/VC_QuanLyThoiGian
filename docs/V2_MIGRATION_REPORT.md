# microSchedule v2 Migration Report

Generated at: 2026-05-25 16:36:49 +0700
Mode: apply
Source SQLite path: `C:\Users\os\Desktop\Tools\VC_microSchedule_home\todo.db`
Source SQLite SHA256: `8fa68a669e3eced5e058397d3c09e56097416f04c56817b4a4907398a2ad4761`
Target PostgreSQL database: `microschedule_v2`
Migration today/date cutoff: `2026-05-25`
Schema timestamp: `2026-05-25 16:36:49 +0700`

## SQLite v1 Counts

- tasks: 116
- subtasks: 81
- schedule: 295
- settings: 4

## Migration Plan

- Completed tasks to `tasks`: 87
- Open non-overdue tasks to `tasks`: 0
- Incomplete overdue tasks to `notes`: 29
- Legacy schedule rows to calendar source/version/events: 295
- Settings to `app_settings`: 4

## Tasks Converted To Notes

| v1 id | title | old date |
|---:|---|---|
| 103 | tìm hiểu về clawbot/moltbot | 2026-03-28 |
| 104 | Tìm hiểu về google developer program | 2026-03-28 |
| 147 | [NMAI] Kiểm tra tổng thể | 2026-05-08 |
| 151 | Kiểm tra vấn đề bảo mật của máy | 2026-05-15 |
| 152 | Nâng cấp workflow làm việc với AI agent | 2026-04-15 |
| 153 | Tìm hiểu về AI fine-tuning | 2026-04-15 |
| 154 | tìm hiểu về AI career path | 2026-04-15 |
| 156 | nghiên cứu về workflow làm việc với AI agent + phương án sử dụng Agent có phí | 2026-04-15 |
| 157 | learn from your failures last semester | 2026-04-21 |
| 158 | Nghiên cứu nâng cấp dự án RAG | 2026-04-23 |
| 159 | Nghiên cứu Agent builder | 2026-04-23 |
| 160 | Học dùng môi trường ảo lite  | 2026-04-27 |
| 161 | AI dịch thuật thời gian thực | 2026-05-06 |
| 162 | Mấy model Trung Quốc | 2026-05-07 |
| 163 | develop Agent + Skill | 2026-05-07 |
| 164 | Các dịch vụ cloud để host app | 2026-05-07 |
| 165 | tool tiết kiệm token Claude v.v | 2026-05-07 |
| 166 | Học cả về Jules (Đọc mail welcome Google one nguyenhaihung0510) | 2026-05-13 |
| 167 | Học cả về design, creator's work | 2026-05-13 |
| 168 | Khai thác AI để viết tool selenium khai thác API key v.v | 2026-05-21 |
| 169 | gemini spark | 2026-05-21 |
| 170 | google's daily brief | 2026-05-21 |
| 171 | tận dụng hệ sinh thái của google | 2026-05-21 |
| 172 | google's live glass | 2026-05-21 |
| 173 | Các Deal AI - Hạ tầng ngon | 2026-05-21 |
| 174 | hermes agent | 2026-05-21 |
| 175 | Codex plugin? Nếu còn sub (hoặc mua đc rẻ) | 2026-05-22 |
| 176 | code wiki (of google) | 2026-05-23 |
| 177 | Flow to make video? | 2026-05-23 |

## Rows Skipped Or Warnings

- None.

## PostgreSQL v2 Counts

- agent_action_log: 0
- app_settings: 8
- backup_runs: 0
- calendar_events: 295
- calendar_source_versions: 1
- calendar_sources: 1
- note_items: 26
- notes: 29
- priorities: 6
- task_items: 55
- tasks: 87

## Calendar Legacy Source Counts

- legacy_event_count: 295
- legacy_source_count: 1
- legacy_source_version_count: 1

## Post-Integration Import Results

- Imported `TKB-QLDT20252.ics` into source `Lich hoc 2025 ky 2`: 139 active events, version 1.
- Imported `LichThi-QLDT-20252.ics` into source `Lich thi 2025 ky 2`: 8 active events, version 1.
- Re-import duplicate checks returned `duplicate_noop` for both ICS files.

## Current PostgreSQL v2 Counts After Imports And Backup Test

- priorities: 6
- tasks: 87
- task_items: 55
- notes: 29
- note_items: 26
- calendar_sources: 3
- calendar_source_versions: 3
- calendar_events: 442
- app_settings: 8
- backup_runs: 1
- agent_action_log: 0

## Current Calendar Source Counts

| source | kind | versions | events | active events |
|---|---|---:|---:|---:|
| Lich hoc 2025 ky 2 | study_schedule | 1 | 139 | 139 |
| Lich thi 2025 ky 2 | exam_schedule | 1 | 8 | 8 |
| v1_sqlite_schedule | legacy_v1 | 1 | 295 | 295 |

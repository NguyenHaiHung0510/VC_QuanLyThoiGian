# Tier 2 Addendum Prompt — microSchedule Full System QA

Bạn là Model Tier 2 đang chạy full-system QA cho `microSchedule`. Mục tiêu là kiểm tra app thật, dữ liệu thật, backup/restore thật, và báo evidence đủ để Tier 1 sửa bug. Không sửa app code để test pass.

## Context Bắt Buộc

- Repo: `C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian`
- App URL khi chạy web verify: `http://127.0.0.1:8550`
- Python venv: `.\venv\Scripts\python.exe`
- Flet CLI: `.\venv\Scripts\flet.exe`
- PostgreSQL URL: đọc bằng `from app.config import load_config; load_config().database_url`
- SQLite legacy path: đọc bằng `load_config().sqlite_v1_path`
- Import fixtures bắt buộc cho TC import:
  - `C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian\LichThi-QLDT-20252.ics`
  - `C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian\LichThi.xlsx`
- Có `psql`, `pg_dump`, `pg_restore`.
- Dùng Browser/Chrome DevTools MCP cho manual UI; dùng Playwright cho automation.
- Dùng Google Drive/Docs/Sheets MCP nếu user giao file test, report, checklist, spreadsheet, hoặc artifact trên Google. Không dùng Google MCP để thay thế app-local verification.

## DB Backup/Restore Gate — Bắt Buộc

Tier 2 **phải backup trước khi test**. Nếu backup không thành công hoặc không verify được bằng `pg_restore --list`, dừng toàn bộ QA và báo `BLOCKED_BACKUP_FAILED`.

QA được phép mutate CSDL sau backup: thêm/sửa/xóa task, note, calendar source, import file, toggle source, archive/delete temporary records. Nhưng cuối run phải restore DB về snapshot backup.

### Backup

```powershell
cd C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian
$runId = "FULLQA_" + (Get-Date -Format "yyyyMMdd_HHmmss")
$backupDir = "agent_workflow_doc\tier2_task_specs\db_backups\$runId"
$artifactDir = "agent_workflow_doc\tier2_task_specs\qa_artifacts\$runId"
New-Item -ItemType Directory -Force -Path $backupDir,$artifactDir | Out-Null

$env:DATABASE_URL = (& .\venv\Scripts\python.exe -c "from app.config import load_config; print(load_config().database_url)")
$safeDbUrl = (& .\venv\Scripts\python.exe -c "from app.config import load_config; print(load_config().safe_database_url)")
$sqlitePath = (& .\venv\Scripts\python.exe -c "from app.config import load_config; print(load_config().sqlite_v1_path)")
$pgBackup = Join-Path $backupDir "postgres.dump"
$sqliteBackup = Join-Path $backupDir "todo.db"

pg_dump --format=custom --file=$pgBackup $env:DATABASE_URL
if ($LASTEXITCODE -ne 0) { throw "BLOCKED_BACKUP_FAILED: pg_dump failed" }
pg_restore --list $pgBackup | Out-File (Join-Path $backupDir "postgres_restore_list.txt")
if ($LASTEXITCODE -ne 0) { throw "BLOCKED_BACKUP_FAILED: pg_restore --list failed" }

if (Test-Path -LiteralPath $sqlitePath) {
  Copy-Item -LiteralPath $sqlitePath -Destination $sqliteBackup -Force
}
```

### Restore

Stop the Flet process first. Then:

```powershell
pg_restore --clean --if-exists --no-owner --no-privileges --dbname=$env:DATABASE_URL $pgBackup
if ($LASTEXITCODE -ne 0) { throw "RESTORE_FAILED: PostgreSQL restore failed" }

if (Test-Path -LiteralPath $sqliteBackup) {
  Copy-Item -LiteralPath $sqliteBackup -Destination $sqlitePath -Force
}
```

Final report must include backup path, restore status, and whether DB state was restored after mutations.

## Preflight

```powershell
cd C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian
.\venv\Scripts\python.exe -m py_compile main.py database.py app\ui\calendar_view.py app\services\*.py app\importers\*.py app\exporters\*.py
.\venv\Scripts\python.exe -m pytest -q
```

If full pytest requires unavailable external DB fixtures, run the targeted service tests and report skipped blockers:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_calendar_view_service.py tests\test_calendar_import_service.py tests\test_task_service.py tests\test_notes_service.py tests\test_export_service.py -q
```

## Start App

Tier 2 phải tự chạy app bằng venv để đọc stdout/stderr. Lệnh trực tiếp tương đương:

```powershell
cd C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian
.\venv\Scripts\flet.exe run --web main.py
```

Khi cần port ổn định và log file cho QA, dùng command dưới đây:

```powershell
$stdout = "agent_workflow_doc\tier2_task_specs\flet_${runId}_stdout.log"
$stderr = "agent_workflow_doc\tier2_task_specs\flet_${runId}_stderr.log"
$app = Start-Process -FilePath ".\venv\Scripts\flet.exe" -ArgumentList @("run","--web","--port","8550","main.py") -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 8
Invoke-WebRequest http://127.0.0.1:8550 -UseBasicParsing
Get-Content $stdout -Tail 80
Get-Content $stderr -Tail 80
```

## Full System QA Matrix

Record `PASS/FAIL/SKIP/BLOCKED_BACKUP_FAILED/RESTORE_FAILED` for every TC.

### Group A — Startup, Layout, Navigation

- TC01: App loads at `http://127.0.0.1:8550` without traceback.
- TC02: Tabs render: `CHI TIẾT NGÀY`, `LỊCH THÁNG`, `GHI CHÚ`.
- TC03: Settings icon opens settings dialog; close without saving.
- TC04: Refresh/reload page; app returns to a safe usable state.

### Group B — Calendar Continuous View

- TC05: First calendar viewport starts at current month/year.
- TC06: Main date cell click switches to day detail and selected day is correct.
- TC07: Return to calendar; `Hôm nay` remains responsive and shows current month.
- TC08: Mini-calendar day click updates selected/visible month.
- TC09: Mini-calendar prev/next arrows update sidebar/main calendar coherently.
- TC10: Source checkbox toggle hides/shows source events.
- TC11: Refresh icon reloads sources/events without control lockup.
- TC12: Source manager opens from source name; close without saving.
- TC13: Add new source flow render; cancel without choosing file unless mutation case is intended.

### Group C — Day Detail

- TC14: Day detail renders fixed schedule column and task area.
- TC15: Day previous/next arrows update the day.
- TC16: `VỀ HÔM NAY` updates day detail to current date.
- TC17: Add task mutation: create `<runId>_task`, verify visible, edit, complete/uncomplete, delete or leave for restore.
- TC18: Imported event cancel/delete mutation if safe: toggle user-cancelled and verify UI, then rely on DB restore.

### Group D — Notes

- TC19: Notes tab renders note cards and sort dropdown.
- TC20: Quick add note mutation: create `<runId>_quick_note`.
- TC21: Add/edit note dialog mutation: title/body/priority/checklist.
- TC22: Pin/archive/delete note mutation; verify UI state.
- TC23: Sort by title/updated does not crash and layout remains usable.

### Group E — Import/Export

- TC24: Export JSON button opens export options; copy/export path tested only if safe.
- TC25: ICS import with fixture `LichThi-QLDT-20252.ics` after backup; verify source/version/events and parsed exam dates.
- TC26: Excel import with fixture `LichThi.xlsx` after backup; verify source/version/events and parsed exam dates.
- TC27: Invalid file type/import failure is surfaced clearly.

### Group F — Backup/Restore App Feature

- TC28: If in-app backup/restore UI exists, open render-only.
- TC29: Do not run app-level restore unless explicitly part of QA and DB backup is already made.

### Group G — Visual QA

- TC30: Desktop viewport around `1280x900`.
- TC31: Narrow viewport around `390x844`; record if mobile is unsupported.
- TC32: Verify no severe text overlap, invisible buttons, or clipped critical controls.

### Group H — Error And Recovery

- TC33: PostgreSQL unavailable scenario only if safe and approved; otherwise SKIP with reason.
- TC34: File picker cancel flows do not crash.
- TC35: Dialog open/close sequences do not leave app controls unresponsive.

## Playwright Deliverable

Create/update:

`test_playwright_microschedule_full_system_qa.py`

Automation requirements:

- Run after backup succeeds.
- Capture screenshots under `$artifactDir`.
- Automate TC01-TC11, TC14-TC17, TC19-TC23, TC30.
- Automate import tests TC25/TC26 only after backup and only with local fixtures `LichThi-QLDT-20252.ics` and `LichThi.xlsx`.
- Use timestamped names for all created data.
- Restore DB at the end, even if assertions fail. Use `try/finally`.
- If restore fails, exit non-zero and print `RESTORE_FAILED`.

Suggested Python structure:

```python
try:
    run_preflight_checks()
    run_ui_tests()
finally:
    stop_app()
    restore_postgres_and_sqlite()
```

Because Flet often renders canvas-heavy UI, Playwright may need coordinate clicks plus screenshots. Prefer accessible selectors when available; otherwise document coordinates and screenshot evidence.

## Google MCP Usage Rule

Use Google Drive/Docs/Sheets MCP when:

- User provides a Google Doc/Sheet test plan.
- QA evidence must be written into a Google Doc/Sheet.
- A fixture file is stored in Drive and connector access is available.

Report connector evidence:

- File title/id.
- Ranges/pages read or written.
- Whether data was exported locally.
- Any MCP failure and fallback.

## Final Report Format

Return one Markdown report:

| TC | Status | Evidence | Notes |
|---|---|---|---|
| TC01 | PASS/FAIL/SKIP | screenshot/log/path | ... |

Required sections:

- `run_id`.
- Browser/viewport.
- App URL.
- `safeDbUrl` with password redacted.
- Backup path and verification result.
- Restore result for PostgreSQL and SQLite.
- Preflight command results.
- Manual Browser/Chrome DevTools result table.
- Playwright script path and command.
- Artifact directory.
- DB mutations performed.
- Bugs requiring Tier 1 action.
- Google MCP usage.
- Skipped destructive cases and exact reason.

Không kết thúc QA nếu restore chưa chạy. Nếu restore fail, báo ngay và không che giấu.

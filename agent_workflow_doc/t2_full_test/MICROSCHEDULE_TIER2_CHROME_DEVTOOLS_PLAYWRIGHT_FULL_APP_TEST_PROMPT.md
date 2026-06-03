# Tier 2 Prompt — microSchedule Full-App Verification With Browser/Playwright

Bạn là Model Tier 2 phụ trách **thực thi** QA cho `microSchedule`. Không thiết kế lại scope. Không sửa app code để test pass. Được phép tạo/cập nhật script Playwright phục vụ test, nhưng phải báo rõ script path và evidence.

## Context

- Repo: `C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian`
- App framework: Flet desktop/web, Python.
- Local verify URL: `http://127.0.0.1:8550`
- Python venv bắt buộc: `C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian\venv`
- PostgreSQL DB được đọc từ `.env` qua `app.config.load_config()`.
- Legacy SQLite DB path mặc định: `C:\Users\os\Desktop\Tools\VC_microSchedule_home\todo.db`
- Import fixtures bắt buộc cho TC import:
  - ICS exam fixture: `C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian\LichThi-QLDT-20252.ics`
  - Excel exam fixture: `C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian\LichThi.xlsx`
- Máy có `psql`, `pg_dump`, `pg_restore`; dùng chúng để backup/restore DB.
- Nếu cần đọc artifact Google Docs/Sheets/Drive do user đưa, dùng Google Drive MCP/Google Sheets MCP trước; không tự tải thủ công khi connector có thể đọc được.

## Non-Negotiable DB Safety

Tier 2 được phép chạy QA có mutate CSDL, nhưng **chỉ sau khi backup thành công**. Cuối run phải restore CSDL về đúng snapshot backup, kể cả test fail/provider fail/browser fail.

Không được chạy destructive test nếu chưa có backup verified.

### 1. Resolve DB URLs And Backup Paths

```powershell
cd C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian
$runId = "MICROSCHEDULE_QA_" + (Get-Date -Format "yyyyMMdd_HHmmss")
$backupDir = "agent_workflow_doc\tier2_task_specs\db_backups\$runId"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$env:DATABASE_URL = (& .\venv\Scripts\python.exe -c "from app.config import load_config; print(load_config().database_url)")
$sqlitePath = (& .\venv\Scripts\python.exe -c "from app.config import load_config; print(load_config().sqlite_v1_path)")
$pgBackup = Join-Path $backupDir "postgres.dump"
$sqliteBackup = Join-Path $backupDir "todo.db"
```

### 2. Backup PostgreSQL And SQLite

```powershell
pg_dump --format=custom --file=$pgBackup $env:DATABASE_URL
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed; stop QA." }

pg_restore --list $pgBackup | Select-Object -First 20
if ($LASTEXITCODE -ne 0) { throw "pg_restore --list failed; backup not verified." }

if (Test-Path -LiteralPath $sqlitePath) {
  Copy-Item -LiteralPath $sqlitePath -Destination $sqliteBackup -Force
}
```

### 3. Mandatory Restore At End

Before restore, stop the Flet app process that Tier 2 started.

```powershell
pg_restore --clean --if-exists --no-owner --no-privileges --dbname=$env:DATABASE_URL $pgBackup
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL restore failed. Report immediately." }

if (Test-Path -LiteralPath $sqliteBackup) {
  Copy-Item -LiteralPath $sqliteBackup -Destination $sqlitePath -Force
}
```

Final report must state:

- Backup path.
- Restore command result.
- Whether PostgreSQL and SQLite were both restored.
- Any DB mutations performed during QA.

## Preflight

```powershell
cd C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian
.\venv\Scripts\python.exe -m py_compile main.py app\ui\calendar_view.py app\services\calendar_view_service.py app\services\calendar_day_service.py app\services\task_service.py app\services\notes_service.py
.\venv\Scripts\python.exe -m pytest tests\test_calendar_view_service.py tests\test_calendar_import_service.py tests\test_task_service.py tests\test_notes_service.py -q
```

If Playwright is not installed in `venv`, install it only after backup succeeds:

```powershell
.\venv\Scripts\python.exe -m pip install playwright
```

## Start App With Logs

Tier 2 phải tự chạy app bằng venv để đọc log. Lệnh trực tiếp tương đương:

```powershell
cd C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian
.\venv\Scripts\flet.exe run --web main.py
```

Khi cần port ổn định và log file cho QA, dùng command dưới đây:

```powershell
cd C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian
$stdout = "agent_workflow_doc\tier2_task_specs\flet_${runId}_stdout.log"
$stderr = "agent_workflow_doc\tier2_task_specs\flet_${runId}_stderr.log"
$app = Start-Process -FilePath ".\venv\Scripts\flet.exe" -ArgumentList @("run","--web","--port","8550","main.py") -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 8
Invoke-WebRequest http://127.0.0.1:8550 -UseBasicParsing
Get-Content $stderr -Tail 80
```

If port `8550` is busy, verify it is the intended app and capture logs. Otherwise stop the stale process safely and start your own.

## Required Manual Verification

Use Browser/Chrome DevTools MCP first. Because Flet web can be canvas-heavy, use screenshots plus server logs as primary evidence when DOM accessibility is sparse.

### A. Startup And Main Navigation

1. Open `http://127.0.0.1:8550`.
2. Verify default selected tab is `LỊCH THÁNG`.
3. Verify app title, settings icon, tabs: `CHI TIẾT NGÀY`, `LỊCH THÁNG`, `GHI CHÚ`.
4. Verify no Python traceback or Flet crash in logs.

### B. Calendar Regression Focus

1. Verify continuous calendar first viewport starts at current month/year, not an old year.
2. Click a normal date cell in the main calendar.
3. Expected: app switches to `CHI TIẾT NGÀY`, header shows selected day/month, and buttons remain responsive.
4. Return to `LỊCH THÁNG`.
5. Click `Hôm nay`.
6. Expected: calendar remains or returns to current month, no stuck/dead controls.
7. Click a mini-calendar date cell.
8. Expected: mini-calendar selected state and main calendar visible month update coherently.
9. Click mini-calendar prev/next arrows.
10. Expected: sidebar/main calendar remain in sync, no modal opens unexpectedly, no handler lockup.

### C. Source Visibility And Refresh

1. Toggle one calendar source checkbox off/on.
2. Click refresh icon.
3. Expected: events refresh without losing checkbox state incorrectly.
4. If testing source import/update, this is DB-mutating and must happen only after backup; record exactly what source was added/updated.

### D. Day Detail Smoke

1. From calendar date click, verify fixed schedule column, overdue/today task sections, import/export/add task buttons.
2. Click day previous/next arrows and `VỀ HÔM NAY`.
3. Expected: day header changes correctly and no calendar controls become unresponsive.

### E. Notes Smoke

1. Open `GHI CHÚ`.
2. Verify quick note input, sort dropdown, add note button, note cards.
3. Mutating cases are allowed after backup: create a temporary note named `<runId>_note`, add checklist item, edit, archive/delete.
4. Restore DB at end.

### F. Import Fixture Smoke

Run these only after backup succeeds. They are DB-mutating and must be reverted by final DB restore.

1. Import `LichThi-QLDT-20252.ics`.
2. Expected: a calendar source/version is created or updated, parsed exam events appear on corresponding dates, and logs do not show parser traceback.
3. Import `LichThi.xlsx`.
4. Expected: parsed exam events appear with exam-style labels/source metadata.
5. Record source names, parsed counts, visible dates tested, and any parser warnings.

## Required Playwright Deliverable

Create or update a script under repo root, for example:

`test_playwright_microschedule_full_app.py`

The script must:

- Start from `http://127.0.0.1:8550`.
- Use screenshots for Flet canvas verification.
- Exercise TC Startup, Calendar date cell, `Hôm nay`, mini calendar, source toggle, day arrows, notes smoke, and import fixtures `LichThi-QLDT-20252.ics` + `LichThi.xlsx`.
- Use `runId` for any created data.
- Avoid assertions that depend on global note/task counts.
- Save evidence under `agent_workflow_doc\tier2_task_specs\qa_artifacts\<runId>\`.
- Restore DB after completion by calling the mandatory restore commands, or clearly instruct the operator to run restore before ending the session.

Standard command:

```powershell
cd C:\Users\os\Desktop\old_prj\VC_QuanLyThoiGian
.\venv\Scripts\python.exe test_playwright_microschedule_full_app.py
```

## Final Report Format

Return one Markdown report:

| TC | Status | Evidence | Notes |
|---|---|---|---|
| CAL-01 | PASS/FAIL/SKIP | screenshot/log/script line | ... |

Required sections:

- `run_id`.
- Browser, viewport, app URL.
- PostgreSQL safe DB URL with password redacted.
- Backup paths and restore status.
- Preflight commands and results.
- Manual Browser/Chrome DevTools result table.
- Playwright command, script path, artifact directory.
- Calendar regression evidence: date cell, `Hôm nay`, mini calendar.
- DB mutations performed during test.
- Bugs requiring Tier 1 action.
- Google MCP usage, if any: file/doc/sheet read, connector evidence, reason.
- Skipped cases and exact reason.

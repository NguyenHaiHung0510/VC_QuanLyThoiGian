# microSchedule 📅

Ứng dụng quản lý lịch học + danh sách việc cần làm, được tối ưu hóa cho ôn tập và kế hoạch thời gian.

## Trạng thái hiện tại

Repo hiện đang ở trạng thái chuyển tiếp từ v1 sang v2:

| Track | Trạng thái | File chính |
|---|---|---|
| v1 desktop app | Vẫn là runtime chính khi chạy `python main.py` | `main.py`, `database.py`, SQLite `todo.db` |
| v2 foundation | Đã có trong repo | `app/config.py`, `app/db`, `app/migration`, `app/importers`, `app/services`, `app/exporters` |
| v2 UI | Chưa tích hợp runtime chính | Notes UI và continuous calendar còn là workstream sau |
| v2 AI tools | Chưa implement | Chỉ mới khóa contract safety/audit trong docs/schema |

Nếu cần trạng thái v2 mới nhất, đọc [docs/V2_CURRENT_STATE.md](docs/V2_CURRENT_STATE.md), [docs/V2_DECISION_BRIEF.md](docs/V2_DECISION_BRIEF.md), và [app/db/schema.sql](app/db/schema.sql). Các phần mô tả `main.py`/`database.py` bên dưới là tài liệu cho v1 runtime hiện tại.

## 🎯 Giới thiệu

**microSchedule** là một desktop app standalone giúp bạn:
- 📅 **Quản lý lịch học cố định** (nhập từ Google Calendar, Outlook, hoặc file Excel)
- ✅ **Tổ chức danh sách việc cần làm** (tasks + subtasks)
- 🎯 **Phân ưu tiên công việc** (5 mức độ từ "Optional" đến "Đặc biệt nguy hiểm")
- 📊 **Xuất dữ liệu JSON** cho AI ôn tập/lập kế hoạch
- 💾 **Sao lưu tự động** (15 backup files, mỗi 2 giờ)

**Đặc biệt**: Được custom để dùng với các AI tools (ChatGPT, Claude, etc.) để tạo kế hoạch ôn thi tối ưu.

---

## ✨ Tính năng chính

### 1. Import Lịch (ICS + Excel)
- **ICS files**: Import từ Google Calendar, Outlook (RFC 5545 compliant)
- **Excel files**: Import lịch thi từ nhà trường (smart column detection)
- Xử lý timezone, format ngày đa dạng, tự động tính thời gian kết thúc

### 2. Quản lý Tasks
- Tạo task với deadline, ưu tiên, và ghi chú
- Phân rã task thành subtasks (track progress)
- Đánh dấu hoàn thành, hiển thị tiến độ (X/Y subtasks)
- Context note tự động (OVERDUE hay UPCOMING)

### 3. Giao diện đa view
- **Day View**: Hiển thị schedule + tasks cho ngày cụ thể
- **Month View**: Calendar grid với legend
- **Settings**: Quản lý locations, priorities, durations

### 4. Xuất & Sao lưu
- **Export JSON**: Copy to clipboard hoặc save file
- **Structured data**: Kèm metadata, schedule, tasks, subtasks, progress
- **Smart backup**: Tự động mỗi 2 giờ, giữ 15 file mới nhất

### 5. Hệ thống Ưu tiên
5 mức độ tùy chỉnh:
- ✅ Optional (xám)
- ✅ Nên làm (xanh)
- ✅ Phải làm (vàng)
- ✅ Bỏ là nhót 💀 (cam)
- ✅ ĐẶC BIỆT NGUY HIỂM 🆘 (đỏ)

Mỗi mức độ có icon + color riêng để dễ phân biệt.

---

## 🛠️ Tech Stack

| Layer | Công nghệ |
|-------|----------|
| **Frontend** | Flet (Python UI framework) |
| **Backend** | Python 3.8+ |
| **Database v1 runtime** | SQLite local file |
| **Database v2 foundation** | PostgreSQL `microschedule_v2` |
| **Backup v1** | File system copy |
| **Backup v2** | `pg_dump -Fc` qua `app/services/backup_service.py` |
| **Packaging** | PyInstaller (→ .exe) |
| **Import** | ICS (RFC 5545), openpyxl (Excel) |
| **Export v1** | JSON native |
| **Export v2** | Markdown default + JSON optional qua `PlannerExportDTO` |

---

## 📦 Cài đặt

### Yêu cầu hệ thống
- Windows/Mac/Linux
- Python 3.8+
- ~50MB disk space (app + data)

### Bước 1: Clone hoặc Download
```bash
# Clone từ repo (nếu có)
git clone <repo-url>
cd VC_QuanLyThoiGian

# Hoặc download zip
# Giải nén vào một thư mục
```

### Bước 2: Tạo virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### Bước 3: Cài đặt dependencies
```bash
pip install -r requirements.txt
```

**requirements.txt**:
```
flet
schedule
openpyxl
pyinstaller
```

### Bước 4: Tạo thư mục dữ liệu v1
```bash
# Database sẽ được tạo tại:
# C:\Users\<username>\Desktop\Tools\VC_microSchedule_home

# Nếu cần đổi path, chỉnh sửa database.py:
DATA_DIR = r"C:\Users\os\Desktop\Tools\VC_microSchedule_home"
```

### Bước 5: Chạy app
```bash
python main.py
```

App sẽ mở cửa sổ Flet, hiển thị giao diện chính.

### Kiểm tra v2 foundation

V2 foundation dùng PostgreSQL và cấu hình qua `.env`. Không commit `.env`; chỉ dùng `.env.example` làm mẫu.

```bash
python -m pytest
python app/migration/analyze_v1_sqlite.py
python app/migration/migrate_sqlite_to_postgres.py --dry-run
```

Chỉ chạy `--apply` khi đã xác nhận target là database v2 dev `microschedule_v2`.

---

## 🚀 Sử dụng

### Quy trình cơ bản

#### 1. Import Lịch
```
Menu → Import Schedule
  ↓
Chọn file (.ics hoặc .xlsx)
  ↓
App parse + hiển thị thành công (success message)
  ↓
Xem lịch ở Day View hoặc Month View
```

**ICS Files**: Export từ Google Calendar
- Google Calendar → Settings → Calendar → Export
- Save file `.ics`
- Import vào microSchedule

**Excel Files**: Chuẩn bị từ nhà trường
- File phải có cột "Môn" (hoặc "Học phần") + "Ngày"
- Import vào microSchedule

#### 2. Tạo Tasks
```
[Day View] → Click [+ Add Task]
  ↓
Điền: Title, Priority, Due date, Note
  ↓
Thêm subtasks nếu muốn
  ↓
Save → Task hiển thị trong list
```

#### 3. Đánh dấu Hoàn thành
```
[Day View/Month View] → Click ✓ button trên card
  ↓
Task đánh dấu hoàn thành
  ↓
Progress tự động cập nhật
```

#### 4. Xuất dữ liệu cho AI
```
Menu → Export Data → JSON
  ↓
Dialog: "Lưu vào File" hoặc "Copy"
  ↓
Chọn option
  ↓
JSON data copy to clipboard (hoặc save file)
  ↓
Paste vào ChatGPT/Claude → AI tạo kế hoạch ôn thi
```

#### 5. Xem Lịch
```
[Month View] → Xem calendar grid tháng
              → Click ngày để chuyển sang Day View

[Day View] → Xem schedule + tasks cho ngày cụ thể
          → [< Prev] [Today] [Next >] để navigate
```

---

## 📊 Cấu trúc dự án

```
VC_QuanLyThoiGian/
├── main.py                 # Entry point, UI layer
├── database.py             # v1 SQLite data access layer, import logic
├── app/                    # v2 foundation modules
│   ├── config.py           # .env/config safety helpers
│   ├── db/                 # PostgreSQL schema/connection helpers
│   ├── migration/          # SQLite v1 -> PostgreSQL v2 tools
│   ├── importers/          # ICS/Excel parser modules
│   ├── services/           # import/export/backup services
│   └── exporters/          # PlannerExportDTO Markdown/JSON renderers
├── tests/                  # v2 service tests
├── requirements.txt        # Dependencies
├── build.bat               # Build script
├── microSchedule.spec      # PyInstaller config
│
├── docs/                   # 📚 Tài liệu (chi tiết)
│   ├── SYSTEM_ARCHITECTURE.md   # Kiến trúc tổng thể
│   ├── IMPORT_GUIDE.md          # ICS/Excel parser
│   ├── EXPORT_GUIDE.md          # v1 JSON + v2 Markdown/JSON DTO
│   ├── UI_GUIDE.md              # Flet components
│   └── DATABASE_SCHEMA.md       # Table definitions
│
├── build/                  # Build artifacts (PyInstaller)
│   └── microSchedule/      # Output EXE
│
└── venv/                   # Virtual environment
```

### File chính

#### `main.py` (~1500 lines)
- Giao diện Flet (UI layer)
- State management (current_date, APP_CONFIG)
- Event handlers (navigation, import/export, refresh)
- Load day/month views
- Theme & color system

#### `database.py` (~700 lines)
- SQLite operations (CRUD)
- ICS parser (RFC 5545)
- Excel parser (smart column detection)
- JSON export
- Auto-backup system
- Settings management

---

## 📖 Tài liệu chi tiết

Các tài liệu trong `/docs/` cung cấp thông tin sâu:

| Tài liệu | Nội dung |
|---------|---------|
| [V2_CURRENT_STATE.md](docs/V2_CURRENT_STATE.md) | Trạng thái v1/v2 hiện tại, nguồn sự thật và việc còn pending |
| [V2_DECISION_BRIEF.md](docs/V2_DECISION_BRIEF.md) | Quyết định kiến trúc v2 đã khóa |
| [V2_MIGRATION_REPORT.md](docs/V2_MIGRATION_REPORT.md) | Kết quả migration/import/backup v2 đã chạy |
| [V2_BACKUP_RESTORE.md](docs/V2_BACKUP_RESTORE.md) | Backup/restore PostgreSQL v2 |
| [SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | Kiến trúc 3-layer, luồng dữ liệu, component overview |
| [IMPORT_GUIDE.md](docs/IMPORT_GUIDE.md) | ICS/Excel parser, RFC 5545, ví dụ, troubleshooting |
| [EXPORT_GUIDE.md](docs/EXPORT_GUIDE.md) | JSON schema, AI integration, use cases |
| [UI_GUIDE.md](docs/UI_GUIDE.md) | Flet components, layout, patterns, handlers |
| [DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | Tables, relationships, migrations, performance |

**👉 Nên đọc từng tài liệu khi cần implement features mới hoặc fix bugs.**

---

## 🔧 Cấu hình

### Đổi đường dẫn Database

Mở `database.py`, tìm:
```python
DATA_DIR = r"C:\Users\os\Desktop\Tools\VC_microSchedule_home"
```

Đổi thành đường dẫn của bạn:
```python
DATA_DIR = r"C:\path\to\your\data\folder"
```

### Đổi Default Settings

Mở `database.py`, tìm hàm `_setup_defaults()`:

```python
def _setup_defaults(cur):
    default_locs = [
        {"name": "A2", "icon": "School"},
        {"name": "Học Online", "icon": "Online"},
        # ...
    ]

    default_prios = [
        {"name": "Optional", "label": "Optional", "color": "Grey", "icon": "Low"},
        # ...
    ]
    # Chỉnh sửa theo nhu cầu
```

### Đổi Theme Colors

Mở `main.py`, tìm:
```python
THEME = {
    "primary": ft.Colors.PINK_600,
    "accent": ft.Colors.TEAL_600,
    # ...
}
```

Đổi colors theo Flet palette.

---

## 🐛 Troubleshooting

### Import không hoạt động
- Kiểm tra file format (ICS hoặc Excel)
- ICS: Đảm bảo có DTSTART + SUMMARY
- Excel: Đảm bảo có cột "Môn" + "Ngày"
- Xem chi tiết: [IMPORT_GUIDE.md](docs/IMPORT_GUIDE.md#troubleshooting)

### Export JSON không hoạt động
- Check clipboard (có thể bị lock bởi app khác)
- Thử "Save to file" thay vì "Copy"
- Xem chi tiết: [EXPORT_GUIDE.md](docs/EXPORT_GUIDE.md#troubleshooting)

### App bị crash
- Check Python version (phải 3.8+)
- Reinstall dependencies: `pip install -r requirements.txt`
- Xoá folder `venv` + tạo lại fresh

### Database corrupted
- Restore từ backup: `backups/todo_backup_*.db`
- Copy file backup vào `todo.db`
- Restart app

---

## 📝 Dữ liệu mẫu

### Schedule Event (từ ICS)
```json
{
  "subject": "Math Midterm",
  "time_start": "07:00",
  "time_end": "09:00",
  "location": "Room A2",
  "date_str": "2025-05-26"
}
```

### Task với Subtasks
```json
{
  "id": 1,
  "title": "Review Chapter 3-5",
  "priority": "Phải làm",
  "date_str": "2025-05-26",
  "subtasks_list": [
    {"content": "Read pages 45-60", "is_completed": 1},
    {"content": "Do problems 1-10", "is_completed": 0}
  ],
  "context_note": "UPCOMING. Tiến độ: 1/2"
}
```

---

## 🤖 Dùng với AI

### ChatGPT/Claude Prompt Template

```markdown
# Dữ liệu ôn thi của tôi

[Paste JSON export here]

## Yêu cầu:
1. Phân tích tasks overdue, urgent
2. Tạo lịch ôn tập hợp lý (2-3h/ngày)
3. Prioritize theo ưu tiên
4. Suggest study order (avoid conflicts)

## Format trả lời:
- Bullet points
- Có thời gian cụ thể
- Để trống time slots đã có lịch học
```

---

## ⚠️ Giới hạn & Vấn đề hiện tại

### Known Issues
1. **Hardcoded path**: Database path là machine-specific (cần config thủ công)
2. **Tight coupling**: UI + logic không tách rời (khó maintain)
3. **No validation**: Không check input user
4. **No logging**: Khó debug khi có lỗi
5. **No multi-user**: Chỉ support 1 user/machine

### Future Enhancements
- [ ] Configurable database path
- [ ] Settings GUI (thay vì code edit)
- [ ] Dark mode + responsive UI
- [ ] Real-time sync (cloud backup)
- [ ] Recurring events (RRULE support)
- [ ] Time block visualization
- [ ] Mobile app (sync with desktop)
- [ ] Search + filter tasks

---

## 📜 License & Author

**Author**: Bạn (tên hoặc GitHub account)

**License**: [Chọn: MIT, GPL, Personal Use, etc.]

---

## 📞 Support & Feedback

- 🐛 **Báo lỗi**: [Issues section nếu có GitHub repo]
- 💡 **Suggest features**: [Discussion nếu có]
- 📧 **Contact**: [Your email hoặc contact info]

---

## 🎓 Học hỏi từ dự án này

Dự án là ví dụ thực tế của:
- ✅ Desktop app (Flet)
- ✅ SQLite database
- ✅ File parsing (ICS, Excel)
- ✅ JSON export/import
- ✅ Auto backup system
- ✅ Structured data architecture

**Code có thể dùng làm tham khảo để:**
- Build desktop app tương tự
- Parse ICS files
- Integrate với AI systems

---

## 🚀 Bắt đầu

**Tóm tắt quick start:**

```bash
# 1. Setup
git clone <repo>
cd VC_QuanLyThoiGian
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. Chạy
python main.py

# 3. Import dữ liệu
# Menu → Import Schedule → chọn ICS hoặc Excel

# 4. Tạo tasks
# Day View → Add Task

# 5. Export cho AI
# Menu → Export Data → Copy or Save

# 6. Dùng với AI
# Paste JSON vào ChatGPT → AI tạo kế hoạch
```

**Đọc thêm**: Xem `/docs/` để hiểu chi tiết từng phần.

---

## 📅 Lịch sử cập nhật

| Ngày | Ghi chú |
|------|---------|
| 25/05/2026 | Viết tài liệu hoàn chỉnh (README + 5 docs) |
| 25/05/2026 | Tạo thư mục docs/ |
| (Trước đó) | Development (no docs) |

---

**Happy planning! 🎯📅**

*Nếu có câu hỏi hoặc cần giúp, hãy check `/docs/` trước.*

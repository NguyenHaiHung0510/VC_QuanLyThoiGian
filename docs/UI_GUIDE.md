# UI_GUIDE.md - Flet Component Breakdown

Tài liệu này mô tả cấu trúc UI của microSchedule, các component Flet được sử dụng, và cách thức layout/interaction.

## 0. Trạng Thái UI

Tài liệu này mô tả **UI v1 hiện tại** trong `main.py`. Sau khi v2 foundation được merge, các service PostgreSQL/import/export/backup đã có trong `app/`, nhưng runtime Flet chính chưa được refactor sang v2.

Không coi các tính năng sau là đã có trong UI nếu chưa có workstream riêng merge:

- Notes tab v2 CRUD.
- Continuous multi-week calendar thay month grid.
- Sidebar source filters đọc `calendar_sources`.
- AI agent/chat/tools UI.

Khi implement WS5/WS6/WS7, Tier 2 phải đọc `docs/V2_CURRENT_STATE.md`, `docs/V2_DECISION_BRIEF.md`, và contract/schema v2 trước; không tự đổi schema/API để tiện UI.

## 1. Architecture Overview

```
main(page: ft.Page)
    ├── Page Config
    │   ├── title, theme_mode, window_size
    │   └── overlay (file_picker, date_picker)
    │
    ├── State Management
    │   ├── current_date
    │   ├── current_month_view
    │   └── APP_CONFIG (settings)
    │
    ├── Helper Functions
    │   ├── get_date_str(), format_date_vn()
    │   ├── get_prio_config(), calculate_end_time()
    │   └── ...
    │
    ├── UI Components (Refs)
    │   ├── App Bar
    │   ├── Main Content Area
    │   │   ├── tabs_control
    │   │   │   ├── Tab 1: Day View
    │   │   │   ├── Tab 2: Month View
    │   │   │   └── Tab 3: Settings
    │   │   └── containers (tasks, schedule, calendar_grid)
    │   └── Footer
    │
    └── Main Loop (page.run())
```

## 2. Theme & Color System

### 2.1 Theme Dictionary

```python
THEME = {
    "primary": ft.Colors.PINK_600,
    "primary_light": ft.Colors.PINK_50,
    "accent": ft.Colors.TEAL_600,
    "text_dark": ft.Colors.GREY_900,
    "today_bg": ft.Colors.RED_50,
    "today_border": ft.Colors.RED_400,
}
```

### 2.2 Icon Mapping

```python
ICON_MAP = {
    # Locations
    "School": ft.Icons.SCHOOL,
    "Home": ft.Icons.HOME,
    "Library": ft.Icons.LOCAL_LIBRARY,

    # Priorities
    "Low": ft.Icons.LOW_PRIORITY,
    "High": ft.Icons.PRIORITY_HIGH,
    "Danger": ft.Icons.DANGEROUS,

    # Misc
    "Check": ft.Icons.CHECK_CIRCLE_OUTLINE,
    "Star": ft.Icons.STAR,
    "Flag": ft.Icons.FLAG,
}
```

### 2.3 Color Mapping (Priority Colors)

```python
COLOR_MAP = {
    "Grey": ft.Colors.BLUE_GREY,
    "Green": ft.Colors.GREEN,
    "Blue": ft.Colors.BLUE,
    "Amber": ft.Colors.AMBER_800,
    "Orange": ft.Colors.DEEP_ORANGE,
    "Red": ft.Colors.RED_900,
    "Purple": ft.Colors.PURPLE,
    "Teal": ft.Colors.TEAL,
    "Pink": ft.Colors.PINK,
}
```

---

## 3. Component Tree (Detailed)

### 3.1 Page Configuration

```python
def main(page: ft.Page):
    # Basic properties
    page.title = APP_CONFIG.get("app_title", "microSchedule")
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1400
    page.window_height = 900
    page.padding = 0  # No padding on main page

    # Overlays (hidden until needed)
    file_picker = ft.FilePicker()
    date_picker = ft.DatePicker(
        first_date=datetime(2023, 1, 1),
        last_date=datetime(2030, 12, 31),
    )
    page.overlay.extend([file_picker, date_picker])
```

### 3.2 UI References (Global State)

```python
# Labels
lbl_current_date = ft.Text(size=20, weight="bold", color=THEME["primary"])
    # Displays: "Thứ 2, 25/05"

lbl_month_title = ft.Text(size=24, weight="bold", color=THEME["primary"])
    # Displays: "May 2025"

app_bar_title = ft.Text(page.title, color="white", weight="bold")
    # Displays: "microSchedule"

# Containers (populated by load_*_view functions)
container_tasks = ft.Column()
    # Dynamic: list of task cards

container_schedule = ft.Column()
    # Dynamic: list of schedule event cards

container_calendar_grid = ft.Column(spacing=2)
    # Dynamic: calendar grid rows

# Tabs
tabs_control = ft.Tabs()
    # Holds 3 tabs: Day, Month, Settings
```

---

## 4. Main Layout (Top-Down)

```
┌─ AppBar (Top) ─────────────────────────────────────────┐
│  [Menu] microSchedule                    [?] [Settings] │
└─────────────────────────────────────────────────────────┘

┌─ Content Area ──────────────────────────────────────────┐
│                                                          │
│  Tabs:  [📅 Day]  [📊 Month]  [⚙️ Settings]            │
│                                                          │
│  ┌──── Tab Content ──────────────────────────────────┐  │
│  │                                                   │  │
│  │  Current Date:  Thứ 2, 25/05                     │  │
│  │                                                   │  │
│  │  [Month/Day Navigation]                          │  │
│  │                                                   │  │
│  │  Content (varies by tab):                        │  │
│  │  - Day Tab: Task list + Schedule for day        │  │
│  │  - Month Tab: Calendar grid + Legend            │  │
│  │  - Settings Tab: Config options                  │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Tab Views (Detailed)

### 5.1 Day View Tab

**Purpose**: Show tasks + schedule for a specific day

**Layout**:
```
┌─ Day View ─────────────────────┐
│  Date: Thứ 2, 25/05             │
│  [< Prev] [Today] [Next >]      │
│                                  │
│  📅 Schedule Events:             │
│  ┌──────────────────────────┐   │
│  │ 07:00-09:00 Math Midterm │   │
│  │ Room A2, Priority: High  │   │
│  │ [✓] [✎] [✗]             │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │ 13:00-14:30 Physics      │   │
│  │ Online                   │   │
│  │ [✓] [✎] [✗]             │   │
│  └──────────────────────────┘   │
│                                  │
│  ✅ Tasks:                       │
│  ┌──────────────────────────┐   │
│  │ ☑ Review Chapter 3-5     │   │
│  │ Priority: Phải làm       │   │
│  │ Progress: 1/2 subtasks   │   │
│  │ [✓] [✎] [✗]             │   │
│  └──────────────────────────┘   │
│                                  │
└────────────────────────────────┘
```

**Components**:
- `lbl_current_date`: Text showing current date
- Navigation buttons: Previous, Today, Next
- `container_schedule`: List of schedule event cards
- `container_tasks`: List of task cards

**Load Function**: `load_day_view()`

### 5.2 Month View Tab

**Purpose**: Show calendar grid + task summary

**Layout**:
```
┌─ Month View ───────────────────────────┐
│  May 2025                               │
│  [< Prev Month] [Today] [Next Month >] │
│                                         │
│  ┌─────────────────────────────────┐  │
│  │ Mo Tu We Th Fr Sa Su            │  │
│  │  4  5  6  7  8  9 10            │  │
│  │ 11 12 13 14 15 16 17            │  │
│  │ 18 19 20 21 22 23 24            │  │
│  │ 25*26 27 28 29 30 31            │  │
│  │                                  │  │
│  │ * = Today (highlighted)          │  │
│  │ Bold number = has events         │  │
│  └─────────────────────────────────┘  │
│                                         │
│  Legend:                                │
│  ☰ = Schedule events                   │
│  ✓ = Tasks                             │
│  ⚠ = OVERDUE tasks                     │
│                                         │
└─────────────────────────────────────────┘
```

**Components**:
- `lbl_month_title`: Month/Year display
- Navigation buttons: Prev Month, Today, Next Month
- `container_calendar_grid`: Calendar grid (7 columns, N rows)
- Legend cards

**Load Function**: `load_month_view()`

### 5.3 Settings Tab

**Purpose**: Configure app settings, manage locations/priorities

**Placeholder Structure**:
```
┌─ Settings ─────────────────┐
│  🔧 Configuration          │
│                             │
│  Locations:                 │
│  + Add Location             │
│  - A2, A3, Thư viện, ...   │
│                             │
│  Priorities:                │
│  + Add Priority             │
│  - Optional, Nên làm, ...   │
│                             │
│  [Export Data]              │
│  [Import from ICS/Excel]    │
│  [Backup & Restore]         │
│                             │
└─────────────────────────────┘
```

---

## 6. Card Components

### 6.1 Schedule Event Card

```python
# Structure
ft.Card(
    content=ft.Container(
        content=ft.Column([
            # Header
            ft.Row([
                ft.Icon(location_icon),
                ft.Text(f"{time_start}-{time_end}", weight="bold"),
                ft.Text(location, size=10, color="grey"),
            ]),
            # Subject
            ft.Text(subject, size=14, weight="bold", color=THEME["primary"]),
            # Actions
            ft.Row([
                ft.IconButton(ft.Icons.CHECK, on_click=...),
                ft.IconButton(ft.Icons.EDIT, on_click=...),
                ft.IconButton(ft.Icons.DELETE, on_click=...),
            ]),
        ]),
        bgcolor=THEME["primary_light"],
        padding=10,
        border_radius=8,
    )
)
```

**Fields**:
- Icon: Based on location
- Time: time_start-time_end (e.g., "07:00-09:00")
- Subject: Event name
- Location: Where (Room/Online)
- Actions: Check (mark complete), Edit, Delete

### 6.2 Task Card

```python
# Structure
ft.Card(
    content=ft.Container(
        content=ft.Column([
            # Header with priority color
            ft.Row([
                ft.Icon(priority_icon, color=priority_color),
                ft.Text(title, weight="bold", size=14),
                ft.Text(f"Priority: {priority_label}", size=10),
            ]),
            # Progress
            ft.Text(f"Progress: {done}/{total} subtasks", size=10, color="grey"),
            # Context (OVERDUE/UPCOMING)
            ft.Text(context_note, size=10, color="red" if "OVERDUE" in context_note else "blue"),
            # Subtasks list
            *[
                ft.Row([
                    ft.Checkbox(value=sub["is_completed"]),
                    ft.Text(sub["content"]),
                ])
                for sub in subtasks
            ],
            # Actions
            ft.Row([
                ft.IconButton(ft.Icons.CHECK, on_click=...),
                ft.IconButton(ft.Icons.EDIT, on_click=...),
                ft.IconButton(ft.Icons.DELETE, on_click=...),
            ]),
        ]),
        bgcolor=priority_color if priority_color else ft.Colors.GREY_100,
        padding=10,
        border_radius=8,
    )
)
```

**Fields**:
- Icon + Priority: Color-coded
- Title: Task name
- Progress: X/Y subtasks complete
- Context: "OVERDUE" or "UPCOMING"
- Subtasks: Checkbox list
- Actions: Check, Edit, Delete

---

## 7. Helper Functions (UI Logic)

### 7.1 Date Formatting

```python
def format_date_vn(dt):
    """Convert datetime to Vietnamese format: 'Thứ 2, 25/05'"""
    weekday = dt.weekday()
    map_thu = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
    return f"{map_thu[weekday]}, {dt.strftime('%d/%m')}"

def get_date_str(dt):
    """Convert to ISO format: '2025-05-25'"""
    return dt.strftime("%Y-%m-%d")
```

### 7.2 Configuration Lookup

```python
def get_location_icon(loc_name):
    """Map location name to icon"""
    if not loc_name:
        return ft.Icons.EVENT
    for loc in APP_CONFIG["locations"]:
        if loc["name"].lower() in loc_name.lower():
            return ICON_MAP.get(loc["icon"], ft.Icons.LOCATION_ON)
    # Fallback: check keywords
    if "online" in loc_name.lower():
        return ft.Icons.VIDEOCAM
    if "home" in loc_name.lower() or "nhà" in loc_name.lower():
        return ft.Icons.HOME
    return ft.Icons.EVENT

def get_prio_config(prio_name):
    """Get color + icon for priority"""
    for p in APP_CONFIG["priorities"]:
        if p["name"] == prio_name:
            return {
                "color": COLOR_MAP.get(p["color"], ft.Colors.GREY),
                "icon": ICON_MAP.get(p["icon"], ft.Icons.CIRCLE),
                "label": p["label"],
            }
    return {"color": ft.Colors.GREY, "icon": ft.Icons.CIRCLE, "label": prio_name}
```

### 7.3 Time Calculation

```python
def generate_time_options():
    """Create time dropdown options: 06:00, 06:30, 07:00, ..., 22:30"""
    return [
        ft.dropdown.Option(f"{h:02d}:{m:02d}")
        for h in range(6, 23)
        for m in (0, 30)
    ]

def calculate_end_time(start_str, duration_minutes):
    """Calculate end time given start time and duration"""
    try:
        h, m = map(int, start_str.split(":"))
        return (
            datetime(2000, 1, 1, h, m) + timedelta(minutes=int(duration_minutes))
        ).strftime("%H:%M")
    except:
        return start_str
```

---

## 8. Event Handlers (Interactions)

### 8.1 Navigation Handlers

```python
def go_to_today(e):
    """Set current_date to today and refresh"""
    nonlocal current_date
    current_date = datetime.now()
    refresh_all()

def go_to_current_month(e):
    """Set current_month_view to current month"""
    nonlocal current_month_view
    current_month_view = datetime.now()
    load_month_view()
    page.update()

def go_prev_day(e):
    """Previous day"""
    nonlocal current_date
    current_date -= timedelta(days=1)
    load_day_view()
    page.update()

def go_next_day(e):
    """Next day"""
    nonlocal current_date
    current_date += timedelta(days=1)
    load_day_view()
    page.update()
```

### 8.2 Import/Export Handlers

```python
def export_data_to_json(e):
    """Dialog: Save to file OR Copy to clipboard"""
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Tùy chọn xuất dữ liệu"),
        actions=[
            ft.TextButton("Lưu vào File", on_click=handle_save_to_file),
            ft.ElevatedButton("Copy", on_click=handle_copy_to_clipboard),
            ft.TextButton("Hủy", on_click=lambda e: page.close(dlg)),
        ],
    )
    page.open(dlg)

def handle_file_picker_result(e: ft.FilePickerResultEvent):
    """Process import or export result"""
    # Import: e.files (list of selected files)
    # Export: e.path (save location)
```

---

## 9. Refresh & Update Logic

### 9.1 Full Refresh

```python
def refresh_all():
    """Reload config + re-render all views"""
    nonlocal APP_CONFIG
    APP_CONFIG = db.load_settings()
    page.title = APP_CONFIG.get("app_title", "microSchedule")
    app_bar_title.value = page.title
    app_bar_title.update()
    load_day_view()
    load_month_view()
    page.update()
```

**When to call**:
- After importing data
- After settings change
- After manual refresh action

### 9.2 Partial Update

```python
# Update only day view
load_day_view()
page.update()

# Update only month view
load_month_view()
page.update()
```

---

## 10. Best Practices & Patterns

### Do's ✅
- ✅ Use containers (`ft.Column`, `ft.Row`) for layout
- ✅ Keep components small and reusable
- ✅ Use theme variables consistently
- ✅ Call `page.update()` after state changes
- ✅ Use `nonlocal` for global state modification

### Don'ts ❌
- ❌ Hardcoding colors (use THEME dict)
- ❌ Deeply nested layouts (max 4-5 levels)
- ❌ Forgetting `page.update()` calls
- ❌ Direct DOM manipulation (let Flet handle it)
- ❌ Inline event handlers (define as separate functions)

---

## 11. Common Patterns

### Pattern: Card with Actions

```python
def create_task_card(task):
    def on_complete(e):
        db.mark_task_complete(task["id"])
        refresh_all()

    def on_edit(e):
        show_edit_dialog(task)

    def on_delete(e):
        db.delete_task(task["id"])
        refresh_all()

    return ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.Text(task["title"], weight="bold"),
                ft.Row([
                    ft.IconButton(ft.Icons.CHECK, on_click=on_complete),
                    ft.IconButton(ft.Icons.EDIT, on_click=on_edit),
                    ft.IconButton(ft.Icons.DELETE, on_click=on_delete),
                ]),
            ]),
        )
    )
```

### Pattern: Dialog with Form

```python
def show_edit_dialog(task):
    title_field = ft.TextField(label="Title", value=task["title"])
    prio_dropdown = ft.Dropdown(
        label="Priority",
        options=[ft.dropdown.Option(p["name"]) for p in APP_CONFIG["priorities"]],
        value=task["priority"],
    )

    def on_save(e):
        task["title"] = title_field.value
        task["priority"] = prio_dropdown.value
        db.update_task(task)
        page.close(dlg)
        refresh_all()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit Task"),
        content=ft.Column([title_field, prio_dropdown]),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: page.close(dlg)),
            ft.ElevatedButton("Save", on_click=on_save),
        ],
    )
    page.open(dlg)
```

---

## 12. Future UI Improvements

- [ ] Dark mode toggle
- [ ] Responsive layout (mobile support)
- [ ] Drag-and-drop reordering
- [ ] Search/filter tasks
- [ ] Settings panel (fully implement)
- [ ] Notification system (SnackBar improvements)
- [ ] Custom colors for categories
- [ ] Time block visualization (Gantt chart)

---
*Tài liệu cập nhật ngày 25/05/2026.*

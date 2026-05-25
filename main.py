import flet as ft
import sqlite3
import calendar
import json
import os
import sys
from datetime import datetime, timedelta
import database as db  # Import module database

# --- 🎨 THEME & CONSTANTS ---
THEME = {
    "primary": ft.Colors.PINK_600,
    "primary_light": ft.Colors.PINK_50,
    "accent": ft.Colors.TEAL_600,
    "text_dark": ft.Colors.GREY_900,
    "today_bg": ft.Colors.RED_50,
    "today_border": ft.Colors.RED_400,
}

ICON_MAP = {
    "School": ft.Icons.SCHOOL,
    "Home": ft.Icons.HOME,
    "Work": ft.Icons.WORK,
    "Cafe": ft.Icons.LOCAL_CAFE,
    "Library": ft.Icons.LOCAL_LIBRARY,
    "Online": ft.Icons.VIDEOCAM,
    "Gym": ft.Icons.FITNESS_CENTER,
    "Other": ft.Icons.LOCATION_ON,
    "Low": ft.Icons.LOW_PRIORITY,
    "Check": ft.Icons.CHECK_CIRCLE_OUTLINE,
    "High": ft.Icons.PRIORITY_HIGH,
    "Danger": ft.Icons.DANGEROUS,
    "Warning": ft.Icons.WARNING,
    "Star": ft.Icons.STAR,
    "Flag": ft.Icons.FLAG,
    "Circle": ft.Icons.CIRCLE,
}

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


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def main(page: ft.Page):
    # 1. Load Config & Init
    APP_CONFIG = db.load_settings()
    page.title = APP_CONFIG.get("app_title", "microSchedule")
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1400
    page.window_height = 900
    page.padding = 0
    try:
        page.window_icon = resource_path("app_icon.ico")
    except:
        pass

    con = db.get_connection()
    cur = con.cursor()

    # --- STATE ---
    current_date = datetime.now()
    current_month_view = datetime.now()
    file_picker = ft.FilePicker()
    date_picker = ft.DatePicker(
        first_date=datetime(2023, 1, 1),
        last_date=datetime(2030, 12, 31),
    )
    page.overlay.extend([file_picker, date_picker])

    # --- UI REFS ---
    lbl_current_date = ft.Text(size=20, weight="bold", color=THEME["primary"])
    lbl_month_title = ft.Text(size=24, weight="bold", color=THEME["primary"])
    app_bar_title = ft.Text(page.title, color="white", weight="bold")

    container_tasks = ft.Column()
    container_schedule = ft.Column()
    container_calendar_grid = ft.Column(spacing=2)
    tabs_control = ft.Tabs()

    # --- HELPERS ---
    def get_date_str(dt):
        return dt.strftime("%Y-%m-%d")

    def format_date_vn(dt):
        weekday = dt.weekday()
        map_thu = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
        return f"{map_thu[weekday]}, {dt.strftime('%d/%m')}"

    def generate_time_options():
        return [
            ft.dropdown.Option(f"{h:02d}:{m:02d}")
            for h in range(6, 23)
            for m in (0, 30)
        ]

    def get_location_icon(loc_name):
        if not loc_name:
            return ft.Icons.EVENT
        for loc in APP_CONFIG["locations"]:
            if loc["name"].lower() in loc_name.lower():
                return ICON_MAP.get(loc["icon"], ft.Icons.LOCATION_ON)
        loc_lower = loc_name.lower()
        if "online" in loc_lower:
            return ft.Icons.VIDEOCAM
        if "home" in loc_lower or "nhà" in loc_lower:
            return ft.Icons.HOME
        return ft.Icons.EVENT

    def get_prio_config(prio_name):
        for p in APP_CONFIG["priorities"]:
            if p["name"] == prio_name:
                return {
                    "color": COLOR_MAP.get(p["color"], ft.Colors.GREY),
                    "icon": ICON_MAP.get(p["icon"], ft.Icons.CIRCLE),
                    "label": p["label"],
                }
        return {"color": ft.Colors.GREY, "icon": ft.Icons.CIRCLE, "label": prio_name}

    def calculate_end_time(start_str, duration_minutes):
        try:
            h, m = map(int, start_str.split(":"))
            return (
                datetime(2000, 1, 1, h, m) + timedelta(minutes=int(duration_minutes))
            ).strftime("%H:%M")
        except:
            return start_str

    # --- CORE LOGIC ---
    def refresh_all():
        nonlocal APP_CONFIG
        APP_CONFIG = db.load_settings()
        page.title = APP_CONFIG.get("app_title", "microSchedule")
        app_bar_title.value = page.title
        app_bar_title.update()
        load_day_view()
        load_month_view()
        page.update()

    def go_to_today(e):
        nonlocal current_date
        current_date = datetime.now()
        refresh_all()

    def go_to_current_month(e):
        nonlocal current_month_view
        current_month_view = datetime.now()
        load_month_view()
        page.update()

    # --- EXPORT/IMPORT HANDLERS ---
    def generate_planner_data():
        """Fetches and structures planner data based on the current date."""
        # Use the global `current_date` and `cur`
        threshold_dt = current_date
        threshold_iso = threshold_dt.strftime("%Y-%m-%d")

        # Helper to convert sqlite rows to dicts
        def rows_to_dicts(cursor, rows):
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

        # 1. GET SCHEDULE
        query_schedule = """
            SELECT subject, time_start, time_end, location, date_str
            FROM schedule
            WHERE date_str >= ?
            ORDER BY date_str ASC, time_start ASC
        """
        cur.execute(query_schedule, (threshold_iso,))
        schedules = rows_to_dicts(cur, cur.fetchall())

        # 2. GET TASKS
        query_tasks = """
            SELECT id, title, is_completed, priority, date_str, note
            FROM tasks
            WHERE date_str >= ?
               OR (date_str < ? AND is_completed = 0)
            ORDER BY date_str ASC
        """
        cur.execute(query_tasks, (threshold_iso, threshold_iso))
        tasks_raw = rows_to_dicts(cur, cur.fetchall())

        # 3. GET SUBTASKS and combine
        tasks_with_subs = []
        for task in tasks_raw:
            task_id = task["id"]
            query_sub = """
                SELECT content, is_completed
                FROM subtasks
                WHERE task_id = ?
            """
            cur.execute(query_sub, (task_id,))
            subtasks = rows_to_dicts(cur, cur.fetchall())

            task["subtasks_list"] = subtasks
            total_sub = len(subtasks)
            done_sub = sum(1 for s in subtasks if s["is_completed"] == 1)

            task_dt = datetime.strptime(task["date_str"], "%Y-%m-%d")

            if task_dt.date() < threshold_dt.date():
                task["context_note"] = f"OVERDUE (Quá hạn). Tiến độ: {done_sub}/{total_sub}"
            else:
                task["context_note"] = f"UPCOMING. Tiến độ: {done_sub}/{total_sub}"

            tasks_with_subs.append(task)

        # 4. Final data structure
        final_data = {
            "metadata": {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "threshold_date": threshold_dt.strftime("%d/%m/%Y"),
                "date_format": "YYYY-MM-DD",
                "description": "Dữ liệu dùng để lập kế hoạch ôn thi.",
            },
            "schedule_events": schedules,
            "todo_tasks": tasks_with_subs,
        }
        return final_data

    def export_data_to_json(e):
        def handle_save_to_file(e):
            page.close(dlg)
            file_picker.save_file(
                dialog_title="Lưu file JSON",
                file_name="planner_data.json",
                allowed_extensions=["json"],
            )

        def handle_copy_to_clipboard(e):
            try:
                data = generate_planner_data()
                json_string = json.dumps(data, ensure_ascii=False, indent=2)
                page.set_clipboard(json_string)
                page.close(dlg)
                page.open(ft.SnackBar(ft.Text("Đã copy dữ liệu vào clipboard!"), bgcolor="green"))
            except Exception as ex:
                page.close(dlg)
                page.open(ft.SnackBar(ft.Text(f"Lỗi khi tạo dữ liệu: {ex}"), bgcolor="red"))

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Tùy chọn xuất dữ liệu"),
            content=ft.Text("Bạn muốn lưu dữ liệu ra file hay copy vào clipboard?"),
            actions=[
                ft.TextButton("Lưu vào File", on_click=handle_save_to_file),
                ft.ElevatedButton("Copy", on_click=handle_copy_to_clipboard),
                ft.TextButton("Hủy", on_click=lambda e: page.close(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def handle_file_picker_result(e: ft.FilePickerResultEvent):
        # Handle file open for import
        if e.files:
            filepath = e.files[0].path
            filename = e.files[0].name
            success = False
            msg = ""

            if filename.endswith(".ics"):
                success, msg = db.import_ics_schedule(filepath)
            elif filename.endswith(".xlsx"):
                success, msg = db.import_excel_schedule(filepath)
            else:
                msg = "Định dạng file không hỗ trợ! (Chỉ nhận .ics hoặc .xlsx)"

            if success:
                refresh_all()
                page.open(ft.SnackBar(ft.Text(msg, color="white"), bgcolor="green"))
            else:
                page.open(ft.SnackBar(ft.Text(f"Lỗi: {msg}", color="white"), bgcolor="red"))
            return

        # Handle file save for export
        if e.path:
            try:
                data = generate_planner_data()
                with open(e.path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                page.open(ft.SnackBar(ft.Text("Đã xuất dữ liệu thành công!"), bgcolor="green"))
            except Exception as ex:
                page.open(ft.SnackBar(ft.Text(f"Lỗi khi xuất file: {ex}", color="white"), bgcolor="red"))

    file_picker.on_result = handle_file_picker_result

    def open_import_dialog(e):
        file_picker.pick_files(allow_multiple=False, allowed_extensions=["ics", "xlsx"])

    # --- DELETE CONFIRM ---
    def open_confirm_delete_dialog(item_type, item_id):
        def on_confirm(e):
            if item_type == "task":
                delete_task(item_id)
            elif item_type == "schedule":
                delete_schedule(item_id)
            page.close(dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Xác nhận xóa"),
            content=ft.Text("Bạn có chắc chắn không?"),
            actions=[
                ft.TextButton("Hủy", on_click=lambda e: page.close(dlg)),
                ft.TextButton(
                    "XÓA", on_click=on_confirm, style=ft.ButtonStyle(color="red")
                ),
            ],
        )
        page.open(dlg)

    # --- VIEW 1: DAY DETAIL ---
    def load_day_view():
        date_str = get_date_str(current_date)
        is_today = date_str == get_date_str(datetime.now())
        lbl_current_date.value = (
            f"{format_date_vn(current_date)} {'(Hôm nay)' if is_today else ''}"
        )

        # Schedule
        container_schedule.controls.clear()
        cur.execute(
            "SELECT id, subject, time_start, time_end, location, date_str, is_cancelled FROM schedule WHERE date_str = ? ORDER BY time_start", (date_str,)
        )
        schedules = cur.fetchall()

        if not schedules:
            container_schedule.controls.append(
                ft.Container(
                    padding=20,
                    alignment=ft.alignment.center,
                    content=ft.Text("Không có lịch cứng", color="grey"),
                )
            )
        else:
            for item in schedules:
                sid, sub, t_start, t_end, loc, d_str, is_can = item
                is_can = bool(is_can)
                loc_icon = get_location_icon(loc)
                btn_care = ft.Container(
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=12,
                    bgcolor=ft.Colors.GREY_300 if not is_can else ft.Colors.ORANGE_100,
                    on_click=lambda e, id=sid: toggle_schedule_cancel(id),
                    content=ft.Text(
                        "Don't care 😒" if not is_can else "Thực ra cũng quan trọng..",
                        size=10,
                        weight="bold",
                        color=(
                            ft.Colors.GREY_800 if not is_can else ft.Colors.ORANGE_900
                        ),
                    ),
                )
                container_schedule.controls.append(
                    ft.Card(
                        elevation=0,
                        color=ft.Colors.WHITE,
                        content=ft.Container(
                            padding=10,
                            border=ft.border.only(
                                left=ft.border.BorderSide(
                                    4,
                                    ft.Colors.GREY_400 if is_can else THEME["primary"],
                                )
                            ),
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Icon(
                                                ft.Icons.ACCESS_TIME_FILLED,
                                                color=THEME["primary"],
                                                size=16,
                                            ),
                                            ft.Text(
                                                f"{t_start} - {t_end}",
                                                weight="bold",
                                                color=THEME["primary"],
                                            ),
                                            ft.Container(expand=True),
                                            btn_care,
                                        ]
                                    ),
                                    ft.Text(
                                        sub,
                                        size=15,
                                        weight="bold",
                                        style=ft.TextStyle(
                                            decoration=(
                                                ft.TextDecoration.LINE_THROUGH
                                                if is_can
                                                else None
                                            )
                                        ),
                                    ),
                                    ft.Row(
                                        [
                                            ft.Icon(
                                                loc_icon, size=14, color=THEME["accent"]
                                            ),
                                            ft.Text(loc, size=12),
                                            ft.Container(expand=True),
                                            ft.IconButton(
                                                ft.Icons.DELETE,
                                                icon_color="red",
                                                icon_size=16,
                                                opacity=0.3,
                                                on_click=lambda e, id=sid: open_confirm_delete_dialog(
                                                    "schedule", id
                                                ),
                                            ),
                                        ]
                                    ),
                                ],
                                spacing=3,
                            ),
                        ),
                    )
                )

        # Tasks (Split)
        container_tasks.controls.clear()
        cur.execute(
            "SELECT * FROM tasks WHERE date_str < ? AND is_completed = 0",
            (get_date_str(datetime.now()),),
        )
        backlogs = cur.fetchall()
        if backlogs:
            container_tasks.controls.append(
                ft.Container(
                    padding=10,
                    bgcolor=ft.Colors.RED_50,
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.RED_200),
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.Icons.WARNING, color="red"),
                                    ft.Text(
                                        "CẦN XỬ LÝ GẤP", color="red", weight="bold"
                                    ),
                                ]
                            ),
                            *[create_task_item(t, is_backlog=True) for t in backlogs],
                        ]
                    ),
                )
            )

        cur.execute(
            "SELECT * FROM tasks WHERE date_str = ? AND is_completed = 0 ORDER BY priority DESC",
            (date_str,),
        )
        todos = cur.fetchall()
        for t in todos:
            container_tasks.controls.append(create_task_item(t, is_backlog=False))

        cur.execute(
            "SELECT * FROM tasks WHERE date_str = ? AND is_completed = 1", (date_str,)
        )
        dones = cur.fetchall()
        if dones:
            container_tasks.controls.append(
                ft.Divider(height=20, thickness=1, color=ft.Colors.GREY_200)
            )
            container_tasks.controls.append(
                ft.Text(
                    "--- ĐÃ HOÀN THÀNH ---",
                    size=12,
                    color="grey",
                    weight="bold",
                    text_align=ft.TextAlign.CENTER,
                )
            )
            for t in dones:
                container_tasks.controls.append(create_task_item(t, is_backlog=False))

        if not todos and not backlogs and not dones:
            container_tasks.controls.append(
                ft.Container(
                    alignment=ft.alignment.center,
                    padding=40,
                    content=ft.Text("Ngày thảnh thơi ~", italic=True, color="grey"),
                )
            )

    # --- TASK ITEM ---
    def create_task_item(task_data, is_backlog):
        tid, title, done, prio, dstr, note = task_data
        done = bool(done)
        prio_cfg = get_prio_config(prio)
        subtask_info_ref = ft.Text(size=11, color="grey", italic=True)

        def update_progress_display(init=False):
            cur.execute(
                "SELECT count(*), sum(is_completed) FROM subtasks WHERE task_id = ?",
                (tid,),
            )
            res = cur.fetchone()
            total = res[0]
            completed = res[1] if res[1] is not None else 0
            subtask_info_ref.value = f"{completed}/{total} mục nhỏ" if total > 0 else ""
            if not init:
                subtask_info_ref.update()

        update_progress_display(init=True)

        note_indicator = ft.Container()
        if note:
            note_indicator = ft.Container(
                bgcolor=ft.Colors.GREY_200,
                border_radius=4,
                padding=ft.padding.symmetric(horizontal=4, vertical=1),
                content=ft.Text(
                    f"Note: {note}",
                    size=10,
                    color=ft.Colors.GREY_800,
                    no_wrap=True,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            )

        date_tag = ft.Container()
        if is_backlog:
            try:
                dt_obj = datetime.strptime(dstr, "%Y-%m-%d")
                date_tag = ft.Container(
                    padding=3,
                    bgcolor=ft.Colors.RED_100,
                    border_radius=4,
                    content=ft.Text(
                        f"{dt_obj.day}/{dt_obj.month}",
                        size=10,
                        color="red",
                        weight="bold",
                    ),
                )
            except:
                pass

        opacity_val = 0.6 if done else 1.0
        prio_chip = ft.Container(
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
            border_radius=10,
            bgcolor=prio_cfg["color"],
            content=ft.Text(prio_cfg["label"], size=10, color="white", weight="bold"),
        )

        subtasks_view = ft.Column(visible=False, spacing=0)

        def render_subtasks_in_view():
            cur.execute("SELECT * FROM subtasks WHERE task_id = ?", (tid,))
            subs = cur.fetchall()
            subtasks_view.controls = []
            for s in subs:
                sid, _, content, s_done = s
                text_ref = ft.Text(
                    content,
                    size=13,
                    style=ft.TextStyle(
                        decoration=(
                            ft.TextDecoration.LINE_THROUGH
                            if s_done
                            else ft.TextDecoration.NONE
                        )
                    ),
                    expand=True,
                )

                def on_tick_sub(e, sub_id=sid, txt_ctrl=text_ref):
                    cur.execute(
                        "UPDATE subtasks SET is_completed = ? WHERE id = ?",
                        (1 if e.control.value else 0, sub_id),
                    )
                    con.commit()
                    txt_ctrl.style.decoration = (
                        ft.TextDecoration.LINE_THROUGH
                        if e.control.value
                        else ft.TextDecoration.NONE
                    )
                    txt_ctrl.update()
                    update_progress_display()

                subtasks_view.controls.append(
                    ft.Container(
                        padding=ft.padding.only(left=30),
                        content=ft.Row(
                            [
                                ft.Checkbox(value=bool(s_done), on_change=on_tick_sub),
                                text_ref,
                            ]
                        ),
                    )
                )
            if not subs:
                subtasks_view.controls.append(
                    ft.Container(
                        padding=ft.padding.only(left=30),
                        content=ft.Text(
                            "Chưa có việc nhỏ", italic=True, size=12, color="grey"
                        ),
                    )
                )

        render_subtasks_in_view()

        def toggle_expansion(e):
            subtasks_view.visible = not subtasks_view.visible
            subtasks_view.update()

        return ft.Container(
            padding=10,
            border_radius=8,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
            opacity=opacity_val,
            content=ft.Column(
                [
                    ft.Container(
                        on_click=toggle_expansion,
                        content=ft.Row(
                            [
                                ft.Checkbox(
                                    value=done,
                                    on_change=lambda e: toggle_task_done(tid, done),
                                ),
                                date_tag,
                                ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                prio_chip,
                                                ft.Text(
                                                    title,
                                                    weight=(
                                                        "bold" if not done else "normal"
                                                    ),
                                                    style=ft.TextStyle(
                                                        decoration=(
                                                            ft.TextDecoration.LINE_THROUGH
                                                            if done
                                                            else None
                                                        ),
                                                        color=(
                                                            ft.Colors.BLACK
                                                            if not done
                                                            else "grey"
                                                        ),
                                                    ),
                                                    expand=True,
                                                    no_wrap=True,
                                                    overflow=ft.TextOverflow.ELLIPSIS,
                                                ),
                                            ],
                                            spacing=5,
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        ),
                                        (
                                            ft.Row(
                                                [subtask_info_ref, note_indicator],
                                                spacing=5,
                                            )
                                            if (subtask_info_ref.value or note)
                                            else ft.Container()
                                        ),
                                    ],
                                    expand=True,
                                    spacing=2,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                ft.IconButton(
                                    ft.Icons.EDIT,
                                    icon_size=16,
                                    opacity=0.5,
                                    tooltip="Sửa Task",
                                    on_click=lambda e: open_edit_task_dialog(tid),
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE,
                                    icon_size=16,
                                    icon_color="red",
                                    opacity=0.5,
                                    tooltip="Xóa",
                                    on_click=lambda e: open_confirm_delete_dialog(
                                        "task", tid
                                    ),
                                ),
                            ]
                        ),
                    ),
                    subtasks_view,
                ]
            ),
        )

    # --- VIEW 2: MONTH CALENDAR ---
    def load_month_view():
        year = current_month_view.year
        month = current_month_view.month
        lbl_month_title.value = f"THÁNG {month} / {year}"
        cal = calendar.monthcalendar(year, month)
        container_calendar_grid.controls.clear()
        container_calendar_grid.controls.append(
            ft.Row(
                [
                    ft.Container(
                        content=ft.Text(d, size=12, weight="bold", color="grey"),
                        expand=True,
                        alignment=ft.alignment.center,
                    )
                    for d in ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
                ]
            )
        )

        today_dt = datetime.now()
        today_str = get_date_str(today_dt)

        # Pre-fetch total overdue for "today" badge and tooltip
        cur.execute(
            "SELECT title, date_str FROM tasks WHERE date_str < ? AND is_completed = 0 ORDER BY date_str",
            (today_str,),
        )
        all_overdue_tasks = cur.fetchall()
        total_overdue_count = len(all_overdue_tasks)

        for week in cal:
            week_row = ft.Row(expand=True, spacing=2)
            for day in week:
                if day == 0:
                    week_row.controls.append(
                        ft.Container(expand=True, bgcolor=ft.Colors.GREY_50)
                    )
                else:
                    this_dt = datetime(year, month, day)
                    this_date_str = get_date_str(this_dt)
                    is_today = this_date_str == today_str
                    is_past = this_dt.date() < today_dt.date()

                    # --- Init UI Vars ---
                    day_bgcolor = ft.Colors.WHITE
                    overdue_indicator = ft.Container()

                    # --- Overdue Logic per day ---
                    cur.execute(
                        "SELECT count(*) FROM tasks WHERE date_str = ? AND is_completed = 0",
                        (this_date_str,),
                    )
                    uncompleted_on_day_count = cur.fetchone()[0]

                    if is_past and uncompleted_on_day_count > 0:
                        day_bgcolor = ft.Colors.RED_50
                        overdue_indicator = ft.Row(
                            [
                                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="red", size=12),
                                ft.Text(
                                    str(uncompleted_on_day_count),
                                    size=11,
                                    weight="bold",
                                    color="red",
                                ),
                            ],
                            spacing=2,
                        )

                    # --- "Today" overdue summary indicator ---
                    if is_today:
                        day_bgcolor = THEME["today_bg"]
                        if total_overdue_count > 0:
                            overdue_indicator = ft.Row(
                                [
                                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="orange", size=12),
                                    ft.Text(
                                        str(total_overdue_count),
                                        size=11,
                                        weight="bold",
                                        color="orange",
                                    ),
                                ],
                                spacing=2,
                            )

                    # --- Get Schedules & Tasks for the day ---
                    cur.execute(
                        "SELECT subject, location FROM schedule WHERE date_str = ? AND is_cancelled = 0",
                        (this_date_str,),
                    )
                    schedules = cur.fetchall()
                    cur.execute(
                        "SELECT title, priority, is_completed FROM tasks WHERE date_str = ?",
                        (this_date_str,),
                    )
                    tasks = cur.fetchall()

                    # --- Tooltip Logic ---
                    tooltip_lines = [f"📅 {s[0]}" for s in schedules]
                    if tasks:
                        tooltip_lines.append("--- Việc cần làm ---")
                        for t in tasks:
                            is_task_overdue = is_past and not t[2]
                            prefix = "⚠️" if is_task_overdue else ("✅" if t[2] else "▫️")
                            tooltip_lines.append(f"{prefix} {t[0]}")

                    if is_today and all_overdue_tasks:
                        tooltip_lines.append("--- Việc trễ hạn ---")
                        for ov_task in all_overdue_tasks:
                             # ov_task is (title, date_str)
                            task_dt = datetime.strptime(ov_task[1], "%Y-%m-%d")
                            tooltip_lines.append(f"⚠️ {ov_task[0]} ({task_dt.day}/{task_dt.month})")

                    # --- Build Day Cell UI ---
                    content_col = ft.Column(
                        spacing=1, alignment=ft.MainAxisAlignment.START
                    )
                    content_col.controls.append(
                        ft.Row(
                            [
                                ft.Container(
                                    padding=3,
                                    border_radius=4,
                                    bgcolor=THEME["today_bg"] if is_today else None,
                                    content=ft.Text(
                                        str(day),
                                        weight="bold",
                                        color=(
                                            THEME["primary"]
                                            if is_today
                                            else ft.Colors.BLACK
                                        ),
                                    ),
                                ),
                                ft.Container(expand=True),
                                overdue_indicator,
                            ]
                        )
                    )

                    max_items = 3
                    count = 0
                    # Display schedules
                    for s in schedules:
                        if count < max_items:
                            smart_icon = get_location_icon(s[1])
                            content_col.controls.append(
                                ft.Container(
                                    padding=2, border_radius=2, bgcolor=ft.Colors.BLUE_50,
                                    content=ft.Row([
                                        ft.Icon(smart_icon, size=10, color=ft.Colors.BLUE_900),
                                        ft.Text(s[0], size=9, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, color=ft.Colors.BLUE_900),
                                    ], spacing=2),
                                )
                            )
                            count += 1
                    # Display tasks for the day
                    for t in tasks:
                        if count < max_items:
                            p_cfg = get_prio_config(t[1])
                            is_task_overdue_style = is_past and not t[2]
                            bg_c = ft.Colors.RED_100 if is_task_overdue_style else (ft.Colors.GREY_100 if t[2] else ft.Colors.GREY_50)
                            txt_c = ft.Colors.RED_900 if is_task_overdue_style else (ft.Colors.GREY if t[2] else ft.Colors.BLACK87)

                            content_col.controls.append(
                                ft.Container(
                                    padding=2, border_radius=2,
                                    border=ft.border.only(left=ft.border.BorderSide(3, p_cfg["color"])),
                                    bgcolor=bg_c,
                                    content=ft.Text(t[0], size=9, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS, color=txt_c),
                                )
                            )
                            count += 1

                    total_hidden = (len(schedules) + len(tasks)) - max_items
                    if total_hidden > 0:
                        content_col.controls.append(
                            ft.Text(f"+ {total_hidden}...", size=9, color="grey", italic=True)
                        )

                    week_row.controls.append(
                        ft.Container(
                            content=content_col,
                            expand=True,
                            height=110,
                            padding=4,
                            bgcolor=day_bgcolor,
                            border=ft.border.all(
                                1 if is_today else 0.5,
                                (
                                    THEME["today_border"]
                                    if is_today
                                    else ft.Colors.GREY_300
                                ),
                            ),
                            tooltip="\n".join(tooltip_lines) if tooltip_lines else None,
                            on_click=lambda e, y=year, m=month, d=day: select_date_from_calendar(
                                y, m, d
                            ),
                        )
                    )
            container_calendar_grid.controls.append(week_row)

    # --- ACTIONS ---
    def select_date_from_calendar(y, m, d):
        nonlocal current_date
        current_date = datetime(y, m, d)
        tabs_control.selected_index = 0
        refresh_all()

    def change_day(delta):
        nonlocal current_date
        current_date += timedelta(days=delta)
        refresh_all()

    def change_month(delta):
        nonlocal current_month_view
        m = current_month_view.month + delta
        y = current_month_view.year
        (m, y) = (1, y + 1) if m > 12 else (12, y - 1) if m < 1 else (m, y)
        current_month_view = datetime(y, m, 1)
        load_month_view()
        page.update()

    def toggle_task_done(tid, current):
        cur.execute(
            "UPDATE tasks SET is_completed = ? WHERE id = ?", (0 if current else 1, tid)
        )
        con.commit()
        refresh_all()

    def delete_task(tid):
        cur.execute("DELETE FROM tasks WHERE id = ?", (tid,))
        cur.execute("DELETE FROM subtasks WHERE task_id = ?", (tid,))
        con.commit()
        refresh_all()

    def toggle_schedule_cancel(sid):
        cur.execute("SELECT is_cancelled FROM schedule WHERE id = ?", (sid,))
        curr = cur.fetchone()[0]
        cur.execute(
            "UPDATE schedule SET is_cancelled = ? WHERE id = ?", (0 if curr else 1, sid)
        )
        con.commit()
        refresh_all()

    def delete_schedule(sid):
        cur.execute("DELETE FROM schedule WHERE id = ?", (sid,))
        con.commit()
        refresh_all()

    # --- SETTINGS DIALOG ---
    def open_settings_dialog(e):
        def create_setting_row(text, detail, on_delete):
            return ft.ListTile(
                title=ft.Text(text, weight="bold"),
                subtitle=ft.Text(detail, size=12),
                trailing=ft.IconButton(
                    ft.Icons.DELETE, icon_color="red", on_click=on_delete
                ),
            )

        gen_col = ft.Column()
        title_tf = ft.TextField(
            label="Tên Ứng dụng", value=APP_CONFIG.get("app_title", "microSchedule")
        )

        def save_title(e):
            db.save_single_setting("app_title", title_tf.value)
            refresh_all()
            page.open(ft.SnackBar(ft.Text("Đã lưu!")))

        gen_col.controls = [
            ft.Row([title_tf, ft.ElevatedButton("Lưu", on_click=save_title)])
        ]
        loc_col = ft.Column(scroll="auto", height=300)
        new_loc_name = ft.TextField(label="Tên", expand=True)
        new_loc_icon = ft.Dropdown(
            label="Icon",
            options=[ft.dropdown.Option(k) for k in ICON_MAP.keys()],
            value="Other",
            width=100,
        )

        def render_locs(init=False):
            loc_col.controls = [
                create_setting_row(
                    l["name"], f"Icon: {l['icon']}", lambda e, x=l: del_loc(x)
                )
                for l in APP_CONFIG["locations"]
            ]
            (None if init else loc_col.update())

        def add_loc(e):
            APP_CONFIG["locations"].append(
                {"name": new_loc_name.value, "icon": new_loc_icon.value}
            )
            db.save_single_setting("locations", APP_CONFIG["locations"])
            new_loc_name.value = ""
            render_locs()

        def del_loc(item):
            APP_CONFIG["locations"].remove(item)
            db.save_single_setting("locations", APP_CONFIG["locations"])
            render_locs()

        prio_col = ft.Column(scroll="auto", height=300)
        new_prio_name = ft.TextField(label="Mức", expand=True)
        new_prio_label = ft.TextField(label="Nhãn", expand=True)
        new_prio_color = ft.Dropdown(
            label="Màu",
            options=[ft.dropdown.Option(k) for k in COLOR_MAP.keys()],
            value="Grey",
            width=90,
        )
        new_prio_icon = ft.Dropdown(
            label="Icon",
            options=[ft.dropdown.Option(k) for k in ICON_MAP.keys()],
            value="Circle",
            width=90,
        )

        def render_prios(init=False):
            prio_col.controls = [
                create_setting_row(
                    p["name"], f"{p['label']}", lambda e, x=p: del_prio(x)
                )
                for p in APP_CONFIG["priorities"]
            ]
            (None if init else prio_col.update())

        def add_prio(e):
            APP_CONFIG["priorities"].append(
                {
                    "name": new_prio_name.value,
                    "label": new_prio_label.value,
                    "color": new_prio_color.value,
                    "icon": new_prio_icon.value,
                }
            )
            db.save_single_setting("priorities", APP_CONFIG["priorities"])
            render_prios()

        def del_prio(item):
            APP_CONFIG["priorities"].remove(item)
            db.save_single_setting("priorities", APP_CONFIG["priorities"])
            render_prios()

        dur_col = ft.Column(scroll="auto", height=300)
        new_dur_lbl = ft.TextField(label="Nhãn", expand=True)
        new_dur_val = ft.TextField(label="Phút", width=80)

        def render_durs(init=False):
            dur_col.controls = [
                create_setting_row(
                    d["label"], f"{d['value']}p", lambda e, x=d: del_dur(x)
                )
                for d in APP_CONFIG["durations"]
            ]
            (None if init else dur_col.update())

        def add_dur(e):
            APP_CONFIG["durations"].append(
                {"label": new_dur_lbl.value, "value": int(new_dur_val.value)}
            )
            db.save_single_setting("durations", APP_CONFIG["durations"])
            render_durs()

        def del_dur(item):
            APP_CONFIG["durations"].remove(item)
            db.save_single_setting("durations", APP_CONFIG["durations"])
            render_durs()

        render_locs(True)
        render_prios(True)
        render_durs(True)
        dlg = ft.AlertDialog(
            title=ft.Text("Cài đặt"),
            content=ft.Container(
                width=750,
                height=500,
                content=ft.Tabs(
                    tabs=[
                        ft.Tab(
                            text="Chung",
                            content=ft.Container(padding=10, content=gen_col),
                        ),
                        ft.Tab(
                            text="Địa điểm",
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            new_loc_name,
                                            new_loc_icon,
                                            ft.IconButton(
                                                ft.Icons.ADD, on_click=add_loc
                                            ),
                                        ]
                                    ),
                                    ft.Divider(),
                                    loc_col,
                                ]
                            ),
                        ),
                        ft.Tab(
                            text="Độ ưu tiên",
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            new_prio_name,
                                            new_prio_label,
                                            new_prio_color,
                                            new_prio_icon,
                                            ft.IconButton(
                                                ft.Icons.ADD, on_click=add_prio
                                            ),
                                        ]
                                    ),
                                    ft.Divider(),
                                    prio_col,
                                ]
                            ),
                        ),
                        ft.Tab(
                            text="Thời gian",
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            new_dur_lbl,
                                            new_dur_val,
                                            ft.IconButton(
                                                ft.Icons.ADD, on_click=add_dur
                                            ),
                                        ]
                                    ),
                                    ft.Divider(),
                                    dur_col,
                                ]
                            ),
                        ),
                    ],
                    expand=True,
                ),
            ),
            actions=[ft.TextButton("Đóng", on_click=lambda e: page.close(dlg))],
        )
        page.open(dlg)

    # --- DIALOG: ADD/EDIT TASK ---
    def open_edit_task_dialog(tid=None):
        task_data = None
        if tid:
            cur.execute("SELECT * FROM tasks WHERE id = ?", (tid,))
            task_data = cur.fetchone()

        # State for the dialog's date
        current_task_date_str = task_data[4] if task_data else get_date_str(current_date)

        def handle_date_change(e):
            nonlocal current_task_date_str
            new_date = e.control.value.strftime("%Y-%m-%d")
            current_task_date_str = new_date
            # Update the UI text
            date_display_row.controls[1].value = f"Ngày: {datetime.strptime(new_date, '%Y-%m-%d').strftime('%d/%m/%Y')}"
            date_display_row.update()

        date_picker.on_change = handle_date_change

        title_tf = ft.TextField(
            label="Tên công việc",
            value=task_data[1] if task_data else "",
            text_size=16,
            autofocus=True,
        )
        note_tf = ft.TextField(
            label="Ghi chú",
            value=task_data[5] if task_data and len(task_data) > 5 else "",
            multiline=True,
            max_lines=2,
        )
        p_val = task_data[3] if task_data else APP_CONFIG["priorities"][1]["name"]
        prio_dd = ft.Dropdown(
            label="Priority",
            value=p_val,
            options=[
                ft.dropdown.Option(p["name"], text=p["label"])
                for p in APP_CONFIG["priorities"]
            ],
        )

        date_display_row = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.CALENDAR_MONTH,
                    on_click=lambda _: page.open(date_picker),
                    tooltip="Đổi ngày"
                ),
                ft.Text(f"Ngày: {datetime.strptime(current_task_date_str, '%Y-%m-%d').strftime('%d/%m/%Y')}")
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        subtasks_col = ft.Column(spacing=5)
        new_sub_tf = ft.TextField(
            hint_text="Thêm mục nhỏ...",
            height=40,
            text_size=13,
            content_padding=10,
            expand=True,
        )

        def render_subtasks(init=False):
            controls = []
            if tid:
                cur.execute("SELECT * FROM subtasks WHERE task_id = ?", (tid,))
                subs = cur.fetchall()
                for s in subs:
                    sid, _, content, s_done = s
                    controls.append(
                        ft.Row(
                            [
                                ft.Checkbox(
                                    value=bool(s_done),
                                    on_change=lambda e, id=sid, v=s_done: toggle_sub(
                                        id, v
                                    ),
                                ),
                                ft.Text(
                                    content,
                                    size=13,
                                    style=ft.TextStyle(
                                        decoration=(
                                            ft.TextDecoration.LINE_THROUGH
                                            if s_done
                                            else ft.TextDecoration.NONE
                                        )
                                    ),
                                    expand=True,
                                ),
                                ft.IconButton(
                                    ft.Icons.CLOSE,
                                    icon_size=14,
                                    on_click=lambda e, id=sid: del_sub(id),
                                ),
                            ]
                        )
                    )
            subtasks_col.controls = controls
            (None if init else subtasks_col.update())

        def save_task(close=True):
            nonlocal tid
            if not title_tf.value:
                return
            if tid:
                cur.execute(
                    "UPDATE tasks SET title=?, priority=?, note=?, date_str=? WHERE id=?",
                    (title_tf.value, prio_dd.value, note_tf.value, current_task_date_str, tid),
                )
            else:
                cur.execute(
                    "INSERT INTO tasks (title, priority, note, date_str) VALUES (?, ?, ?, ?)",
                    (
                        title_tf.value,
                        prio_dd.value,
                        note_tf.value,
                        current_task_date_str,
                    ),
                )
                tid = cur.lastrowid
            con.commit()
            (page.close(dlg) if close else None)
            refresh_all()

        def add_sub(e):
            if not new_sub_tf.value:
                return
            if not tid:
                save_task(close=False)
            cur.execute(
                "INSERT INTO subtasks (task_id, content) VALUES (?, ?)",
                (tid, new_sub_tf.value),
            )
            con.commit()
            new_sub_tf.value = ""
            new_sub_tf.focus()
            new_sub_tf.update()
            render_subtasks()

        def toggle_sub(sid, v):
            cur.execute(
                "UPDATE subtasks SET is_completed = ? WHERE id = ?",
                (0 if v else 1, sid),
            )
            con.commit()
            render_subtasks()

        def del_sub(sid):
            cur.execute("DELETE FROM subtasks WHERE id = ?", (sid,))
            con.commit()
            render_subtasks()

        new_sub_tf.on_submit = add_sub
        render_subtasks(True)
        dlg = ft.AlertDialog(
            title=ft.Text("Chi tiết Task"),
            content=ft.Container(
                width=500,
                height=450,
                content=ft.Column(
                    [
                        title_tf,
                        prio_dd,
                        date_display_row,
                        note_tf,
                        ft.Divider(),
                        ft.Text("Việc nhỏ:"),
                        ft.Row(
                            [new_sub_tf, ft.IconButton(ft.Icons.ADD, on_click=add_sub)]
                        ),
                        ft.Container(
                            content=subtasks_col,
                            expand=True,
                            border=ft.border.all(1, "grey"),
                            border_radius=5,
                            padding=5,
                        ),
                    ],
                    scroll="auto",
                ),
            ),
            actions=[
                ft.TextButton("Đóng", on_click=lambda e: page.close(dlg)),
                ft.ElevatedButton(
                    "LƯU",
                    bgcolor=THEME["primary"],
                    color="white",
                    on_click=lambda e: save_task(True),
                ),
            ],
        )
        page.open(dlg)

    # --- DIALOG: ADD SCHEDULE ---
    def open_add_schedule_dialog(e):
        start_dd = ft.Dropdown(
            label="Bắt đầu", options=generate_time_options(), value="07:00", expand=True
        )
        dur_tf = ft.TextField(label="Phút", value="90", expand=True)

        def set_dur(e):
            dur_tf.value = e.control.data
            dur_tf.update()

        chips_dur = ft.Row(
            [
                ft.Chip(
                    label=ft.Text(d["label"]), data=str(d["value"]), on_click=set_dur
                )
                for d in APP_CONFIG["durations"]
            ],
            wrap=True,
        )
        sub_tf = ft.TextField(label="Tên", autofocus=True)
        loc_tf = ft.TextField(label="Địa điểm", icon=ft.Icons.LOCATION_ON)

        def set_loc(e):
            loc_tf.value = e.control.label.value
            loc_tf.update()

        chips_loc = ft.Row(
            [
                ft.Chip(label=ft.Text(l["name"]), on_click=set_loc)
                for l in APP_CONFIG["locations"]
            ],
            wrap=True,
        )

        def save(e):
            end = calculate_end_time(start_dd.value, dur_tf.value)
            cur.execute(
                "INSERT INTO schedule (subject, time_start, time_end, location, date_str) VALUES (?, ?, ?, ?, ?)",
                (
                    sub_tf.value,
                    start_dd.value,
                    end,
                    loc_tf.value,
                    get_date_str(current_date),
                ),
            )
            con.commit()
            page.close(dlg)
            refresh_all()

        dlg = ft.AlertDialog(
            title=ft.Text("Thêm Lịch Cứng"),
            content=ft.Container(
                width=400,
                height=400,
                content=ft.Column(
                    [
                        sub_tf,
                        ft.Row([start_dd, dur_tf]),
                        chips_dur,
                        ft.Text("Địa điểm nhanh:"),
                        chips_loc,
                        loc_tf,
                    ],
                    scroll="auto",
                ),
            ),
            actions=[
                ft.ElevatedButton(
                    "Lưu", bgcolor=THEME["primary"], color="white", on_click=save
                )
            ],
        )
        page.open(dlg)

    # --- MAIN LAYOUT ---
    tab_day = ft.Row(
        [
            ft.Container(
                width=400,
                bgcolor=THEME["primary_light"],
                padding=0,
                border=ft.border.only(right=ft.border.BorderSide(1, "grey")),
                content=ft.Column(
                    [
                        ft.Container(
                            padding=20,
                            bgcolor=ft.Colors.WHITE,
                            content=ft.Row(
                                [
                                    ft.Text(
                                        "LỊCH CỐ ĐỊNH",
                                        color=THEME["primary"],
                                        weight="bold",
                                    ),
                                    ft.Container(expand=True),
                                    ft.IconButton(
                                        ft.Icons.ADD_CIRCLE,
                                        icon_color=THEME["primary"],
                                        on_click=open_add_schedule_dialog,
                                    ),
                                ]
                            ),
                        ),
                        ft.Column(
                            [container_schedule], scroll="auto", expand=True, spacing=10
                        ),
                    ]
                ),
            ),
            ft.Container(
                expand=True,
                padding=20,
                bgcolor="white",
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.IconButton(
                                    ft.Icons.CHEVRON_LEFT,
                                    on_click=lambda e: change_day(-1),
                                ),
                                ft.OutlinedButton(
                                    "VỀ HÔM NAY",
                                    on_click=go_to_today,
                                    icon=ft.Icons.CALENDAR_TODAY,
                                    style=ft.ButtonStyle(color=THEME["primary"]),
                                ),
                                lbl_current_date,
                                ft.IconButton(
                                    ft.Icons.CHEVRON_RIGHT,
                                    on_click=lambda e: change_day(1),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Divider(),
                        ft.Column([container_tasks], scroll="auto", expand=True),
                        ft.Container(
                            alignment=ft.alignment.bottom_right,
                            content=ft.Row(
                                [
                                    ft.FloatingActionButton(
                                        icon=ft.Icons.FILE_UPLOAD,
                                        text="Import",
                                        bgcolor=ft.Colors.BLUE_GREY,
                                        on_click=open_import_dialog,
                                    ),
                                    ft.FloatingActionButton(
                                        icon=ft.Icons.SAVE,
                                        text="Export JSON",
                                        tooltip="Xuất dữ liệu cho AI",
                                        bgcolor=ft.Colors.PURPLE,
                                        on_click=export_data_to_json,
                                    ),
                                    ft.FloatingActionButton(
                                        icon=ft.Icons.ADD,
                                        text="Thêm Task",
                                        bgcolor=THEME["accent"],
                                        foreground_color="white",
                                        on_click=lambda e: open_edit_task_dialog(None),
                                    ),
                                ],
                                spacing=10,
                                alignment=ft.MainAxisAlignment.END,
                            ),
                        ),
                    ]
                ),
            ),
        ],
        spacing=0,
        expand=True,
    )

    tab_month = ft.Container(
        padding=20,
        bgcolor="white",
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.IconButton(
                            ft.Icons.ARROW_BACK_IOS, on_click=lambda e: change_month(-1)
                        ),
                        lbl_month_title,
                        ft.IconButton(
                            ft.Icons.ARROW_FORWARD_IOS,
                            on_click=lambda e: change_month(1),
                        ),
                        ft.Container(width=20),
                        ft.ElevatedButton(
                            "Tháng hiện tại",
                            on_click=go_to_current_month,
                            bgcolor=THEME["primary_light"],
                            color=THEME["primary"],
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Divider(height=20, color="transparent"),
                container_calendar_grid,
            ]
        ),
    )

    tabs_control.tabs = [
        ft.Tab(text="CHI TIẾT NGÀY", content=tab_day),
        ft.Tab(text="LỊCH THÁNG", content=tab_month),
    ]
    tabs_control.expand = True
    tabs_control.label_color = THEME["primary"]
    tabs_control.indicator_color = THEME["primary"]

    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.SCHEDULE, color="white"),
        title=app_bar_title,
        bgcolor=THEME["primary"],
        actions=[
            ft.IconButton(
                ft.Icons.SETTINGS,
                icon_color="white",
                tooltip="Cài đặt",
                on_click=open_settings_dialog,
            )
        ],
    )
    page.add(tabs_control)
    refresh_all()


ft.app(target=main)

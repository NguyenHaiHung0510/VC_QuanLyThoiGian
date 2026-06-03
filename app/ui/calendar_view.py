"""
calendar_view.py — WS6: Continuous Calendar UI component.

Renders an Outlook-style scrollable multi-week calendar with:
- Left sidebar: mini month navigator + source visibility checkboxes
- Main area:    ListView of week rows, scrollable continuously
"""
import flet as ft
import calendar
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Any
from collections import defaultdict

from app.services.calendar_view_service import CalendarViewService
from app.services.calendar_import_service import CalendarImportService


# ---------------------------------------------------------------------------
# Week helpers (Appendix B)
# ---------------------------------------------------------------------------

def get_week_start(d: date) -> date:
    """Returns the Monday of the week containing d. weekday(): Mon=0, Sun=6."""
    return d - timedelta(days=d.weekday())


def _parse_hex_color(hex_color: str) -> str:
    """
    Convert '#RRGGBB' or 'RRGGBB' to a Flet-compatible color string.
    Falls back to original string/object if it's already a valid name or object.
    """
    if not hex_color:
        return ft.Colors.GREY_400
    if isinstance(hex_color, str):
        h = hex_color.strip().lstrip("#")
        if len(h) == 6:
            try:
                int(h, 16)
                return f"#{h.upper()}"
            except ValueError:
                pass
    return hex_color


# ---------------------------------------------------------------------------
# Main builder function
# ---------------------------------------------------------------------------

def build_continuous_calendar_tab(
    page: ft.Page,
    calendar_view_svc: CalendarViewService,
    theme: dict,
    color_map: dict,
    on_day_click=None,
) -> ft.Control:
    """
    Returns an ft.Row containing:
    - sidebar (width≈220px): mini month nav + source checkboxes
    - main area (expand): header row + scrollable week ListView
    """
    today = date.today()

    # Generate the visible continuous list from the current month forward.
    # Older months are still fetched for services/export paths, but rendering
    # them before the current month made Flet's initial scroll target unreliable.
    start_year = today.year
    end_year = today.year + 2
    start_month = today.month
    end_month = today.month

    sorted_months = []
    curr_y, curr_m = start_year, start_month
    while (curr_y, curr_m) <= (end_year, end_month):
        sorted_months.append((curr_y, curr_m))
        curr_m += 1
        if curr_m > 12:
            curr_m = 1
            curr_y += 1

    # ------------------------------------------------------------------ #
    # Mutable state                                                        #
    # ------------------------------------------------------------------ #
    state = {
        "mini_nav_month": datetime(today.year, today.month, 1),
        "selected_date": today,
        "events_cache": {},          # date_iso → List[dict]
        "sources": [],
        "last_visible_weeks_hash": "", # Track scroll state to prevent redundant updates
        "visible_dates": set(),      # Store current visible dates for highlighting
        "updating_source_id": None,  # Track which source is being updated with a new file
        "new_source_name": "",
    }

    source_update_picker = ft.FilePicker()
    new_source_picker = ft.FilePicker()
    page.overlay.append(source_update_picker)
    page.overlay.append(new_source_picker)

    def handle_source_update_result(e: ft.FilePickerResultEvent):
        if e.files:
            filepath = e.files[0].path
            source_id = state["updating_source_id"]
            if not source_id:
                return
            try:
                import_svc = CalendarImportService(calendar_view_svc.conn)
                res = import_svc.import_file(source_id, filepath)

                # Reload all data and views
                _reload_events()
                _reload_sources()
                _rebuild_calendar()
                _build_sources_col()

                if sources_col.page:
                    sources_col.update()
                page.update()

                page.open(ft.SnackBar(ft.Text(f"Đã cập nhật nguồn lịch thành công! (Nạp {res['parsed_count']} sự kiện)"), bgcolor="green"))
            except Exception as ex:
                print(f"[CalendarView] Error updating source file: {ex}")
                page.open(ft.SnackBar(ft.Text(f"Cập nhật file lịch thất bại: {ex}"), bgcolor="red"))

    source_update_picker.on_result = handle_source_update_result

    def _pick_source_color() -> str:
        colors = [
            "#2563eb",
            "#dc2626",
            "#64748b",
            "#16a34a",
            "#9333ea",
            "#ea580c",
            "#0891b2",
            "#be123c",
        ]
        return colors[len(state["sources"]) % len(colors)]

    def handle_new_source_result(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        display_name = state.get("new_source_name", "").strip()
        if not display_name:
            page.open(ft.SnackBar(ft.Text("Vui lòng đặt tên nguồn lịch trước khi import."), bgcolor="red"))
            return
        filepath = e.files[0].path
        try:
            import_svc = CalendarImportService(calendar_view_svc.conn)
            res = import_svc.import_new_source(
                display_name=display_name,
                file_path=filepath,
                kind="other",
                color=_pick_source_color(),
            )
            _reload_sources()
            _build_sources_col()
            _rebuild_calendar()
            if sources_col.page:
                sources_col.update()
            page.update()
            page.open(ft.SnackBar(ft.Text(f"Đã thêm nguồn lịch '{display_name}'! (Nạp {res['parsed_count']} sự kiện)"), bgcolor="green"))
        except Exception as ex:
            print(f"[CalendarView] Error adding new source: {ex}")
            page.open(ft.SnackBar(ft.Text(f"Thêm nguồn lịch thất bại: {ex}"), bgcolor="red"))
        finally:
            state["new_source_name"] = ""

    new_source_picker.on_result = handle_new_source_result

    # ------------------------------------------------------------------ #
    # Prefetch events from PG for visible range (±2 years)               #
    # ------------------------------------------------------------------ #
    def _reload_events():
        range_start_d = date(today.year - 2, today.month, 1)
        next_m = end_month + 1
        next_y = today.year + 2
        if next_m > 12:
            next_m = 1
            next_y += 1
        range_end_d = date(next_y, next_m, 1) - timedelta(days=1)

        # Convert to UTC datetime for PG query
        VN_TZ = timezone(timedelta(hours=7))
        range_start_dt = datetime(range_start_d.year, range_start_d.month, range_start_d.day,
                                  0, 0, 0, tzinfo=VN_TZ)
        range_end_dt = datetime(range_end_d.year, range_end_d.month, range_end_d.day,
                                23, 59, 59, tzinfo=VN_TZ)
        try:
            events = calendar_view_svc.get_events_by_range(range_start_dt, range_end_dt)
        except Exception as e:
            print(f"[CalendarView] Error fetching events: {e}")
            events = []

        cache: Dict[str, List[dict]] = {}
        for ev in events:
            starts = ev["starts_at"]
            if hasattr(starts, "date"):
                if starts.tzinfo is not None:
                    vn_dt = starts.astimezone(VN_TZ)
                    d_key = vn_dt.date().isoformat()
                else:
                    d_key = starts.date().isoformat()
            else:
                d_key = str(starts)[:10]
            cache.setdefault(d_key, []).append(ev)
        state["events_cache"] = cache

    def _reload_sources():
        try:
            state["sources"] = calendar_view_svc.get_active_sources()
        except Exception as e:
            print(f"[CalendarView] Error fetching sources: {e}")
            state["sources"] = []

    _reload_events()
    _reload_sources()

    # ------------------------------------------------------------------ #
    # Helper: month/year label                                            #
    # ------------------------------------------------------------------ #
    def _visible_range_label(center_date: date) -> str:
        return f"THÁNG {center_date.month:02d} / {center_date.year}"

    # ------------------------------------------------------------------ #
    # Header label (month/year of visible range)                          #
    # ------------------------------------------------------------------ #
    header_label = ft.Text(
        _visible_range_label(today),
        size=18,
        weight="bold",
        color=theme.get("primary", ft.Colors.PINK_600),
    )

    # ------------------------------------------------------------------ #
    # Build day cells (empty and normal)                                  #
    # ------------------------------------------------------------------ #
    def _build_empty_day_cell() -> ft.Control:
        return ft.Container(
            expand=True,
            height=100,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(0.5, ft.Colors.GREY_200),
        )

    def _event_vn_date(ev: Dict[str, Any]) -> date:
        starts = ev.get("starts_at")
        if hasattr(starts, "date"):
            if starts.tzinfo is not None:
                return starts.astimezone(timezone(timedelta(hours=7))).date()
            return starts.date()
        try:
            return datetime.fromisoformat(str(starts)).date()
        except Exception:
            return today

    def _build_day_cell(d: date, display_month: int) -> ft.Control:
        is_today = (d == today)
        is_other_month = (d.month != display_month)

        day_key = d.isoformat()
        day_events = state["events_cache"].get(day_key, [])

        num_color = (
            ft.Colors.GREY_400 if is_other_month
            else (theme.get("primary", ft.Colors.PINK_600) if is_today else ft.Colors.BLACK87)
        )
        num_weight = "bold" if is_today else "normal"

        day_num_container = ft.Container(
            padding=ft.padding.symmetric(horizontal=4, vertical=2),
            border_radius=16,
            bgcolor=theme.get("primary_light", ft.Colors.PINK_50) if is_today else None,
            content=ft.Text(str(d.day), size=12, weight=num_weight, color=num_color),
        )

        content_col = ft.Column(
            [ft.Row([day_num_container, ft.Container(expand=True)])],
            spacing=2,
            alignment=ft.MainAxisAlignment.START,
        )

        # Event chips (max 3 in cell, then +N...)
        max_chips = 3
        for i, ev in enumerate(day_events):
            if i >= max_chips:
                remaining = len(day_events) - max_chips
                content_col.controls.append(
                    ft.Text(f"+{remaining}…", size=9, color=ft.Colors.GREY_600, italic=True)
                )
                break
            ev_color = _parse_hex_color(ev.get("color", ""))
            chip = ft.Container(
                padding=ft.padding.symmetric(horizontal=4, vertical=1),
                border_radius=4,
                bgcolor=ev_color,
                alignment=ft.alignment.center_left, # Stretch chip horizontally
                content=ft.Text(
                    ev["title"],
                    size=9,
                    color="white",
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            )
            content_col.controls.append(chip)

        border = ft.border.all(
            2 if is_today else 0.5,
            ft.Colors.PINK_300 if is_today else ft.Colors.GREY_200,
        )

        # Classify events for the Tooltip popup
        exams = []
        studies = []
        personal = []
        tasks = []
        for ev in day_events:
            kind = ev.get("kind", "")
            ev_type = ev.get("event_type", "")
            if ev_type == "task" or kind == "task":
                tasks.append(ev)
            elif kind == "exam_schedule" or ev_type == "exam":
                exams.append(ev)
            elif kind == "study_schedule" or ev_type == "class":
                studies.append(ev)
            else:
                personal.append(ev)

        # Construct native tooltip multiline string (max 4 total events, categorized)
        tooltip_lines = []
        tooltip_lines.append(f"📅 {d.strftime('%d/%m/%Y')}")
        tooltip_lines.append("──────────────────────")

        max_tooltip_items = 4
        displayed_items = 0

        def _fmt_ev_time(starts, ends):
            return f"[{_fmt_time(starts)} - {_fmt_time(ends)}]"

        # 1. Exams
        if exams:
            tooltip_lines.append("【 LỊCH THI 】")
            for ev in exams:
                if displayed_items >= max_tooltip_items:
                    break
                tooltip_lines.append(f"• {_fmt_ev_time(ev.get('starts_at'), ev.get('ends_at'))} {ev['title']}")
                displayed_items += 1

        # 2. Studies
        if studies:
            if displayed_items < max_tooltip_items:
                if exams:
                    tooltip_lines.append("──────────────────────")
                tooltip_lines.append("【 LỊCH HỌC 】")
                for ev in studies:
                    if displayed_items >= max_tooltip_items:
                        break
                    tooltip_lines.append(f"• {_fmt_ev_time(ev.get('starts_at'), ev.get('ends_at'))} {ev['title']}")
                    displayed_items += 1

        # 3. Personal
        if personal:
            if displayed_items < max_tooltip_items:
                if exams or studies:
                    tooltip_lines.append("──────────────────────")
                tooltip_lines.append("【 LỊCH TỰ ĐẶT 】")
                for ev in personal:
                    if displayed_items >= max_tooltip_items:
                        break
                    tooltip_lines.append(f"• {_fmt_ev_time(ev.get('starts_at'), ev.get('ends_at'))} {ev['title']}")
                    displayed_items += 1

        # 4. Tasks
        overdue_tasks = []
        due_today_tasks = []
        todo_tasks = []
        for ev in tasks:
            status = ev.get("status", "")
            ev_date = _event_vn_date(ev)
            if status == "open" and ev_date < today:
                overdue_tasks.append(ev)
            elif status == "open" and ev_date == today:
                due_today_tasks.append(ev)
            else:
                todo_tasks.append(ev)

        def _append_task_group(label: str, group: List[Dict[str, Any]]) -> None:
            nonlocal displayed_items
            if not group or displayed_items >= max_tooltip_items:
                return
            if exams or studies or personal or displayed_items > 0:
                tooltip_lines.append("──────────────────────")
            tooltip_lines.append(f"【 {label} 】")
            for ev in group:
                if displayed_items >= max_tooltip_items:
                    break
                status = ev.get("status", "")
                prefix = "✅" if status == "completed" else "▫️"
                tooltip_lines.append(f"{prefix} {ev['title']}")
                displayed_items += 1

        _append_task_group("VIỆC TRỄ HẠN", overdue_tasks)
        _append_task_group("VIỆC ĐẾN HẠN HÔM NAY", due_today_tasks)
        _append_task_group("VIỆC CẦN LÀM", todo_tasks)

        total_evs = len(exams) + len(studies) + len(personal) + len(tasks)
        hidden_count = total_evs - displayed_items
        if hidden_count > 0:
            tooltip_lines.append(f"+ {hidden_count} mục khác...")

        tooltip_str = "\n".join(tooltip_lines) if total_evs > 0 else f"📅 {d.strftime('%d/%m/%Y')}\n(Không có lịch)"

        def on_day_cell_click(e):
            state["selected_date"] = d
            if on_day_click:
                try:
                    on_day_click(d)
                except Exception as ex:
                    print(f"[CalendarView] Day click callback error: {ex}")
                    page.open(ft.SnackBar(ft.Text(f"Không mở được ngày đã chọn: {ex}"), bgcolor="red"))
                    if root.page:
                        page.update()

        # Return a single Container with the native tooltip
        return ft.Container(
            content=content_col,
            padding=4,
            bgcolor=theme.get("primary_light", ft.Colors.PINK_50) if is_today else ft.Colors.WHITE,
            border=border,
            on_click=on_day_cell_click,
            expand=True,
            height=100,
            tooltip=ft.Tooltip(
                message=tooltip_str,
                prefer_below=True,
                vertical_offset=60,
                bgcolor=ft.Colors.BLUE_GREY_900,
                text_style=ft.TextStyle(color=ft.Colors.WHITE, size=11),
                padding=8,
                border_radius=6,
            ),
        )

    def _fmt_time(ts) -> str:
        if ts is None:
            return ""
        if hasattr(ts, "strftime"):
            VN_TZ = timezone(timedelta(hours=7))
            if ts.tzinfo is not None:
                ts = ts.astimezone(VN_TZ)
            return ts.strftime("%H:%M")
        return str(ts)[:5]

    # Pre-calculate heights & offsets for scroll position detection
    # Month Header = 50px, Week Row = 100px, ListView spacing = 2px between items
    item_offsets = []
    current_offset = 0.0
    spacing = 2.0

    for year, month in sorted_months:
        header_key = f"header_{year}_{month:02d}"
        item_offsets.append({
            "key": header_key,
            "offset": current_offset,
            "type": "header",
            "month": (year, month),
            "dates": [],
        })
        current_offset += 50.0 + spacing

        cal = calendar.monthcalendar(year, month)
        for w_idx, week in enumerate(cal):
            week_key = f"week_{year}_{month:02d}_{w_idx}"
            # Extract actual dates inside this month for this week
            week_dates = []
            for day in week:
                if day != 0:
                    week_dates.append(date(year, month, day))

            item_offsets.append({
                "key": week_key,
                "offset": current_offset,
                "type": "week",
                "month": (year, month),
                "dates": week_dates,
            })
            current_offset += 100.0 + spacing

    # Helper to find week row by date
    def _get_week_key(d: date) -> str | None:
        for item in item_offsets:
            if item["type"] == "week" and d in item["dates"]:
                return item["key"]
        return None

    # ------------------------------------------------------------------ #
    # Scroll handling & Mini-Nav Sync                                      #
    # ------------------------------------------------------------------ #
    def on_calendar_scroll(e: ft.OnScrollEvent):
        pixels = e.pixels
        viewport_dim = e.viewport_dimension if e.viewport_dimension else 700.0

        # Apply a scroll detection threshold to account for cumulative layout errors
        # and only trigger when a row is substantially scrolled into view
        viewport_start = pixels + 30.0
        viewport_end = pixels + viewport_dim - 30.0

        visible_dates = set()
        visible_week_keys = []
        primary_month = None

        for item in item_offsets:
            item_top = item["offset"]
            item_h = 50.0 if item["type"] == "header" else 100.0
            item_bottom = item_top + item_h

            # Check overlap
            if item_bottom >= viewport_start and item_top <= viewport_end:
                if item["type"] == "week":
                    visible_week_keys.append(item["key"])
                    for d in item["dates"]:
                        visible_dates.add(d)

                # Find the primary visible month at the top of the viewport
                # We use raw pixels (without threshold) for header month changes
                if primary_month is None and item_bottom > pixels:
                    primary_month = item["month"]

        # Throttle update: only rebuild mini-nav if the visible weeks changed
        weeks_hash = ",".join(visible_week_keys)
        state["visible_dates"] = visible_dates
        if weeks_hash == state["last_visible_weeks_hash"]:
            return
        state["last_visible_weeks_hash"] = weeks_hash

        if primary_month:
            yr, mo = primary_month
            header_label.value = f"THÁNG {mo:02d} / {yr}"
            if header_label.page:
                header_label.update()

            new_nav_month = datetime(yr, mo, 1)
            if state["mini_nav_month"].year != yr or state["mini_nav_month"].month != mo:
                state["mini_nav_month"] = new_nav_month
                _build_mini_nav()
                if mini_month_label.page:
                    mini_month_label.update()
                if mini_navigator_container.page:
                    mini_navigator_container.update()
            else:
                _build_mini_nav()
                if mini_navigator_container.page:
                    mini_navigator_container.update()

    # ListView of flat controls (headers + week rows)
    calendar_list_view = ft.ListView(
        expand=True,
        spacing=2,
        padding=0,
        on_scroll=on_calendar_scroll,
    )

    def _fill_calendar_list_view():
        calendar_list_view.controls.clear()
        for year, month in sorted_months:
            header_key = f"header_{year}_{month:02d}"
            # Month divider at top of header
            calendar_list_view.controls.append(
                ft.Container(
                    key=header_key,
                    height=50,
                    padding=ft.padding.only(top=10, bottom=5, left=10, right=10),
                    alignment=ft.alignment.center_left,
                    content=ft.Column(
                        [
                            ft.Divider(height=1, color=ft.Colors.GREY_300),
                            ft.Container(height=4),
                            ft.Text(
                                f"THÁNG {month:02d} / {year}",
                                size=14,
                                weight="bold",
                                color=theme.get("primary", ft.Colors.PINK_600),
                            ),
                        ],
                        spacing=0,
                    ),
                )
            )

            # Weeks of this month via calendar.monthcalendar
            cal = calendar.monthcalendar(year, month)
            for w_idx, week in enumerate(cal):
                row_controls = []
                for day in week:
                    if day == 0:
                        row_controls.append(_build_empty_day_cell())
                    else:
                        d_obj = date(year, month, day)
                        row_controls.append(_build_day_cell(d_obj, month))

                calendar_list_view.controls.append(
                    ft.Container(
                        key=f"week_{year}_{month:02d}_{w_idx}",
                        height=100,
                        content=ft.Row(row_controls, spacing=2),
                    )
                )

    _fill_calendar_list_view()

    # ------------------------------------------------------------------ #
    # Rebuild calendar (called after source toggle)                        #
    # ------------------------------------------------------------------ #
    def _rebuild_calendar():
        _reload_events()
        _fill_calendar_list_view()
        if root.page:
            page.update()

    def _refresh_calendar(e=None):
        _reload_sources()
        _build_sources_col()
        _reload_events()
        _fill_calendar_list_view()
        if root.page:
            page.update()

    # ------------------------------------------------------------------ #
    # Scroll to today                                                      #
    # ------------------------------------------------------------------ #
    def _scroll_to_today(e=None):
        _scroll_to_date(today)

    # ------------------------------------------------------------------ #
    # Mini month navigator                                                 #
    # ------------------------------------------------------------------ #
    mini_month_label = ft.Text("", size=13, weight="bold")

    mini_navigator_container = ft.Column(spacing=15)

    def _build_mini_nav(visible_dates=None):
        if visible_dates is not None:
            state["visible_dates"] = visible_dates
        visible_dates = state["visible_dates"]

        # Determine unique visible months chronologically, always maintaining exactly 2 months
        if not visible_dates:
            main_y, main_m = state["mini_nav_month"].year, state["mini_nav_month"].month
            next_y = main_y
            next_m = main_m + 1
            if next_m > 12:
                next_m = 1
                next_y += 1
            visible_months = [(main_y, main_m), (next_y, next_m)]
        else:
            unique_months = sorted(list(set(
                (d.year, d.month) for d in visible_dates
            )))
            if len(unique_months) == 1:
                main_y, main_m = unique_months[0]
                prev_y = main_y
                prev_m = main_m - 1
                if prev_m < 1:
                    prev_m = 12
                    prev_y -= 1
                visible_months = [(prev_y, prev_m), (main_y, main_m)]
            else:
                # Always take the first 2 unique months to keep layout height fixed to exactly 2 months
                visible_months = unique_months[:2]

        # Update the main label to show the primary month of interest
        nav_dt = state["mini_nav_month"]
        mini_month_label.value = f"{nav_dt.strftime('%m/%Y')}"

        mini_navigator_container.controls.clear()

        # Build each visible month block
        for year, month in visible_months:
            month_controls = []

            # Month block header
            month_controls.append(
                ft.Container(
                    content=ft.Text(
                        f"Tháng {month:02d} / {year}",
                        size=12,
                        weight="bold",
                        color=theme.get("primary", ft.Colors.PINK_600),
                    ),
                    padding=ft.padding.only(left=2, bottom=4),
                )
            )

            # Day-of-week subheader row
            subheaders = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
            month_controls.append(
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(h, size=9, color=ft.Colors.GREY_600, weight="bold", text_align=ft.TextAlign.CENTER),
                            alignment=ft.alignment.center,
                            width=24,
                            height=24,
                        )
                        for h in subheaders
                    ],
                    spacing=2,
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            )

            # Build week rows using calendar.monthcalendar
            import calendar as cal_module
            cal = cal_module.monthcalendar(year, month)
            for week in cal:
                week_cells = []
                for day in week:
                    if day == 0:
                        week_cells.append(ft.Container(width=24, height=24))
                    else:
                        d = date(year, month, day)
                        is_today_d = (d == today)
                        is_sel = (d == state["selected_date"])
                        is_visible_on_screen = (d in visible_dates)

                        # Highlighting visible range in main calendar
                        bg = (
                            theme.get("primary_light", ft.Colors.PINK_50) if is_visible_on_screen
                            else (theme.get("today_bg", ft.Colors.RED_50) if is_today_d else None)
                        )
                        # Outline selected date
                        border = ft.border.all(1, theme.get("primary", ft.Colors.PINK_600)) if is_sel else None

                        txt_color = theme.get("primary", ft.Colors.PINK_600) if is_today_d else ft.Colors.BLACK87

                        def make_click(clicked_date=d):
                            def on_click(e):
                                _scroll_to_date(clicked_date)
                            return on_click

                        week_cells.append(
                            ft.Container(
                                content=ft.Text(
                                    str(day), size=10,
                                    weight="bold" if is_today_d else "normal",
                                    color=txt_color,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                bgcolor=bg,
                                border=border,
                                border_radius=4,
                                alignment=ft.alignment.center,
                                width=24,
                                height=24,
                                on_click=make_click(),
                                tooltip=d.strftime("%d/%m/%Y"),
                            )
                        )

                month_controls.append(
                    ft.Row(
                        week_cells,
                        spacing=2,
                        alignment=ft.MainAxisAlignment.CENTER,
                    )
                )

            # Append the whole month block to the mini column container
            mini_navigator_container.controls.append(
                ft.Column(
                    month_controls,
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )

    def _sync_mini_nav_to_date(d: date) -> None:
        state["selected_date"] = d
        state["mini_nav_month"] = datetime(d.year, d.month, 1)
        state["visible_dates"] = {d}
        _build_mini_nav()
        if mini_month_label.page:
            mini_month_label.update()
        if mini_navigator_container.page:
            mini_navigator_container.update()

    def _scroll_to_date(d: date, duration: int = 300) -> None:
        week_key = _get_week_key(d)
        try:
            if week_key:
                calendar_list_view.scroll_to(key=week_key, duration=duration)
            else:
                print(f"[CalendarView] No week key found for {d.isoformat()}")
        except Exception as ex:
            print(f"[CalendarView] Scroll to date error: {ex}")
        header_label.value = _visible_range_label(d)
        if header_label.page:
            header_label.update()
        _sync_mini_nav_to_date(d)
        if root.page:
            page.update()

    _build_mini_nav()

    def _prev_mini_month(e):
        m = state["mini_nav_month"]
        y, mo = m.year, m.month - 1
        if mo < 1:
            mo, y = 12, y - 1
        target_date = date(y, mo, 1)
        _scroll_to_date(target_date)

    def _next_mini_month(e):
        m = state["mini_nav_month"]
        y, mo = m.year, m.month + 1
        if mo > 12:
            mo, y = 1, y + 1
        target_date = date(y, mo, 1)
        _scroll_to_date(target_date)

    mini_nav_row = ft.Row(
        [
            ft.IconButton(ft.Icons.CHEVRON_LEFT, icon_size=16, on_click=_prev_mini_month),
            mini_month_label,
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_size=16, on_click=_next_mini_month),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    # ------------------------------------------------------------------ #
    # Source toggles sidebar                                               #
    # ------------------------------------------------------------------ #
    sources_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)

    def _open_source_manager_dialog(source_info):
        import os
        src_id = source_info["id"]
        try:
            versions = calendar_view_svc.get_source_versions(src_id)
        except Exception as ex:
            print(f"[CalendarView] Error loading source versions: {ex}")
            versions = []

        active_ver = None
        for v in versions:
            if v["status"] == "active":
                active_ver = v
                break
        if not active_ver and versions:
            active_ver = versions[0]

        file_name = active_ver["file_name"] if active_ver else "N/A"
        file_sha256 = active_ver["file_sha256"] if active_ver else "N/A"

        project_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        simulated_path = os.path.join(project_dir, "storage", "copied_calendars", file_name)

        name_tf = ft.TextField(
            label="Tên hiển thị nguồn lịch",
            value=source_info["display_name"],
            expand=True,
            height=45,
            text_size=14,
        )

        def handle_save_name(e):
            new_name = name_tf.value.strip()
            if not new_name:
                return
            try:
                calendar_view_svc.update_source_name(src_id, new_name)
                _reload_sources()
                _build_sources_col()
                if sources_col.page:
                    sources_col.update()
                _rebuild_calendar()
                page.close(dlg)
                page.open(ft.SnackBar(ft.Text("Đã cập nhật tên nguồn lịch!"), bgcolor="green"))
            except Exception as ex:
                print(f"[CalendarView] Error updating source name: {ex}")
                page.open(ft.SnackBar(ft.Text(f"Lỗi: {ex}"), bgcolor="red"))

        def handle_pick_new_file(e):
            state["updating_source_id"] = src_id
            page.close(dlg)
            source_update_picker.pick_files(allow_multiple=False, allowed_extensions=["ics", "xlsx"])

        history_list = ft.Column(spacing=8, scroll="auto", height=180)
        if not versions:
            history_list.controls.append(ft.Text("Chưa có lịch sử nhập.", size=12, color="grey", italic=True))
        else:
            for v in versions:
                imp_dt = v["imported_at"]
                if isinstance(imp_dt, str):
                    try:
                        imp_dt = datetime.fromisoformat(imp_dt.replace("Z", "+00:00"))
                    except Exception:
                        pass
                date_str = imp_dt.strftime("%d/%m/%Y %H:%M:%S") if isinstance(imp_dt, datetime) else str(imp_dt)
                history_list.controls.append(
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=10, vertical=8),
                        bgcolor=ft.Colors.GREY_50,
                        border_radius=6,
                        border=ft.border.all(1, ft.Colors.GREY_200),
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.HISTORY, size=16, color=theme.get("primary", ft.Colors.PINK_600)),
                                ft.Column(
                                    [
                                        ft.Text(f"{v['source_display_name']}", size=12, weight="bold"),
                                        ft.Text(f"Thời gian: {date_str} (v{v['version_number']})", size=10, color=ft.Colors.GREY_600),
                                    ],
                                    spacing=2,
                                    expand=True
                                ),
                                ft.Container(
                                    content=ft.Text(v["status"].upper(), size=8, color="white", weight="bold"),
                                    bgcolor=ft.Colors.GREEN_600 if v["status"] == "active" else ft.Colors.GREY_500,
                                    padding=ft.padding.symmetric(horizontal=5, vertical=2),
                                    border_radius=3,
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        )
                    )
                )

        dlg = ft.AlertDialog(
            title=ft.Text("Quản lý Nguồn lịch", weight="bold"),
            content=ft.Container(
                width=500,
                height=450,
                content=ft.Column(
                    [
                        ft.Text("Cấu hình tên hiển thị:", size=12, weight="bold", color="grey"),
                        ft.Row(
                            [
                                name_tf,
                                ft.ElevatedButton(
                                    "Lưu",
                                    bgcolor=theme.get("primary", ft.Colors.PINK_600),
                                    color="white",
                                    on_click=handle_save_name
                                )
                            ],
                            spacing=10,
                        ),
                        ft.Divider(height=15),
                        ft.Text("Thông tin file hiện tại:", size=12, weight="bold", color="grey"),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.FILE_PRESENT, color=ft.Colors.BLUE_GREY),
                                ft.Column(
                                    [
                                        ft.Text(f"File gốc: {file_name}", size=13, weight="bold"),
                                        ft.Text(f"Vị trí: {simulated_path}", size=11, color="grey", overflow=ft.TextOverflow.ELLIPSIS),
                                        ft.Text(f"SHA-256: {file_sha256}", size=11, color="grey", overflow=ft.TextOverflow.ELLIPSIS),
                                    ],
                                    spacing=2,
                                    expand=True
                                )
                            ]
                        ),
                        ft.Row(
                            [
                                ft.OutlinedButton(
                                    "Cập nhật File mới...",
                                    icon=ft.Icons.UPLOAD_FILE,
                                    on_click=handle_pick_new_file
                                )
                            ],
                            alignment=ft.MainAxisAlignment.END
                        ),
                        ft.Divider(height=15),
                        ft.Text("Lịch sử nhập (mới nhất lên trước):", size=12, weight="bold", color="grey"),
                        history_list,
                    ],
                    scroll="auto",
                    spacing=10,
                )
            ),
            actions=[
                ft.TextButton("Đóng", on_click=lambda e: page.close(dlg))
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def _open_new_source_dialog(e=None):
        name_tf = ft.TextField(
            label="Tên nguồn lịch",
            hint_text="Ví dụ: Lịch cá nhân, Deadline môn học...",
            autofocus=True,
            text_size=14,
        )

        def handle_pick_file(ev):
            display_name = (name_tf.value or "").strip()
            if not display_name:
                name_tf.error_text = "Nhập tên nguồn lịch trước khi chọn file"
                name_tf.update()
                return
            state["new_source_name"] = display_name
            page.close(dlg)
            new_source_picker.pick_files(allow_multiple=False, allowed_extensions=["ics", "xlsx"])

        dlg = ft.AlertDialog(
            title=ft.Text("Thêm nguồn lịch", weight="bold"),
            content=ft.Container(
                width=420,
                content=ft.Column(
                    [
                        name_tf,
                        ft.Text(
                            "Hỗ trợ file .ics hoặc .xlsx. Nguồn mới sẽ hiện trong danh sách và được bật mặc định.",
                            size=12,
                            color=ft.Colors.GREY_600,
                        ),
                    ],
                    spacing=10,
                ),
            ),
            actions=[
                ft.TextButton("Hủy", on_click=lambda ev: page.close(dlg)),
                ft.ElevatedButton(
                    "Chọn file",
                    icon=ft.Icons.UPLOAD_FILE,
                    bgcolor=theme.get("primary", ft.Colors.PINK_600),
                    color="white",
                    on_click=handle_pick_file,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def _build_sources_col():
        sources_col.controls.clear()
        for src in state["sources"]:
            src_id = src["id"]
            src_color = _parse_hex_color(src.get("color", ""))
            is_vis = src.get("is_visible", True)

            def make_toggle(s_id=src_id):
                def on_change(e):
                    try:
                        calendar_view_svc.toggle_source_visibility(s_id, e.control.value)
                    except Exception as ex:
                        print(f"[CalendarView] Toggle source error: {ex}")
                    _rebuild_calendar()
                    _reload_sources()
                    _build_sources_col()
                    sources_col.update()
                return on_change

            def make_open_manager(source_info=src):
                return lambda e: _open_source_manager_dialog(source_info)

            chip_dot = ft.Container(
                width=10, height=10,
                border_radius=5,
                bgcolor=src_color,
            )
            src_name_container = ft.Container(
                            content=ft.Text(
                                src["display_name"],
                                size=13,
                                color=ft.Colors.BLACK87,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            on_click=make_open_manager(),
                            expand=True,
                        )
            src_name_container.mouse_cursor = ft.MouseCursor.CLICK
            sources_col.controls.append(
                ft.Row(
                    [
                        chip_dot,
                        ft.Checkbox(
                            value=is_vis,
                            on_change=make_toggle(),
                        ),
                        src_name_container
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )

    _build_sources_col()

    # ------------------------------------------------------------------ #
    # Week header row (day-of-week labels)                                 #
    # ------------------------------------------------------------------ #
    dow_labels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    week_header_row = ft.Row(
        [
            ft.Container(
                content=ft.Text(
                    lbl, size=11, weight="bold",
                    color=ft.Colors.GREY_700,
                    text_align=ft.TextAlign.CENTER,
                ),
                expand=True,
                alignment=ft.alignment.center,
                height=24,
            )
            for lbl in dow_labels
        ],
        spacing=2,
    )

    # ------------------------------------------------------------------ #
    # Assemble sidebar                                                     #
    # ------------------------------------------------------------------ #
    source_header = ft.Row(
        [
            ft.Text("Nguồn lịch", size=12, weight="bold", color=ft.Colors.GREY_700),
            ft.Container(expand=True),
            ft.IconButton(
                ft.Icons.ADD,
                icon_size=16,
                tooltip="Thêm nguồn lịch",
                on_click=_open_new_source_dialog,
            ),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    sources_scroll = ft.Container(
        content=sources_col,
        height=220,
    )
    sidebar = ft.Container(
        width=220,
        bgcolor=ft.Colors.GREY_50,
        border=ft.border.only(right=ft.border.BorderSide(1, ft.Colors.GREY_200)),
        padding=10,
        content=ft.Column(
            [
                mini_nav_row,
                mini_navigator_container,
                ft.Divider(height=12),
                source_header,
                sources_scroll,
            ],
            spacing=6,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    # ------------------------------------------------------------------ #
    # Main area: header + week-header + scrollable ListView               #
    # ------------------------------------------------------------------ #
    main_header = ft.Row(
        [
            header_label,
            ft.Container(expand=True),
            ft.IconButton(
                ft.Icons.REFRESH,
                icon_size=18,
                tooltip="Làm mới lịch",
                on_click=_refresh_calendar,
            ),
            ft.OutlinedButton(
                "Hôm nay",
                icon=ft.Icons.CALENDAR_TODAY,
                on_click=_scroll_to_today,
                style=ft.ButtonStyle(
                    color=theme.get("primary", ft.Colors.PINK_600),
                ),
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    main_area = ft.Container(
        expand=True,
        bgcolor=ft.Colors.WHITE,
        padding=ft.padding.symmetric(horizontal=8, vertical=8),
        content=ft.Column(
            [
                main_header,
                ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                week_header_row,
                ft.Divider(height=4, color=ft.Colors.GREY_200),
                calendar_list_view,
            ],
            expand=True,
            spacing=0,
        ),
    )

    # ------------------------------------------------------------------ #
    # Root container                                                       #
    # ------------------------------------------------------------------ #
    root = ft.Row(
        [sidebar, main_area],
        spacing=0,
        expand=True,
    )

    # Attach helper to trigger scroll from parent tabs container
    root.scroll_to_today = _scroll_to_today
    root.refresh_calendar = _refresh_calendar

    return root

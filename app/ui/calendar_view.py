"""
calendar_view.py — WS6: Continuous Calendar UI component.

Renders an Outlook-style scrollable multi-week calendar with:
- Left sidebar: mini month navigator + source visibility checkboxes
- Main area:    ListView of week rows, scrollable continuously

Usage:
    from app.ui.calendar_view import build_continuous_calendar_tab
    tab_content = build_continuous_calendar_tab(page, calendar_view_svc, THEME, COLOR_MAP)
"""
import flet as ft
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Any

from app.services.calendar_view_service import CalendarViewService


# ---------------------------------------------------------------------------
# Week helpers (Appendix B)
# ---------------------------------------------------------------------------

def get_week_start(d: date) -> date:
    """Returns the Monday of the week containing d. weekday(): Mon=0, Sun=6."""
    return d - timedelta(days=d.weekday())


def generate_week_rows(center: date, before: int = 8, after: int = 8) -> List[List[date]]:
    """
    Returns a list of [7 dates] lists.
    Total rows = before + 1 + after (17 by default).
    """
    start = get_week_start(center) - timedelta(weeks=before)
    return [
        [start + timedelta(weeks=w, days=d) for d in range(7)]
        for w in range(before + 1 + after)
    ]


def _parse_hex_color(hex_color: str) -> str:
    """
    Convert '#RRGGBB' or 'RRGGBB' to a Flet-compatible color string.
    Falls back to ft.Colors.GREY if parsing fails.
    """
    if not hex_color:
        return ft.Colors.GREY_400
    h = hex_color.strip().lstrip("#")
    if len(h) == 6:
        try:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"#{h.upper()}"
        except ValueError:
            pass
    return ft.Colors.GREY_400


# ---------------------------------------------------------------------------
# Main builder function
# ---------------------------------------------------------------------------

def build_continuous_calendar_tab(
    page: ft.Page,
    calendar_view_svc: CalendarViewService,
    theme: dict,
    color_map: dict,
) -> ft.Control:
    """
    Returns an ft.Row containing:
    - sidebar (width≈220px): mini month nav + source checkboxes
    - main area (expand): header row + scrollable week ListView
    """
    today = date.today()

    # ------------------------------------------------------------------ #
    # Mutable state                                                        #
    # ------------------------------------------------------------------ #
    state = {
        "mini_nav_month": datetime(today.year, today.month, 1),
        "selected_date": today,
        "events_cache": {},          # date_iso → List[dict]
        "sources": [],
    }

    # ------------------------------------------------------------------ #
    # Prefetch events from PG for visible range (±8 weeks)               #
    # ------------------------------------------------------------------ #
    def _reload_events():
        weeks = generate_week_rows(today, before=8, after=8)
        range_start_d = weeks[0][0]
        range_end_d = weeks[-1][-1]
        # Convert to UTC datetime for PG query (ends_at <= end of last day)
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
                # Convert to VN date
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
    # Header label (month/year of visible range)                          #
    # ------------------------------------------------------------------ #
    header_label = ft.Text(
        _visible_range_label(today),
        size=18,
        weight="bold",
        color=theme.get("primary", ft.Colors.PINK_600),
    )

    def _visible_range_label(center_date: date) -> str:
        return f"THÁNG {center_date.month:02d} / {center_date.year}"

    # ------------------------------------------------------------------ #
    # Build a single day cell                                              #
    # ------------------------------------------------------------------ #
    def _build_day_cell(d: date, display_month: int) -> ft.Control:
        is_today = (d == today)
        is_other_month = (d.month != display_month)

        day_key = d.isoformat()
        day_events = state["events_cache"].get(day_key, [])

        # Number display
        num_color = (
            ft.Colors.GREY_400 if is_other_month
            else (theme.get("primary", ft.Colors.PINK_600) if is_today else ft.Colors.BLACK87)
        )
        num_weight = "bold" if is_today else "normal"

        day_num_container = ft.Container(
            padding=ft.padding.symmetric(horizontal=4, vertical=2),
            border_radius=16,
            bgcolor=theme.get("today_bg", ft.Colors.RED_50) if is_today else None,
            content=ft.Text(str(d.day), size=12, weight=num_weight, color=num_color),
        )

        content_col = ft.Column(
            [ft.Row([day_num_container, ft.Container(expand=True)])],
            spacing=2,
            alignment=ft.MainAxisAlignment.START,
        )

        # Event chips (max 3, then +N...)
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
                tooltip=f"{ev['title']}\n{_fmt_time(ev.get('starts_at'))} – {_fmt_time(ev.get('ends_at'))}",
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
            theme.get("today_border", ft.Colors.RED_400) if is_today else ft.Colors.GREY_200,
        )

        return ft.Container(
            content=content_col,
            expand=True,
            height=100,
            padding=4,
            bgcolor=theme.get("today_bg", ft.Colors.RED_50) if is_today else ft.Colors.WHITE,
            border=border,
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

    # ------------------------------------------------------------------ #
    # Build week rows                                                      #
    # ------------------------------------------------------------------ #
    weeks = generate_week_rows(today, before=8, after=8)
    # For header tracking: detect "display_month" from center week
    center_week_monday = get_week_start(today)

    def _build_week_row(week_days: List[date]) -> ft.Control:
        # Use the Wednesday of the week as the representative month
        rep_month = week_days[2].month if len(week_days) > 2 else week_days[0].month
        return ft.Row(
            [_build_day_cell(d, rep_month) for d in week_days],
            spacing=2,
        )

    # ListView of week rows
    calendar_list_view = ft.ListView(
        expand=True,
        spacing=2,
        padding=0,
    )

    for week_days in weeks:
        monday = week_days[0]
        calendar_list_view.controls.append(
            ft.Container(
                key=monday.isoformat(),
                content=_build_week_row(week_days),
            )
        )

    # ------------------------------------------------------------------ #
    # Rebuild calendar (called after source toggle)                        #
    # ------------------------------------------------------------------ #
    def _rebuild_calendar():
        _reload_events()
        calendar_list_view.controls.clear()
        for week_days in weeks:
            monday = week_days[0]
            calendar_list_view.controls.append(
                ft.Container(
                    key=monday.isoformat(),
                    content=_build_week_row(week_days),
                )
            )
        calendar_list_view.update()

    # ------------------------------------------------------------------ #
    # Scroll to today                                                      #
    # ------------------------------------------------------------------ #
    def _scroll_to_today(e=None):
        monday_key = get_week_start(today).isoformat()
        try:
            calendar_list_view.scroll_to(key=monday_key, duration=300)
        except Exception:
            pass
        header_label.value = _visible_range_label(today)
        header_label.update()
        page.update()

    # ------------------------------------------------------------------ #
    # Mini month navigator                                                 #
    # ------------------------------------------------------------------ #
    mini_month_label = ft.Text("", size=13, weight="bold")

    mini_grid = ft.GridView(
        runs_count=7,
        max_extent=28,
        spacing=2,
        run_spacing=2,
    )

    def _build_mini_nav():
        nav_dt = state["mini_nav_month"]
        mini_month_label.value = f"{nav_dt.strftime('%m/%Y')}"
        mini_grid.controls.clear()

        # Day-of-week headers
        for h in ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]:
            mini_grid.controls.append(
                ft.Container(
                    content=ft.Text(h, size=9, color=ft.Colors.GREY_600, text_align=ft.TextAlign.CENTER),
                    alignment=ft.alignment.center,
                )
            )

        # Blank cells before the 1st
        first_day = date(nav_dt.year, nav_dt.month, 1)
        # weekday(): Mon=0 → skip 0, Tue=1 → skip 1, etc.
        for _ in range(first_day.weekday()):
            mini_grid.controls.append(ft.Container())

        # Day cells
        import calendar as cal_module
        _, days_in_month = cal_module.monthrange(nav_dt.year, nav_dt.month)
        for day_n in range(1, days_in_month + 1):
            d = date(nav_dt.year, nav_dt.month, day_n)
            is_today_d = (d == today)
            is_sel = (d == state["selected_date"])
            bg = theme.get("today_bg", ft.Colors.RED_50) if is_today_d else (
                ft.Colors.PINK_100 if is_sel else None
            )
            txt_color = theme.get("primary", ft.Colors.PINK_600) if is_today_d else ft.Colors.BLACK87

            def make_click(clicked_date=d):
                def on_click(e):
                    state["selected_date"] = clicked_date
                    monday_key = get_week_start(clicked_date).isoformat()
                    header_label.value = _visible_range_label(clicked_date)
                    header_label.update()
                    try:
                        calendar_list_view.scroll_to(key=monday_key, duration=300)
                    except Exception:
                        pass
                    _build_mini_nav()
                    mini_month_label.update()
                    mini_grid.update()
                    page.update()
                return on_click

            mini_grid.controls.append(
                ft.Container(
                    content=ft.Text(
                        str(day_n), size=10,
                        weight="bold" if is_today_d else "normal",
                        color=txt_color,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    bgcolor=bg,
                    border_radius=4,
                    alignment=ft.alignment.center,
                    on_click=make_click(),
                    tooltip=d.strftime("%d/%m/%Y"),
                )
            )

    _build_mini_nav()

    def _prev_mini_month(e):
        m = state["mini_nav_month"]
        y, mo = m.year, m.month - 1
        if mo < 1:
            mo, y = 12, y - 1
        state["mini_nav_month"] = datetime(y, mo, 1)
        _build_mini_nav()
        mini_month_label.update()
        mini_grid.update()

    def _next_mini_month(e):
        m = state["mini_nav_month"]
        y, mo = m.year, m.month + 1
        if mo > 12:
            mo, y = 1, y + 1
        state["mini_nav_month"] = datetime(y, mo, 1)
        _build_mini_nav()
        mini_month_label.update()
        mini_grid.update()

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
    sources_col = ft.Column(spacing=6)

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

            chip_dot = ft.Container(
                width=10, height=10,
                border_radius=5,
                bgcolor=src_color,
            )
            sources_col.controls.append(
                ft.Row(
                    [
                        chip_dot,
                        ft.Checkbox(
                            value=is_vis,
                            on_change=make_toggle(),
                            label=src["display_name"],
                        ),
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
    sidebar = ft.Container(
        width=220,
        bgcolor=ft.Colors.GREY_50,
        border=ft.border.only(right=ft.border.BorderSide(1, ft.Colors.GREY_200)),
        padding=10,
        content=ft.Column(
            [
                mini_nav_row,
                mini_grid,
                ft.Divider(height=12),
                ft.Text("Nguồn lịch", size=12, weight="bold", color=ft.Colors.GREY_700),
                sources_col,
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

    return root

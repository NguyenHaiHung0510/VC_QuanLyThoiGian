import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from ..exporters.planner_dto import (
    PlannerExportDTO,
    ExportMetadata,
    ExportEvent,
    ExportSubtask,
    ExportTask,
    ExportNoteItem,
    ExportNote,
)
from ..exporters.markdown_exporter import MarkdownExporter
from ..exporters.json_exporter import JSONExporter

class ExportService:
    def __init__(self):
        pass

    def _format_date(self, d) -> str:
        if not d:
            return ""
        if isinstance(d, (datetime, date)):
            return d.strftime("%Y-%m-%d")
        return str(d)[:10]

    def _format_time(self, dt) -> str:
        if not dt:
            return ""
        if isinstance(dt, datetime):
            return dt.strftime("%H:%M")
        # Nếu là chuỗi dạng HH:MM:SS
        dt_str = str(dt)
        if len(dt_str) >= 5 and ":" in dt_str:
            parts = dt_str.split(" ")
            time_part = parts[-1]
            return time_part[:5]
        return dt_str

    def _detect_conflicts(self, events: List[ExportEvent]) -> List[str]:
        # Nhóm events theo ngày
        events_by_day: Dict[str, List[ExportEvent]] = {}
        for event in events:
            if event.date_str:
                events_by_day.setdefault(event.date_str, []).append(event)

        warnings = []
        for day, day_events in events_by_day.items():
            # So sánh chéo các event trong ngày
            for i in range(len(day_events)):
                for j in range(i + 1, len(day_events)):
                    e1 = day_events[i]
                    e2 = day_events[j]

                    # Kiểm tra overlap thời gian
                    # e1.time_start < e2.time_end và e2.time_start < e1.time_end
                    if e1.time_start < e2.time_end and e2.time_start < e1.time_end:
                        warnings.append(
                            f"Trùng lịch ngày {day}: '{e1.subject}' ({e1.time_start}-{e1.time_end}) và '{e2.subject}' ({e2.time_start}-{e2.time_end})"
                        )
        return warnings

    def get_settings(self, conn) -> Dict[str, Any]:
        """Load settings từ bảng app_settings."""
        settings = {
            "export.default_format": "markdown",
            "export.include_notes": True,
            "export.include_completed": False,
            "export.lookahead_days": None
        }

        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT key, value_json FROM app_settings WHERE key LIKE 'export.%'"
                )
                rows = cur.fetchall()
                for key, val_json in rows:
                    try:
                        # Postgres jsonb có thể được psycopg tự động parse thành dict/list/value
                        # hoặc trả về dạng string
                        if isinstance(val_json, str):
                            settings[key] = json.loads(val_json)
                        else:
                            settings[key] = val_json
                    except Exception:
                        settings[key] = val_json
        except Exception:
            # Fallback nếu bảng chưa có hoặc lỗi kết nối
            pass

        return settings

    def generate_export_data(
        self,
        conn,
        threshold_dt: Optional[datetime] = None,
        settings_override: Optional[Dict[str, Any]] = None
    ) -> PlannerExportDTO:
        """
        Gom dữ liệu từ PostgreSQL database v2 và đóng gói thành PlannerExportDTO.
        """
        if threshold_dt is None:
            threshold_dt = datetime.now()

        threshold_iso = threshold_dt.strftime("%Y-%m-%d")

        # Load và merge settings
        db_settings = self.get_settings(conn)
        if settings_override:
            db_settings.update(settings_override)

        include_notes = db_settings.get("export.include_notes", True)
        include_completed = db_settings.get("export.include_completed", False)
        lookahead_days = db_settings.get("export.lookahead_days", None)

        # Thiết lập khoảng thời gian kết thúc (nếu có lookahead_days)
        end_date_str = None
        if lookahead_days is not None:
            try:
                end_dt = threshold_dt + timedelta(days=int(lookahead_days))
                end_date_str = end_dt.strftime("%Y-%m-%d")
            except Exception:
                pass

        # 1. GET CALENDAR EVENTS
        events: List[ExportEvent] = []
        try:
            with conn.cursor() as cur:
                query_events = """
                    SELECT e.title, e.starts_at, e.ends_at, e.location, e.event_type, s.display_name
                    FROM calendar_events e
                    JOIN calendar_sources s ON e.source_id = s.id
                    WHERE s.is_visible = TRUE
                      AND e.source_version_id = s.current_version_id
                      AND e.starts_at >= %s
                """
                params = [threshold_dt]

                if end_date_str:
                    query_events += " AND e.starts_at <= %s"
                    params.append(end_date_str)

                query_events += " ORDER BY e.starts_at ASC"

                cur.execute(query_events, params)
                rows = cur.fetchall()
                for title, starts_at, ends_at, location, event_type, source_name in rows:
                    events.append(
                        ExportEvent(
                            subject=title or "",
                            time_start=self._format_time(starts_at),
                            time_end=self._format_time(ends_at),
                            location=location or "",
                            date_str=self._format_date(starts_at),
                            source_name=source_name or "",
                            event_type=event_type or ""
                        )
                    )
        except Exception as e:
            # Log error hoặc reraise tùy thiết kế, tạm thời in ra console hoặc bỏ qua
            print(f"Error querying calendar events: {e}")

        # 2. GET TASKS
        tasks: List[ExportTask] = []
        try:
            with conn.cursor() as cur:
                # Điều kiện tasks:
                # - Task chưa hoàn thành (status != 'completed')
                # - HOẶC Task sắp tới (due_at >= threshold)
                # - HOẶC Task đã hoàn thành nếu include_completed = True
                query_tasks = """
                    SELECT t.id, t.title, t.note, p.name as priority, t.due_at, t.status, t.completed_at
                    FROM tasks t
                    LEFT JOIN priorities p ON t.priority_id = p.id
                    WHERE (t.status != 'completed')
                       OR (t.due_at >= %s)
                       OR (t.status = 'completed' AND %s = TRUE)
                """
                params = [threshold_iso, include_completed]

                if end_date_str:
                    query_tasks += " AND (t.due_at <= %s OR t.due_at IS NULL)"
                    params.append(end_date_str)

                query_tasks += " ORDER BY t.due_at ASC NULLS LAST"

                cur.execute(query_tasks, params)
                task_rows = cur.fetchall()

                for tid, title, note, priority, due_at, status, completed_at in task_rows:
                    # Lấy subtasks
                    cur.execute(
                        "SELECT content, is_completed FROM task_items WHERE task_id = %s ORDER BY position ASC, id ASC",
                        (tid,)
                    )
                    sub_rows = cur.fetchall()
                    subtasks_list = [ExportSubtask(content=c, is_completed=ic) for c, ic in sub_rows]

                    total_sub = len(subtasks_list)
                    done_sub = sum(1 for s in subtasks_list if s.is_completed == 1)

                    is_done = 1 if status == 'completed' else 0

                    # Xây dựng context_note
                    due_date_str = self._format_date(due_at)
                    if due_at and due_at < threshold_dt.date() and is_done == 0:
                        context_note = f"OVERDUE (Quá hạn). Tiến độ: {done_sub}/{total_sub}"
                    else:
                        context_note = f"UPCOMING. Tiến độ: {done_sub}/{total_sub}"

                    tasks.append(
                        ExportTask(
                            id=tid,
                            title=title or "",
                            is_completed=is_done,
                            priority=priority or "Nên làm",
                            date_str=due_date_str,
                            note=note,
                            subtasks_list=subtasks_list,
                            context_note=context_note
                        )
                    )
        except Exception as e:
            print(f"Error querying tasks: {e}")

        # 3. GET NOTES
        notes: List[ExportNote] = []
        if include_notes:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT n.id, n.title, n.body, n.pinned, p.name as priority
                        FROM notes n
                        LEFT JOIN priorities p ON n.priority_id = p.id
                        WHERE n.archived_at IS NULL
                        ORDER BY n.pinned DESC, n.updated_at DESC, n.id DESC
                        """
                    )
                    note_rows = cur.fetchall()
                    for nid, title, body, pinned, priority in note_rows:
                        # Lấy note items
                        cur.execute(
                            "SELECT content, is_done FROM note_items WHERE note_id = %s ORDER BY position ASC, id ASC",
                            (nid,)
                        )
                        item_rows = cur.fetchall()
                        note_items = [ExportNoteItem(content=c, is_done=idne) for c, idne in item_rows]

                        notes.append(
                            ExportNote(
                                id=nid,
                                title=title or "",
                                body=body,
                                pinned=pinned or 0,
                                priority=priority,
                                note_items=note_items
                            )
                        )
            except Exception as e:
                print(f"Error querying notes: {e}")

        # 4. DETECT WARNINGS
        warnings = self._detect_conflicts(events)

        # 5. METADATA
        metadata = ExportMetadata(
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            threshold_date=threshold_dt.strftime("%d/%m/%Y"),
            description="Dữ liệu dùng để lập kế hoạch ôn thi."
        )

        return PlannerExportDTO(
            metadata=metadata,
            schedule_events=events,
            todo_tasks=tasks,
            notes=notes,
            warnings=warnings
        )

    def export_to_string(
        self,
        conn,
        format_type: Optional[str] = None,
        threshold_dt: Optional[datetime] = None,
        settings_override: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Thực hiện xuất dữ liệu ra chuỗi (Markdown hoặc JSON) dựa trên tham số hoặc cấu hình.
        """
        dto = self.generate_export_data(conn, threshold_dt, settings_override)

        # Nếu format_type không được truyền, đọc từ settings
        if not format_type:
            db_settings = self.get_settings(conn)
            if settings_override:
                db_settings.update(settings_override)
            format_type = db_settings.get("export.default_format", "markdown")

        if format_type.lower() == "json":
            return JSONExporter.export(dto)
        else:
            return MarkdownExporter.export(dto)

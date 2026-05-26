"""
CalendarViewService — WS6: Query calendar_events by date range for the continuous calendar tab.

Prefetches events around the visible range and supports source visibility toggling.
"""
from datetime import datetime
from typing import List, Dict, Any


class CalendarViewService:
    def __init__(self, conn):
        """
        conn: psycopg2 connection (injected from main.py).
        """
        self.conn = conn

    def get_events_by_range(
        self, range_start: datetime, range_end: datetime
    ) -> List[Dict[str, Any]]:
        """
        Returns calendar_events in the given UTC datetime range (inclusive) PLUS active tasks.
        """
        query = """
            SELECT ce.id, ce.title, ce.location, ce.event_type,
                   ce.starts_at, ce.ends_at, ce.user_cancelled,
                   cs.color, cs.display_name, cs.id AS source_id,
                   cs.kind
            FROM calendar_events ce
            JOIN calendar_sources cs ON ce.source_id = cs.id
            WHERE ce.source_version_id = cs.current_version_id
              AND ce.status = 'active'
              AND ce.user_cancelled = false
              AND cs.is_visible = true
              AND ce.starts_at >= %(range_start)s
              AND ce.ends_at   <= %(range_end)s
            ORDER BY ce.starts_at ASC
        """
        events = []
        with self.conn.cursor() as cur:
            cur.execute(query, {"range_start": range_start, "range_end": range_end})
            for row in cur.fetchall():
                events.append({
                    "id": row[0],
                    "title": row[1],
                    "location": row[2],
                    "event_type": row[3],
                    "starts_at": row[4],
                    "ends_at": row[5],
                    "user_cancelled": row[6],
                    "color": row[7],
                    "display_name": row[8],
                    "source_id": row[9],
                    "kind": row[10],
                })

        # Fetch active tasks within the range (ignoring archived ones)
        try:
            query_tasks = """
                SELECT t.id, t.title, t.due_at, t.status, p.color
                FROM tasks t
                LEFT JOIN priorities p ON t.priority_id = p.id
                WHERE t.due_at >= %(range_start)s
                  AND t.due_at <= %(range_end)s
                  AND t.status <> 'archived'
            """
            color_hex_map = {
                "Grey": "#607d8b",
                "Green": "#4caf50",
                "Blue": "#2196f3",
                "Amber": "#ff8f00",
                "Orange": "#ff5722",
                "Red": "#b71c1c",
                "Purple": "#9c27b0",
                "Teal": "#009688",
                "Pink": "#e91e63",
            }
            with self.conn.cursor() as cur:
                cur.execute(query_tasks, {"range_start": range_start, "range_end": range_end})
                for row in cur.fetchall():
                    p_color_name = row[4] or "Grey"
                    color_hex = color_hex_map.get(p_color_name, "#607d8b")
                    events.append({
                        "id": row[0],
                        "title": row[1],
                        "location": "",
                        "event_type": "task",
                        "starts_at": row[2],
                        "ends_at": row[2],
                        "user_cancelled": False,
                        "color": color_hex,
                        "display_name": "Công việc",
                        "source_id": None,
                        "kind": "task",
                        "status": row[3]  # Keep task status to display correctly
                    })
        except Exception as ex:
            try:
                self.conn.rollback()
            except Exception:
                pass
            print(f"[CalendarViewService] Failed to load tasks (ignored in test/minimal schemas): {ex}")
        return events

    def get_active_sources(self) -> List[Dict[str, Any]]:
        """
        Returns all calendar sources (regardless of is_visible).
        Used to populate the sidebar source toggles.
        Dict: {id, display_name, color, is_visible, kind}
        """
        query = """
            SELECT id, display_name, color, is_visible, kind
            FROM calendar_sources
            WHERE current_version_id IS NOT NULL
            ORDER BY sort_start_date ASC NULLS LAST, display_name ASC
        """
        sources = []
        with self.conn.cursor() as cur:
            cur.execute(query)
            for row in cur.fetchall():
                sources.append({
                    "id": row[0],
                    "display_name": row[1],
                    "color": row[2],
                    "is_visible": row[3],
                    "kind": row[4],
                })
        return sources

    def toggle_source_visibility(self, source_id: str, is_visible: bool) -> None:
        """
        Sets is_visible on a calendar_source and commits.
        Per D5: this persists to DB so the filter survives restart.
        """
        query = """
            UPDATE calendar_sources
            SET is_visible = %s,
                updated_at = NOW()
            WHERE id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (is_visible, source_id))
            self.conn.commit()

    def update_source_name(self, source_id: str, new_name: str) -> None:
        """
        Updates the display name of a calendar source.
        """
        query = """
            UPDATE calendar_sources
            SET display_name = %s,
                updated_at = NOW()
            WHERE id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (new_name, source_id))
            self.conn.commit()

    def get_source_versions(self, source_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all version history for a given calendar source.
        """
        query = """
            SELECT csv.id, csv.version_number, csv.file_name, csv.file_sha256, csv.imported_at, csv.status, cs.display_name
            FROM calendar_source_versions csv
            JOIN calendar_sources cs ON csv.source_id = cs.id
            WHERE csv.source_id = %s
            ORDER BY csv.imported_at DESC
        """
        versions = []
        with self.conn.cursor() as cur:
            cur.execute(query, (source_id,))
            for row in cur.fetchall():
                versions.append({
                    "id": row[0],
                    "version_number": row[1],
                    "file_name": row[2],
                    "file_sha256": row[3],
                    "imported_at": row[4],
                    "status": row[5],
                    "source_display_name": row[6]
                })
        return versions

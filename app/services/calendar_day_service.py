"""
CalendarDayService — WS6: Query calendar_events from PostgreSQL for a specific day.

Used by the Day View tab (CHI TIẾT NGÀY) to show events and handle user_cancelled toggle.
"""
from datetime import date
from typing import List, Dict, Any, Optional


class CalendarDayService:
    def __init__(self, conn):
        """
        conn: psycopg2 connection (injected from main.py).
        """
        self.conn = conn

    def get_events_for_date(self, target_date: date) -> List[Dict[str, Any]]:
        """
        Returns calendar_events where:
        - source_version_id = cs.current_version_id  (only current import)
        - status = 'active'
        - user_cancelled = false
        - DATE(starts_at AT TIME ZONE 'Asia/Ho_Chi_Minh') = target_date
        - cs.is_visible = true

        Returns list of dicts:
        {id, title, location, event_type, starts_at, ends_at,
         color, display_name, source_id, user_cancelled}
        """
        query = """
            SELECT ce.id, ce.title, ce.location, ce.event_type,
                   ce.starts_at, ce.ends_at, ce.user_cancelled,
                   cs.color, cs.display_name, cs.id AS source_id
            FROM calendar_events ce
            JOIN calendar_sources cs ON ce.source_id = cs.id
            WHERE ce.source_version_id = cs.current_version_id
              AND ce.status = 'active'
              AND ce.user_cancelled = false
              AND cs.is_visible = true
              AND DATE(ce.starts_at AT TIME ZONE 'Asia/Ho_Chi_Minh') = %(date)s
            ORDER BY ce.starts_at ASC
        """
        events = []
        with self.conn.cursor() as cur:
            cur.execute(query, {"date": target_date})
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
                })
        return events

    def toggle_event_user_cancelled(self, event_id: str) -> bool:
        """
        Toggles user_cancelled on the given calendar_event.
        Returns the new value of user_cancelled (True = cancelled, False = active).
        """
        query = """
            UPDATE calendar_events
            SET user_cancelled = NOT user_cancelled,
                updated_at = NOW()
            WHERE id = %s
            RETURNING user_cancelled
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (event_id,))
            row = cur.fetchone()
            self.conn.commit()
            if not row:
                raise ValueError(f"Event {event_id} not found")
            return row[0]

    def mark_event_user_cancelled(self, event_id: str, cancelled: bool) -> None:
        """
        Explicitly sets user_cancelled = cancelled for an event.
        Used for the "delete" action on an imported event (per D11, no hard delete).
        """
        query = """
            UPDATE calendar_events
            SET user_cancelled = %s,
                updated_at = NOW()
            WHERE id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (cancelled, event_id))
            self.conn.commit()

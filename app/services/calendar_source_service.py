from typing import List, Dict, Any, Optional
from datetime import date

class CalendarSourceService:
    def __init__(self, conn):
        """
        Accepts a psycopg connection object for dependency injection.
        """
        self.conn = conn

    def list_sources(self) -> List[Dict[str, Any]]:
        """
        Lists all calendar sources, ordered by:
        1. sort_start_date ASC NULLS LAST
        2. academic_year
        3. term
        4. display_name
        """
        query = """
            SELECT id, display_name, kind, academic_year, term, sort_start_date, color, is_visible, current_version_id
            FROM calendar_sources
            ORDER BY sort_start_date ASC NULLS LAST, academic_year ASC NULLS LAST, term ASC NULLS LAST, display_name ASC
        """
        sources = []
        with self.conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            for row in rows:
                sources.append({
                    "id": row[0],
                    "display_name": row[1],
                    "kind": row[2],
                    "academic_year": row[3],
                    "term": row[4],
                    "sort_start_date": row[5] if row[5] else None,
                    "color": row[6],
                    "is_visible": row[7],
                    "current_version_id": row[8]
                })
        return sources

    def get_source_by_id(self, source_id) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single calendar source by ID.
        """
        query = """
            SELECT id, display_name, kind, academic_year, term, sort_start_date, color, is_visible, current_version_id
            FROM calendar_sources
            WHERE id = %s
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (source_id,))
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "display_name": row[1],
                    "kind": row[2],
                    "academic_year": row[3],
                    "term": row[4],
                    "sort_start_date": row[5],
                    "color": row[6],
                    "is_visible": row[7],
                    "current_version_id": row[8]
                }
        return None

    def create_source(
        self,
        display_name: str,
        kind: str,
        academic_year: Optional[int] = None,
        term: Optional[str] = None,
        sort_start_date: Optional[date] = None,
        color: Optional[str] = None,
        is_visible: bool = True
    ) -> Dict[str, Any]:
        """
        Creates a new calendar source.
        """
        color = color or "#2563eb"
        query = """
            INSERT INTO calendar_sources (display_name, kind, academic_year, term, sort_start_date, color, is_visible)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, display_name, kind, academic_year, term, sort_start_date, color, is_visible, current_version_id
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (display_name, kind, academic_year, term, sort_start_date, color, is_visible))
            row = cur.fetchone()
            self.conn.commit()
            return {
                "id": row[0],
                "display_name": row[1],
                "kind": row[2],
                "academic_year": row[3],
                "term": row[4],
                "sort_start_date": row[5],
                "color": row[6],
                "is_visible": row[7],
                "current_version_id": row[8]
            }

    def update_source(
        self,
        source_id,
        display_name: Optional[str] = None,
        kind: Optional[str] = None,
        academic_year: Optional[int] = None,
        term: Optional[str] = None,
        sort_start_date: Optional[date] = None,
        color: Optional[str] = None,
        is_visible: Optional[bool] = None,
        current_version_id = None
    ) -> Dict[str, Any]:
        """
        Updates an existing calendar source with provided fields.
        """
        updates = []
        params = []

        fields = {
            "display_name": display_name,
            "kind": kind,
            "academic_year": academic_year,
            "term": term,
            "sort_start_date": sort_start_date,
            "color": color,
            "is_visible": is_visible,
            "current_version_id": current_version_id,
            "updated_at": "now()"  # Automatically set update time
        }

        for field_name, value in fields.items():
            if value is not None:
                if field_name == "updated_at":
                    updates.append("updated_at = NOW()")
                else:
                    updates.append(f"{field_name} = %s")
                    params.append(value)

        if not updates:
            # Nothing to update, just return the current state
            source = self.get_source_by_id(source_id)
            if not source:
                raise ValueError(f"Source with id {source_id} not found.")
            return source

        params.append(source_id)
        query = f"""
            UPDATE calendar_sources
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, display_name, kind, academic_year, term, sort_start_date, color, is_visible, current_version_id
        """
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            if not row:
                self.conn.rollback()
                raise ValueError(f"Source with id {source_id} not found.")
            self.conn.commit()
            return {
                "id": row[0],
                "display_name": row[1],
                "kind": row[2],
                "academic_year": row[3],
                "term": row[4],
                "sort_start_date": row[5],
                "color": row[6],
                "is_visible": row[7],
                "current_version_id": row[8]
            }

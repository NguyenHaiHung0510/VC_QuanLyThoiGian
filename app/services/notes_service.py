from typing import List, Dict, Any, Optional
from datetime import datetime
import psycopg

class NotesService:
    def __init__(self, conn: psycopg.Connection):
        """
        Accepts a psycopg connection object for dependency injection.
        """
        self.conn = conn

    def list_priorities(self) -> List[Dict[str, Any]]:
        """
        Lists all priority definitions from priorities table.
        """
        query = """
            SELECT id, name, label, color, icon, sort_order
            FROM priorities
            ORDER BY sort_order ASC
        """
        priorities = []
        try:
            with self.conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                for row in rows:
                    priorities.append({
                        "id": str(row[0]),
                        "name": row[1],
                        "label": row[2],
                        "color": row[3],
                        "icon": row[4],
                        "sort_order": row[5]
                    })
        except Exception as e:
            print(f"Error listing priorities: {e}")
        return priorities

    def list_notes(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """
        Lists notes sorted by:
        1. pinned DESC
        2. updated_at DESC
        """
        if include_archived:
            query = """
                SELECT n.id, n.title, n.body, n.priority_id, n.pinned, n.archived_at, n.created_at, n.updated_at,
                       p.name as priority_name, p.label as priority_label, p.color as priority_color, p.icon as priority_icon
                FROM notes n
                LEFT JOIN priorities p ON n.priority_id = p.id
                ORDER BY n.pinned DESC, n.updated_at DESC
            """
            params = ()
        else:
            query = """
                SELECT n.id, n.title, n.body, n.priority_id, n.pinned, n.archived_at, n.created_at, n.updated_at,
                       p.name as priority_name, p.label as priority_label, p.color as priority_color, p.icon as priority_icon
                FROM notes n
                LEFT JOIN priorities p ON n.priority_id = p.id
                WHERE n.archived_at IS NULL
                ORDER BY n.pinned DESC, n.updated_at DESC
            """
            params = ()

        notes = []
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                for row in rows:
                    notes.append({
                        "id": str(row[0]),
                        "title": row[1],
                        "body": row[2] if row[2] else "",
                        "priority_id": str(row[3]) if row[3] else None,
                        "pinned": bool(row[4]),
                        "archived_at": row[5].isoformat() if row[5] else None,
                        "created_at": row[6].isoformat() if row[6] else None,
                        "updated_at": row[7].isoformat() if row[7] else None,
                        "priority_name": row[8],
                        "priority_label": row[9],
                        "priority_color": row[10],
                        "priority_icon": row[11],
                        "note_items": self.list_note_items(str(row[0]))
                    })
        except Exception as e:
            print(f"Error listing notes: {e}")
        return notes

    def get_note_by_id(self, note_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single note by ID along with its note items.
        """
        query = """
            SELECT n.id, n.title, n.body, n.priority_id, n.pinned, n.archived_at, n.created_at, n.updated_at,
                   p.name as priority_name, p.label as priority_label, p.color as priority_color, p.icon as priority_icon
            FROM notes n
            LEFT JOIN priorities p ON n.priority_id = p.id
            WHERE n.id = %s
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, (note_id,))
                row = cur.fetchone()
                if row:
                    return {
                        "id": str(row[0]),
                        "title": row[1],
                        "body": row[2] if row[2] else "",
                        "priority_id": str(row[3]) if row[3] else None,
                        "pinned": bool(row[4]),
                        "archived_at": row[5].isoformat() if row[5] else None,
                        "created_at": row[6].isoformat() if row[6] else None,
                        "updated_at": row[7].isoformat() if row[7] else None,
                        "priority_name": row[8],
                        "priority_label": row[9],
                        "priority_color": row[10],
                        "priority_icon": row[11],
                        "note_items": self.list_note_items(note_id)
                    }
        except Exception as e:
            print(f"Error getting note by id: {e}")
        return None

    def create_note(
        self,
        title: str,
        body: Optional[str] = None,
        priority_id: Optional[str] = None,
        pinned: bool = False
    ) -> Dict[str, Any]:
        """
        Creates a new note in PostgreSQL.
        """
        query = """
            INSERT INTO notes (title, body, priority_id, pinned, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            RETURNING id, title, body, priority_id, pinned, archived_at, created_at, updated_at
        """
        # Convert empty strings to None for UUID priority_id
        p_id = priority_id if priority_id else None
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, (title, body, p_id, pinned))
                row = cur.fetchone()
                self.conn.commit()
                return {
                    "id": str(row[0]),
                    "title": row[1],
                    "body": row[2] if row[2] else "",
                    "priority_id": str(row[3]) if row[3] else None,
                    "pinned": bool(row[4]),
                    "archived_at": row[5].isoformat() if row[5] else None,
                    "created_at": row[6].isoformat() if row[6] else None,
                    "updated_at": row[7].isoformat() if row[7] else None,
                    "note_items": []
                }
        except Exception as e:
            self.conn.rollback()
            raise e

    def update_note(
        self,
        note_id: str,
        title: Optional[str] = None,
        body: Optional[str] = None,
        priority_id: Optional[str] = None,
        pinned: Optional[bool] = None,
        archived: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Updates an existing note with provided fields.
        """
        updates = []
        params = []

        fields = {
            "title": title,
            "body": body,
            "priority_id": priority_id if priority_id else None if priority_id == "" or priority_id is not None else None,
            "pinned": pinned,
        }

        # Specific priority_id logic to allow unsetting it
        if priority_id == "":
            updates.append("priority_id = NULL")
        elif priority_id is not None:
            updates.append("priority_id = %s")
            params.append(priority_id)

        for field_name, value in fields.items():
            if field_name == "priority_id":
                continue # Handled separately above
            if value is not None:
                updates.append(f"{field_name} = %s")
                params.append(value)

        if archived is not None:
            if archived:
                updates.append("archived_at = NOW()")
            else:
                updates.append("archived_at = NULL")

        updates.append("updated_at = NOW()")

        if not updates:
            note = self.get_note_by_id(note_id)
            if not note:
                raise ValueError(f"Note with id {note_id} not found.")
            return note

        params.append(note_id)
        query = f"""
            UPDATE notes
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, title, body, priority_id, pinned, archived_at, created_at, updated_at
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                if not row:
                    self.conn.rollback()
                    raise ValueError(f"Note with id {note_id} not found.")
                self.conn.commit()
                return {
                    "id": str(row[0]),
                    "title": row[1],
                    "body": row[2] if row[2] else "",
                    "priority_id": str(row[3]) if row[3] else None,
                    "pinned": bool(row[4]),
                    "archived_at": row[5].isoformat() if row[5] else None,
                    "created_at": row[6].isoformat() if row[6] else None,
                    "updated_at": row[7].isoformat() if row[7] else None,
                    "note_items": self.list_note_items(note_id)
                }
        except Exception as e:
            self.conn.rollback()
            raise e

    def delete_note(self, note_id: str) -> bool:
        """
        Deletes a note from PostgreSQL. Associated note_items are cascade deleted.
        """
        query = "DELETE FROM notes WHERE id = %s"
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, (note_id,))
                self.conn.commit()
                return True
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting note: {e}")
            return False

    def list_note_items(self, note_id: str) -> List[Dict[str, Any]]:
        """
        Lists all checklist items for a note, sorted by position.
        """
        query = """
            SELECT id, note_id, content, is_done, position, created_at, updated_at
            FROM note_items
            WHERE note_id = %s
            ORDER BY position ASC
        """
        items = []
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, (note_id,))
                rows = cur.fetchall()
                for row in rows:
                    items.append({
                        "id": str(row[0]),
                        "note_id": str(row[1]),
                        "content": row[2],
                        "is_done": bool(row[3]),
                        "position": row[4],
                        "created_at": row[5].isoformat() if row[5] else None,
                        "updated_at": row[6].isoformat() if row[6] else None,
                    })
        except Exception as e:
            print(f"Error listing note items: {e}")
        return items

    def add_note_item(
        self,
        note_id: str,
        content: str,
        is_done: bool = False,
        position: int = 0
    ) -> Dict[str, Any]:
        """
        Adds a checklist item to a note.
        """
        query = """
            INSERT INTO note_items (note_id, content, is_done, position, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            RETURNING id, note_id, content, is_done, position, created_at, updated_at
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, (note_id, content, is_done, position))
                row = cur.fetchone()
                self.conn.commit()
                return {
                    "id": str(row[0]),
                    "note_id": str(row[1]),
                    "content": row[2],
                    "is_done": bool(row[3]),
                    "position": row[4],
                    "created_at": row[6].isoformat() if row[6] else None,
                    "updated_at": row[6].isoformat() if row[6] else None,
                }
        except Exception as e:
            self.conn.rollback()
            raise e

    def update_note_item(
        self,
        item_id: str,
        content: Optional[str] = None,
        is_done: Optional[bool] = None,
        position: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Updates a checklist item.
        """
        updates = []
        params = []

        fields = {
            "content": content,
            "is_done": is_done,
            "position": position,
        }

        for field_name, value in fields.items():
            if value is not None:
                updates.append(f"{field_name} = %s")
                params.append(value)

        updates.append("updated_at = NOW()")

        if not updates:
            # Return current item state
            raise ValueError("No fields provided for update.")

        params.append(item_id)
        query = f"""
            UPDATE note_items
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, note_id, content, is_done, position, created_at, updated_at
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
                if not row:
                    self.conn.rollback()
                    raise ValueError(f"Note item with id {item_id} not found.")
                self.conn.commit()
                return {
                    "id": str(row[0]),
                    "note_id": str(row[1]),
                    "content": row[2],
                    "is_done": bool(row[3]),
                    "position": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "updated_at": row[6].isoformat() if row[6] else None,
                }
        except Exception as e:
            self.conn.rollback()
            raise e

    def delete_note_item(self, item_id: str) -> bool:
        """
        Deletes a checklist item.
        """
        query = "DELETE FROM note_items WHERE id = %s"
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, (item_id,))
                self.conn.commit()
                return True
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting note item: {e}")
            return False

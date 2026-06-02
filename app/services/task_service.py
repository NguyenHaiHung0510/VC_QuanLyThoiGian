"""
TaskService — WS6: PostgreSQL-backed CRUD for tasks and task_items.

Replaces v1 SQLite task operations in main.py.
All queries use psycopg2 parameterized syntax (%s).
"""
from datetime import date, datetime, timezone, timedelta
from typing import List, Dict, Optional, Any

VN_TZ = timezone(timedelta(hours=7))


class TaskService:
    def __init__(self, conn):
        """
        conn: psycopg2 connection (injected from main.py).
        """
        self.conn = conn

    # ------------------------------------------------------------------ #
    # TASKS                                                                #
    # ------------------------------------------------------------------ #

    def get_tasks_for_date(self, target_date: date) -> List[Dict[str, Any]]:
        """
        Returns tasks where DATE(due_at AT TIME ZONE 'Asia/Ho_Chi_Minh') = target_date
        AND status != 'archived'.

        Each dict includes priority_label / priority_color and nested task_items list.
        Ordered by status ASC, due_at ASC (so 'completed' appears last alphabetically).
        """
        query = """
            SELECT t.id, t.title, t.note, t.priority_id, t.due_at, t.status,
                   p.name AS priority_name, p.label AS priority_label, p.color AS priority_color, p.icon AS priority_icon
            FROM tasks t
            LEFT JOIN priorities p ON t.priority_id = p.id
            WHERE DATE(t.due_at AT TIME ZONE 'Asia/Ho_Chi_Minh') = %(date)s
              AND t.status != 'archived'
            ORDER BY t.status ASC, t.due_at ASC
        """
        tasks = []
        with self.conn.cursor() as cur:
            cur.execute(query, {"date": target_date})
            rows = cur.fetchall()
            for row in rows:
                task = {
                    "id": row[0],
                    "title": row[1],
                    "note": row[2],
                    "priority_id": row[3],
                    "due_at": row[4],
                    "status": row[5],
                    "priority_name": row[6],
                    "priority_label": row[7],
                    "priority_color": row[8],
                    "priority_icon": row[9],
                    "items": self.list_task_items(row[0]),
                }
                tasks.append(task)
        return tasks

    def get_overdue_tasks(self, reference_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Returns open tasks whose due date is before the reference date in Vietnam time.
        """
        reference_date = reference_date or datetime.now(VN_TZ).date()
        query = """
            SELECT t.id, t.title, t.note, t.due_at, t.status,
                   p.name AS priority_name, p.label AS priority_label, p.color AS priority_color, p.icon AS priority_icon
            FROM tasks t
            LEFT JOIN priorities p ON t.priority_id = p.id
            WHERE DATE(t.due_at AT TIME ZONE 'Asia/Ho_Chi_Minh') < %s
              AND t.status = 'open'
            ORDER BY t.due_at ASC
        """
        tasks = []
        with self.conn.cursor() as cur:
            cur.execute(query, (reference_date,))
            rows = cur.fetchall()
            for row in rows:
                tasks.append({
                    "id": row[0],
                    "title": row[1],
                    "note": row[2],
                    "due_at": row[3],
                    "status": row[4],
                    "priority_name": row[5],
                    "priority_label": row[6],
                    "priority_color": row[7],
                    "priority_icon": row[8],
                })
        return tasks

    def create_task(
        self,
        title: str,
        due_at: datetime,
        priority_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Inserts a new task with status='open'.
        due_at should be a timezone-aware datetime (use VN_TZ from this module).
        """
        query = """
            INSERT INTO tasks (title, note, priority_id, due_at, status)
            VALUES (%s, %s, %s, %s, 'open')
            RETURNING id, title, note, priority_id, due_at, status, created_at
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (title, note, priority_id, due_at))
            row = cur.fetchone()
            self.conn.commit()
            return {
                "id": row[0],
                "title": row[1],
                "note": row[2],
                "priority_id": row[3],
                "due_at": row[4],
                "status": row[5],
                "created_at": row[6],
            }

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        due_at: Optional[datetime] = None,
        priority_id: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Updates specified fields for a task. Updated_at is always refreshed.
        Supports clearing priority_id by passing the sentinel string ''.
        """
        updates = ["updated_at = NOW()"]
        params: List[Any] = []

        if title is not None:
            updates.append("title = %s")
            params.append(title)
        if due_at is not None:
            updates.append("due_at = %s")
            params.append(due_at)
        if priority_id is not None:
            # empty string → NULL
            updates.append("priority_id = %s")
            params.append(priority_id if priority_id != "" else None)
        if note is not None:
            updates.append("note = %s")
            params.append(note)

        params.append(task_id)
        query = f"""
            UPDATE tasks
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, title, note, priority_id, due_at, status, updated_at
        """
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            self.conn.commit()
            if not row:
                raise ValueError(f"Task {task_id} not found")
            return {
                "id": row[0],
                "title": row[1],
                "note": row[2],
                "priority_id": row[3],
                "due_at": row[4],
                "status": row[5],
                "updated_at": row[6],
            }

    def toggle_task_done(self, task_id: str) -> Dict[str, Any]:
        """
        If status='open' → status='completed', completed_at=NOW()
        If status='completed' → status='open', completed_at=NULL
        Returns updated task dict.
        """
        query = """
            UPDATE tasks
            SET status = CASE WHEN status = 'open' THEN 'completed' ELSE 'open' END,
                completed_at = CASE WHEN status = 'open' THEN NOW() ELSE NULL END,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, title, status, completed_at
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (task_id,))
            row = cur.fetchone()
            self.conn.commit()
            if not row:
                raise ValueError(f"Task {task_id} not found")
            return {
                "id": row[0],
                "title": row[1],
                "status": row[2],
                "completed_at": row[3],
            }

    def delete_task(self, task_id: str) -> bool:
        """
        Hard deletes the task and cascades to task_items.
        Returns True if a row was deleted.
        """
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            deleted = cur.rowcount
            self.conn.commit()
            return deleted > 0

    # ------------------------------------------------------------------ #
    # TASK ITEMS                                                           #
    # ------------------------------------------------------------------ #

    def list_task_items(self, task_id: str) -> List[Dict[str, Any]]:
        """Returns task_items for a task ordered by position."""
        query = """
            SELECT id, task_id, content, is_completed, position
            FROM task_items
            WHERE task_id = %s
            ORDER BY position ASC
        """
        items = []
        with self.conn.cursor() as cur:
            cur.execute(query, (task_id,))
            for row in cur.fetchall():
                items.append({
                    "id": row[0],
                    "task_id": row[1],
                    "content": row[2],
                    "is_completed": row[3],
                    "position": row[4],
                })
        return items

    def toggle_task_item(self, item_id: str) -> Dict[str, Any]:
        """Toggles is_completed on a task_item."""
        query = """
            UPDATE task_items
            SET is_completed = NOT is_completed,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, task_id, content, is_completed
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (item_id,))
            row = cur.fetchone()
            self.conn.commit()
            if not row:
                raise ValueError(f"Task item {item_id} not found")
            return {
                "id": row[0],
                "task_id": row[1],
                "content": row[2],
                "is_completed": row[3],
            }

    def add_task_item(self, task_id: str, content: str, position: int) -> Dict[str, Any]:
        """Inserts a new task_item."""
        query = """
            INSERT INTO task_items (task_id, content, position)
            VALUES (%s, %s, %s)
            RETURNING id, task_id, content, is_completed, position
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (task_id, content, position))
            row = cur.fetchone()
            self.conn.commit()
            return {
                "id": row[0],
                "task_id": row[1],
                "content": row[2],
                "is_completed": row[3],
                "position": row[4],
            }

    def delete_task_item(self, item_id: str) -> bool:
        """Deletes a task_item by id."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM task_items WHERE id = %s", (item_id,))
            deleted = cur.rowcount
            self.conn.commit()
            return deleted > 0

    # ------------------------------------------------------------------ #
    # PRIORITIES                                                           #
    # ------------------------------------------------------------------ #

    def list_priorities(self) -> List[Dict[str, Any]]:
        """Returns all priorities ordered by sort_order."""
        query = """
            SELECT id, name, label, color, icon
            FROM priorities
            ORDER BY sort_order ASC
        """
        with self.conn.cursor() as cur:
            cur.execute(query)
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "label": row[2],
                    "color": row[3],
                    "icon": row[4],
                }
                for row in cur.fetchall()
            ]

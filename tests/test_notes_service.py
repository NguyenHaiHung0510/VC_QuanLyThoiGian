import os
import sys
import psycopg
import pytest
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.notes_service import NotesService

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:hungklv123@localhost:5432/microschedule_v2")

@pytest.fixture(scope="module")
def db_conn():
    """
    Connects to PostgreSQL test database and uses an isolated schema.
    """
    conn = psycopg.connect(DATABASE_URL)
    schema_name = f"test_notes_service_{uuid.uuid4().hex}"

    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA "{schema_name}";')
        cur.execute(f'SET search_path TO "{schema_name}";')
        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

        # Create priorities table
        cur.execute("""
            CREATE TABLE priorities (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL,
                color TEXT NOT NULL,
                icon TEXT NULL,
                sort_order INTEGER NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)

        # Create notes table
        cur.execute("""
            CREATE TABLE notes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title TEXT NOT NULL,
                body TEXT NULL,
                priority_id UUID NULL REFERENCES priorities(id),
                pinned BOOLEAN NOT NULL DEFAULT false,
                archived_at TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)

        # Create note_items table
        cur.execute("""
            CREATE TABLE note_items (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                note_id UUID NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                is_done BOOLEAN NOT NULL DEFAULT false,
                position INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)

        # Insert some dummy priorities
        cur.execute("""
            INSERT INTO priorities (name, label, color, icon, sort_order)
            VALUES
                ('Optional', 'Optional', 'Grey', 'Low', 0),
                ('Nên làm', 'Nên làm', 'Green', 'Check', 1),
                ('Phải làm', 'Phải làm', 'Amber', 'High', 2)
        """)
        conn.commit()

    yield conn

    with conn.cursor() as cur:
        cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;')
        conn.commit()
    conn.close()


def test_notes_crud_workflow(db_conn):
    service = NotesService(db_conn)

    # 1. List priorities
    priorities = service.list_priorities()
    assert len(priorities) == 3
    assert priorities[0]["name"] == "Optional"
    assert priorities[1]["name"] == "Nên làm"

    prio_id = priorities[1]["id"] # 'Nên làm'

    # 2. Create Note
    note = service.create_note(
        title="Ý tưởng AI Agent",
        body="Nghiên cứu về LangGraph và LiteLLM",
        priority_id=prio_id,
        pinned=True
    )
    assert note["title"] == "Ý tưởng AI Agent"
    assert note["body"] == "Nghiên cứu về LangGraph và LiteLLM"
    assert note["pinned"] is True
    assert note["priority_id"] == prio_id
    assert note["archived_at"] is None

    note_id = note["id"]

    # 3. Add Checklist Items
    item1 = service.add_note_item(note_id, "Đọc tài liệu OpenAI", is_done=True, position=0)
    item2 = service.add_note_item(note_id, "Thiết lập môi trường test", is_done=False, position=1)

    assert item1["content"] == "Đọc tài liệu OpenAI"
    assert item1["is_done"] is True
    assert item2["content"] == "Thiết lập môi trường test"
    assert item2["is_done"] is False

    # 4. List Notes
    notes = service.list_notes()
    assert len(notes) == 1
    assert notes[0]["id"] == note_id
    assert notes[0]["priority_name"] == "Nên làm"
    assert len(notes[0]["note_items"]) == 2
    assert notes[0]["note_items"][0]["content"] == "Đọc tài liệu OpenAI"

    # 5. Update Note Checklist Item
    updated_item = service.update_note_item(item2["id"], is_done=True)
    assert updated_item["is_done"] is True

    # 6. Update Note (unpin & edit body)
    updated_note = service.update_note(
        note_id,
        title="Ý tưởng AI Agent v2",
        body="Cập nhật nghiên cứu LangGraph",
        pinned=False
    )
    assert updated_note["title"] == "Ý tưởng AI Agent v2"
    assert updated_note["body"] == "Cập nhật nghiên cứu LangGraph"
    assert updated_note["pinned"] is False

    # 7. Archive Note
    archived_note = service.update_note(note_id, archived=True)
    assert archived_note["archived_at"] is not None

    # Verify note is not in active notes list
    active_notes = service.list_notes(include_archived=False)
    assert len(active_notes) == 0

    # Verify note is in archived list
    all_notes = service.list_notes(include_archived=True)
    assert len(all_notes) == 1

    # Unarchive
    unarchived_note = service.update_note(note_id, archived=False)
    assert unarchived_note["archived_at"] is None
    assert len(service.list_notes(include_archived=False)) == 1

    # 8. Delete Note Item
    assert service.delete_note_item(item1["id"]) is True
    assert len(service.list_note_items(note_id)) == 1

    # 9. Delete Note
    assert service.delete_note(note_id) is True
    assert len(service.list_notes(include_archived=True)) == 0

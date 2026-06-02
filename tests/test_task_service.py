import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

import psycopg
import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.task_service import TaskService

load_dotenv()
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
VN_TZ = timezone(timedelta(hours=7))


@pytest.fixture
def db_conn():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set in environment.")

    conn = psycopg.connect(TEST_DATABASE_URL)
    schema_name = f"test_task_service_{uuid.uuid4().hex}"

    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA "{schema_name}";')
        cur.execute(f'SET search_path TO "{schema_name}";')
        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
        cur.execute("""
            CREATE TABLE priorities (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL,
                color TEXT NOT NULL,
                icon TEXT,
                sort_order INTEGER NOT NULL
            );
        """)
        cur.execute("""
            CREATE TABLE tasks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title TEXT NOT NULL,
                note TEXT,
                priority_id UUID REFERENCES priorities(id),
                due_at TIMESTAMPTZ,
                status TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                completed_at TIMESTAMPTZ
            );
        """)
        conn.commit()

    yield conn

    with conn.cursor() as cur:
        cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;')
        conn.commit()
    conn.close()


def test_get_overdue_tasks_uses_due_date_not_due_time(db_conn):
    service = TaskService(db_conn)
    reference_date = date(2026, 6, 2)

    with db_conn.cursor() as cur:
        cur.execute("""
            INSERT INTO tasks (title, due_at, status)
            VALUES
                ('Hôm nay nhưng giờ đã qua', %s, 'open'),
                ('Hôm qua còn mở', %s, 'open'),
                ('Hôm qua đã xong', %s, 'completed')
        """, (
            datetime(2026, 6, 2, 0, 0, 0, tzinfo=VN_TZ),
            datetime(2026, 6, 1, 23, 59, 0, tzinfo=VN_TZ),
            datetime(2026, 6, 1, 10, 0, 0, tzinfo=VN_TZ),
        ))
        db_conn.commit()

    overdue = service.get_overdue_tasks(reference_date=reference_date)
    assert [task["title"] for task in overdue] == ["Hôm qua còn mở"]

import os
import sys
import psycopg
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.calendar_view_service import CalendarViewService

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:hungklv123@localhost:5432/microschedule_v2")

@pytest.fixture(scope="module")
def db_conn():
    conn = psycopg.connect(DATABASE_URL)
    schema_name = f"test_cal_view_{uuid.uuid4().hex}"

    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA "{schema_name}";')
        cur.execute(f'SET search_path TO "{schema_name}";')
        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

        # Create calendar_sources
        cur.execute("""
            CREATE TABLE calendar_sources (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                display_name TEXT NOT NULL UNIQUE,
                kind TEXT NOT NULL,
                color TEXT NOT NULL,
                is_visible BOOLEAN NOT NULL DEFAULT true,
                current_version_id UUID NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)

        # Create calendar_source_versions
        cur.execute("""
            CREATE TABLE calendar_source_versions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source_id UUID NOT NULL REFERENCES calendar_sources(id) ON DELETE CASCADE,
                version_number INTEGER NOT NULL,
                imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                parser_version TEXT NOT NULL,
                status TEXT NOT NULL,
                summary_json JSONB NOT NULL DEFAULT '{}'::jsonb
            );
        """)

        # Alter sources to add current_version FK
        cur.execute("""
            ALTER TABLE calendar_sources
            ADD CONSTRAINT calendar_sources_current_version_fk
            FOREIGN KEY (current_version_id)
            REFERENCES calendar_source_versions(id)
            ON DELETE SET NULL;
        """)

        # Create calendar_events
        cur.execute("""
            CREATE TABLE calendar_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source_id UUID NOT NULL REFERENCES calendar_sources(id),
                source_version_id UUID NOT NULL REFERENCES calendar_source_versions(id) ON DELETE CASCADE,
                content_hash TEXT NOT NULL,
                title TEXT NOT NULL,
                starts_at TIMESTAMPTZ NOT NULL,
                ends_at TIMESTAMPTZ NOT NULL,
                location TEXT NULL,
                event_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                user_cancelled BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        conn.commit()

    yield conn

    with conn.cursor() as cur:
        cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;')
        conn.commit()
    conn.close()


def test_get_events_by_range(db_conn):
    # 1. Setup mock source, version and event
    with db_conn.cursor() as cur:
        # Create source
        cur.execute("""
            INSERT INTO calendar_sources (display_name, kind, color, is_visible)
            VALUES ('Lịch học Kỳ 2', 'study_schedule', '#FF00FF', true)
            RETURNING id;
        """)
        src_id = cur.fetchone()[0]

        # Create version
        cur.execute("""
            INSERT INTO calendar_source_versions (source_id, version_number, parser_version, status)
            VALUES (%s, 1, 'v1.0', 'active')
            RETURNING id;
        """, (src_id,))
        ver_id = cur.fetchone()[0]

        # Update current version reference
        cur.execute("""
            UPDATE calendar_sources SET current_version_id = %s WHERE id = %s;
        """, (ver_id, src_id))

        # Create active event
        start_t = datetime.now(timezone.utc) - timedelta(hours=1)
        end_t = datetime.now(timezone.utc) + timedelta(hours=1)
        cur.execute("""
            INSERT INTO calendar_events (source_id, source_version_id, content_hash, title, starts_at, ends_at, event_type, status, user_cancelled)
            VALUES (%s, %s, 'hash123', 'Học Nhập Môn Kỹ Thuật', %s, %s, 'class', 'active', false);
        """, (src_id, ver_id, start_t, end_t))
        db_conn.commit()

    # 2. Call service
    service = CalendarViewService(db_conn)
    query_start = datetime.now(timezone.utc) - timedelta(days=1)
    query_end = datetime.now(timezone.utc) + timedelta(days=1)

    events = service.get_events_by_range(query_start, query_end)

    # 3. Assert
    assert len(events) == 1
    assert events[0]["title"] == "Học Nhập Môn Kỹ Thuật"
    assert events[0]["kind"] == "study_schedule"
    assert events[0]["color"] == "#FF00FF"
    assert events[0]["user_cancelled"] is False

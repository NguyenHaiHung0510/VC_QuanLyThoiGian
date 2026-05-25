import os
import sys
import psycopg
import pytest
import uuid
from datetime import datetime, date, timezone, timedelta
from dotenv import load_dotenv

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.importers.ics_importer import IcsImporter
from app.importers.excel_exam_importer import ExcelExamImporter
from app.services.calendar_source_service import CalendarSourceService
from app.services.calendar_import_service import CalendarImportService

# Load environment variables
load_dotenv()
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

@pytest.fixture(scope="module")
def db_conn():
    """
    Connects to a PostgreSQL test database and uses an isolated schema.
    This deliberately does not read DATABASE_URL and never drops public tables.
    """
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set in environment.")

    conn = psycopg.connect(TEST_DATABASE_URL)
    schema_name = f"test_calendar_import_{uuid.uuid4().hex}"

    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA "{schema_name}";')
        cur.execute(f'SET search_path TO "{schema_name}";')
        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
        cur.execute("""
            CREATE TABLE calendar_sources (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                display_name TEXT UNIQUE NOT NULL,
                kind TEXT NOT NULL,
                academic_year INTEGER,
                term TEXT,
                sort_start_date DATE,
                color TEXT NOT NULL,
                is_visible BOOLEAN DEFAULT TRUE,
                current_version_id UUID,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE calendar_source_versions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source_id UUID NOT NULL REFERENCES calendar_sources(id) ON DELETE CASCADE,
                version_number INTEGER NOT NULL,
                file_name TEXT,
                file_sha256 TEXT NOT NULL,
                imported_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                parser_version TEXT,
                status TEXT NOT NULL,
                summary_json JSONB,
                UNIQUE(source_id, version_number),
                UNIQUE(source_id, file_sha256)
            );
        """)
        cur.execute("""
            CREATE TABLE calendar_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source_id UUID NOT NULL REFERENCES calendar_sources(id) ON DELETE CASCADE,
                source_version_id UUID NOT NULL REFERENCES calendar_source_versions(id) ON DELETE CASCADE,
                external_uid TEXT,
                content_hash TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                starts_at TIMESTAMPTZ NOT NULL,
                ends_at TIMESTAMPTZ NOT NULL,
                location TEXT,
                event_type TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            ALTER TABLE calendar_sources ADD CONSTRAINT calendar_sources_current_version_fk
            FOREIGN KEY (current_version_id) REFERENCES calendar_source_versions(id) ON DELETE SET NULL;
        """)
        conn.commit()

    yield conn

    with conn.cursor() as cur:
        cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;')
        conn.commit()
    conn.close()


def test_ics_parser_study_schedule():
    """
    Verifies that the ICS parser parses TKB-QLDT20252.ics correctly.
    Should yield 139 events.
    """
    file_path = "TKB-QLDT20252.ics"
    if not os.path.exists(file_path):
        pytest.skip(f"Test file {file_path} not found.")

    importer = IcsImporter()
    events = importer.parse(file_path)

    assert len(events) == 139

    # Spot-check first event
    # UID:0@qldt.ptit.edu.vn-20252
    # DTSTART;VALUE=DATE-TIME:20260113T070000 -> 2026-01-13 07:00:00+07:00
    # SUMMARY;LANGUAGE=en-us:Cơ sở dữ liệu phân tán (06)
    ev0 = next(e for e in events if e["external_uid"] == "0@qldt.ptit.edu.vn-20252")
    assert ev0["title"] == "Cơ sở dữ liệu phân tán (06)"
    assert ev0["event_type"] == "class"
    assert ev0["starts_at"].year == 2026
    assert ev0["starts_at"].month == 1
    assert ev0["starts_at"].day == 13
    assert ev0["starts_at"].hour == 7
    assert ev0["starts_at"].tzinfo is not None
    assert ev0["starts_at"].tzinfo.utcoffset(ev0["starts_at"]) == timedelta(hours=7)
    assert ev0["location"] == "304-A2-304-A2(HN)"


def test_ics_parser_exam_schedule():
    """
    Verifies that the ICS parser parses LichThi-QLDT-20252.ics correctly.
    Should yield 8 events.
    """
    file_path = "LichThi-QLDT-20252.ics"
    if not os.path.exists(file_path):
        pytest.skip(f"Test file {file_path} not found.")

    importer = IcsImporter()
    events = importer.parse(file_path)

    assert len(events) == 8

    # Spot check: [THI] Kỹ năng tạo lập Văn bản
    ev0 = next(e for e in events if e["external_uid"] == "0@qldt.ptit.edu.vn-LichThi-20252")
    assert ev0["title"] == "[THI] Kỹ năng tạo lập Văn bản (D23TKDPT03_41) - Tổ: 001"
    assert ev0["event_type"] == "exam"
    assert ev0["starts_at"].month == 5
    assert ev0["starts_at"].day == 28
    assert ev0["starts_at"].hour == 10
    assert ev0["location"] == "201A-A3"


def test_excel_parser():
    """
    Verifies that the Excel parser parses LichThi.xlsx correctly.
    Should yield 8 events.
    """
    file_path = "LichThi.xlsx"
    if not os.path.exists(file_path):
        pytest.skip(f"Test file {file_path} not found.")

    importer = ExcelExamImporter()
    events, warnings = importer.parse(file_path)

    assert len(events) == 8
    # Warnings can be populated due to ambiguous mm-dd-yy formats
    assert isinstance(warnings, list)

    # Spot check: should have prefixed [THI]
    for ev in events:
        assert ev["title"].startswith("[THI]")
        assert ev["event_type"] == "exam"


def test_calendar_import_service_workflow(db_conn):
    """
    Verifies the end-to-end versioned import logic.
    """
    # Create services
    source_service = CalendarSourceService(db_conn)
    import_service = CalendarImportService(db_conn)

    # 1. Create a calendar source
    source = source_service.create_source(
        display_name="Lịch học kỳ 2 năm 2026",
        kind="study_schedule",
        academic_year=2025,
        term="Kỳ 2",
        sort_start_date=date(2026, 1, 13),
        color="Blue"
    )

    source_id = source["id"]
    assert source["current_version_id"] is None

    # 2. Import TKB-QLDT20252.ics (Version 1)
    file_path = "TKB-QLDT20252.ics"
    if not os.path.exists(file_path):
        pytest.skip(f"Test file {file_path} not found.")

    res1 = import_service.import_file(source_id, file_path)
    assert res1["status"] == "active"
    assert res1["version_number"] == 1
    assert res1["parsed_count"] == 139

    # Check source's current_version_id is updated
    updated_source = source_service.get_source_by_id(source_id)
    assert updated_source["current_version_id"] == res1["version_id"]

    # Verify events exist in db
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM calendar_events WHERE source_version_id = %s", (res1["version_id"],))
        count = cur.fetchone()[0]
        assert count == 139

    # 3. Re-importing same file (Duplicate check)
    res2 = import_service.import_file(source_id, file_path)
    assert res2["status"] == "duplicate_noop"
    assert res2["version_id"] == res1["version_id"]
    assert res2["version_number"] == 1

    # Verify no new version is created
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM calendar_source_versions WHERE source_id = %s", (source_id,))
        ver_count = cur.fetchone()[0]
        assert ver_count == 1

    # 4. Import a different file or modified file mock
    # Create a small temp ics file
    temp_file = "temp_test_schedule.ics"
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write("""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:temp-event-1
SUMMARY:Mock Event
DTSTART:20260113T100000
LOCATION:Online
END:VEVENT
END:VCALENDAR""")

    try:
        res3 = import_service.import_file(source_id, temp_file)
        assert res3["status"] == "active"
        assert res3["version_number"] == 2
        assert res3["parsed_count"] == 1

        # Verify source points to version 2
        updated_source = source_service.get_source_by_id(source_id)
        assert updated_source["current_version_id"] == res3["version_id"]

        # Verify both versions exist in db
        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM calendar_source_versions WHERE source_id = %s", (source_id,))
            assert cur.fetchone()[0] == 2

            cur.execute("SELECT COUNT(*) FROM calendar_events WHERE source_version_id = %s", (res3["version_id"],))
            assert cur.fetchone()[0] == 1

            cur.execute("SELECT COUNT(*) FROM calendar_events WHERE source_version_id = %s", (res1["version_id"],))
            assert cur.fetchone()[0] == 139
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    # 5. List sources ordering verification
    # Create another source with earlier date
    source2 = source_service.create_source(
        display_name="Lịch thi kỳ 2 năm 2026",
        kind="exam_schedule",
        academic_year=2025,
        term="Kỳ 2",
        sort_start_date=date(2026, 5, 28),
        color="Red"
    )

    # List sources
    sources = source_service.list_sources()
    # Blue source (sort_start_date=2026-01-13) should be before Red source (2026-05-28)
    blue_idx = next(i for i, s in enumerate(sources) if s["id"] == source_id)
    red_idx = next(i for i, s in enumerate(sources) if s["id"] == source2["id"])
    assert blue_idx < red_idx

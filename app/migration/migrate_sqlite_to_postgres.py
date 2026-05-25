from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import assert_safe_target_database, load_config
from app.db.postgres import apply_schema, connect_checked, reset_public_schema, transaction
from app.migration.analyze_v1_sqlite import (
    VIETNAM_TZ,
    analyze,
    open_sqlite_readonly,
    parse_v1_datetime,
    parse_v1_time,
    v1_date_to_due_at,
    write_report,
)


DEFAULT_PRIORITIES = [
    {"name": "Optional", "label": "Optional", "color": "Grey", "icon": "Low"},
    {"name": "Nên làm", "label": "Nên làm", "color": "Green", "icon": "Check"},
    {"name": "Phải làm", "label": "Phải làm", "color": "Amber", "icon": "High"},
    {"name": "Bỏ là nhót", "label": "Bỏ là nhót", "color": "Orange", "icon": "Danger"},
    {"name": "Nguy hiểm", "label": "Nguy hiểm", "color": "Red", "icon": "Warning"},
]


def fetch_dicts(conn: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute(query).fetchall()]


def normalize_priority_settings(settings: dict[str, Any]) -> list[dict[str, Any]]:
    raw = settings.get("priorities")
    if isinstance(raw, list) and raw:
        priorities = []
        for idx, item in enumerate(raw):
            if not isinstance(item, dict) or not item.get("name"):
                continue
            priorities.append(
                {
                    "name": item["name"],
                    "label": item.get("label") or item["name"],
                    "color": item.get("color") or "Grey",
                    "icon": item.get("icon"),
                    "sort_order": idx,
                }
            )
        if priorities:
            return priorities

    return [
        {
            "name": item["name"],
            "label": item["label"],
            "color": item["color"],
            "icon": item["icon"],
            "sort_order": idx,
        }
        for idx, item in enumerate(DEFAULT_PRIORITIES)
    ]


def load_v1_data(sqlite_path: Path) -> dict[str, list[dict[str, Any]]]:
    with open_sqlite_readonly(sqlite_path) as conn:
        return {
            "tasks": fetch_dicts(
                conn,
                "SELECT id, title, is_completed, priority, date_str, note FROM tasks ORDER BY id",
            ),
            "subtasks": fetch_dicts(
                conn,
                "SELECT id, task_id, content, is_completed FROM subtasks ORDER BY task_id, id",
            ),
            "schedule": fetch_dicts(
                conn,
                "SELECT id, subject, time_start, time_end, location, date_str, is_cancelled FROM schedule ORDER BY id",
            ),
            "settings": fetch_dicts(
                conn,
                "SELECT key, value FROM settings ORDER BY key",
            ),
        }


def parse_settings(rows: list[dict[str, Any]]) -> dict[str, Any]:
    settings: dict[str, Any] = {}
    for row in rows:
        raw_value = row.get("value")
        try:
            settings[row["key"]] = json.loads(raw_value)
        except Exception:
            settings[row["key"]] = raw_value
    return settings


def content_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def insert_priorities(cur, settings: dict[str, Any]) -> dict[str, Any]:
    priority_ids: dict[str, Any] = {}
    for priority in normalize_priority_settings(settings):
        cur.execute(
            """
            INSERT INTO priorities (name, label, color, icon, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                label = EXCLUDED.label,
                color = EXCLUDED.color,
                icon = EXCLUDED.icon,
                sort_order = EXCLUDED.sort_order,
                updated_at = now()
            RETURNING id
            """,
            (
                priority["name"],
                priority["label"],
                priority["color"],
                priority["icon"],
                priority["sort_order"],
            ),
        )
        priority_ids[priority["name"]] = cur.fetchone()[0]
    return priority_ids


def insert_settings(cur, settings: dict[str, Any]) -> None:
    for key, value in settings.items():
        cur.execute(
            """
            INSERT INTO app_settings (key, value_json)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (key) DO UPDATE SET
                value_json = EXCLUDED.value_json,
                updated_at = now()
            """,
            (key, json.dumps(value, ensure_ascii=False)),
        )

    defaults = {
        "export.default_format": "markdown",
        "export.include_notes": True,
        "export.include_completed": False,
        "export.lookahead_days": 30,
    }
    for key, value in defaults.items():
        cur.execute(
            """
            INSERT INTO app_settings (key, value_json)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (key) DO NOTHING
            """,
            (key, json.dumps(value, ensure_ascii=False)),
        )


def migrate_tasks_and_notes(
    cur,
    tasks: list[dict[str, Any]],
    subtasks: list[dict[str, Any]],
    priority_ids: dict[str, Any],
    today: date,
    migration_time: datetime,
) -> tuple[int, int]:
    subtasks_by_task: dict[int, list[dict[str, Any]]] = {}
    for subtask in subtasks:
        subtasks_by_task.setdefault(int(subtask["task_id"]), []).append(subtask)

    migrated_tasks = 0
    migrated_notes = 0

    for task in tasks:
        old_task_id = int(task["id"])
        due_at = v1_date_to_due_at(task.get("date_str"))
        is_completed = int(task.get("is_completed") or 0) == 1
        priority_id = priority_ids.get(task.get("priority")) or priority_ids.get("Nên làm")
        title = task.get("title") or "(untitled)"
        note = task.get("note")

        if (not is_completed) and due_at and due_at.date() < today:
            cur.execute(
                """
                INSERT INTO notes (title, body, priority_id, pinned, created_at, updated_at)
                VALUES (%s, %s, %s, false, %s, %s)
                RETURNING id
                """,
                (title, note, priority_id, migration_time, migration_time),
            )
            note_id = cur.fetchone()[0]
            for position, subtask in enumerate(subtasks_by_task.get(old_task_id, [])):
                cur.execute(
                    """
                    INSERT INTO note_items (note_id, content, is_done, position, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        note_id,
                        subtask.get("content") or "",
                        bool(subtask.get("is_completed")),
                        position,
                        migration_time,
                        migration_time,
                    ),
                )
            migrated_notes += 1
            continue

        status = "completed" if is_completed else "open"
        completed_at = migration_time if is_completed else None
        cur.execute(
            """
            INSERT INTO tasks (title, note, priority_id, due_at, status, created_at, updated_at, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (title, note, priority_id, due_at, status, migration_time, migration_time, completed_at),
        )
        task_id = cur.fetchone()[0]
        for position, subtask in enumerate(subtasks_by_task.get(old_task_id, [])):
            cur.execute(
                """
                INSERT INTO task_items (task_id, content, is_completed, position, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    task_id,
                    subtask.get("content") or "",
                    bool(subtask.get("is_completed")),
                    position,
                    migration_time,
                    migration_time,
                ),
            )
        migrated_tasks += 1

    return migrated_tasks, migrated_notes


def migrate_schedule(
    cur,
    schedule_rows: list[dict[str, Any]],
    sqlite_path: Path,
    sqlite_sha256: str,
    migration_time: datetime,
) -> tuple[int, int, int]:
    cur.execute(
        """
        INSERT INTO calendar_sources (
            display_name, kind, color, is_visible, created_at, updated_at
        )
        VALUES ('v1_sqlite_schedule', 'legacy_v1', '#64748b', true, %s, %s)
        ON CONFLICT (display_name) DO UPDATE SET updated_at = EXCLUDED.updated_at
        RETURNING id
        """,
        (migration_time, migration_time),
    )
    source_id = cur.fetchone()[0]

    summary = {"source_rows": len(schedule_rows), "sqlite_path": str(sqlite_path)}
    cur.execute(
        """
        INSERT INTO calendar_source_versions (
            source_id, version_number, file_name, file_sha256, imported_at,
            parser_version, status, summary_json
        )
        VALUES (%s, 1, %s, %s, %s, 'v1_sqlite_migration', 'active', %s::jsonb)
        RETURNING id
        """,
        (
            source_id,
            sqlite_path.name,
            sqlite_sha256,
            migration_time,
            json.dumps(summary, ensure_ascii=False),
        ),
    )
    version_id = cur.fetchone()[0]

    inserted = 0
    skipped = 0
    for row in schedule_rows:
        starts_at = parse_v1_datetime(row.get("date_str"), row.get("time_start"))
        if starts_at is None:
            skipped += 1
            continue

        end_time = parse_v1_time(row.get("time_end"))
        if end_time is None:
            ends_at = starts_at + timedelta(minutes=90)
        else:
            ends_at = starts_at.replace(
                hour=end_time.hour,
                minute=end_time.minute,
                second=end_time.second,
                microsecond=0,
            )
            if ends_at <= starts_at:
                ends_at += timedelta(days=1)

        payload = {
            "title": row.get("subject") or "",
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "location": row.get("location") or "",
            "event_type": "legacy",
        }
        cur.execute(
            """
            INSERT INTO calendar_events (
                source_id, source_version_id, external_uid, content_hash, title,
                description, starts_at, ends_at, location, event_type, status,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, NULL, %s, %s, %s, 'legacy', %s, %s, %s)
            """,
            (
                source_id,
                version_id,
                f"v1-schedule-{row['id']}",
                content_hash(payload),
                row.get("subject") or "(untitled)",
                starts_at,
                ends_at,
                row.get("location"),
                "cancelled" if int(row.get("is_cancelled") or 0) else "active",
                migration_time,
                migration_time,
            ),
        )
        inserted += 1

    cur.execute(
        "UPDATE calendar_sources SET current_version_id = %s, updated_at = %s WHERE id = %s",
        (version_id, migration_time, source_id),
    )
    return 1, 1, inserted


def collect_postgres_counts(cur) -> dict[str, int]:
    tables = [
        "priorities",
        "tasks",
        "task_items",
        "notes",
        "note_items",
        "app_settings",
        "calendar_sources",
        "calendar_source_versions",
        "calendar_events",
        "backup_runs",
        "agent_action_log",
    ]
    counts: dict[str, int] = {}
    for table in tables:
        cur.execute(f"SELECT count(*) FROM {table}")
        counts[table] = int(cur.fetchone()[0])
    return counts


def collect_calendar_counts(cur) -> dict[str, int]:
    cur.execute(
        "SELECT count(*) FROM calendar_sources WHERE display_name = 'v1_sqlite_schedule'"
    )
    source_count = int(cur.fetchone()[0])
    cur.execute(
        """
        SELECT count(*)
        FROM calendar_source_versions v
        JOIN calendar_sources s ON s.id = v.source_id
        WHERE s.display_name = 'v1_sqlite_schedule'
        """
    )
    version_count = int(cur.fetchone()[0])
    cur.execute(
        """
        SELECT count(*)
        FROM calendar_events e
        JOIN calendar_sources s ON s.id = e.source_id
        WHERE s.display_name = 'v1_sqlite_schedule'
        """
    )
    event_count = int(cur.fetchone()[0])
    return {
        "legacy_source_count": source_count,
        "legacy_source_version_count": version_count,
        "legacy_event_count": event_count,
    }


def apply_migration(
    sqlite_path: Path,
    *,
    reset_dev_db: bool,
    allow_non_dev_target: bool,
    today: date,
) -> tuple[dict[str, int], dict[str, int]]:
    config = load_config()
    assert_safe_target_database(
        config.database_url,
        allow_non_dev_target=allow_non_dev_target,
    )
    v1_data = load_v1_data(sqlite_path)
    settings = parse_settings(v1_data["settings"])
    analysis = analyze(sqlite_path, config.database_name, today)
    migration_time = datetime.now(VIETNAM_TZ)

    with connect_checked(config, allow_non_dev_target=allow_non_dev_target) as conn:
        with transaction(conn):
            if reset_dev_db:
                reset_public_schema(conn, config.database_url)
            apply_schema(conn)
            with conn.cursor() as cur:
                priority_ids = insert_priorities(cur, settings)
                insert_settings(cur, settings)
                migrate_tasks_and_notes(
                    cur,
                    v1_data["tasks"],
                    v1_data["subtasks"],
                    priority_ids,
                    today,
                    migration_time,
                )
                migrate_schedule(
                    cur,
                    v1_data["schedule"],
                    sqlite_path,
                    analysis.sqlite_sha256,
                    migration_time,
                )
                postgres_counts = collect_postgres_counts(cur)
                calendar_counts = collect_calendar_counts(cur)

    return postgres_counts, calendar_counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate SQLite v1 to PostgreSQL v2.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--reset-dev-db", action="store_true")
    parser.add_argument("--allow-non-dev-target", action="store_true")
    parser.add_argument("--sqlite-path", type=Path, default=None)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    config = load_config()
    sqlite_path = args.sqlite_path or config.sqlite_v1_path
    analysis = analyze(sqlite_path, config.database_name, args.today)

    if not args.apply:
        assert_safe_target_database(
            config.database_url,
            allow_non_dev_target=args.allow_non_dev_target,
        )
        write_report(analysis, mode="dry-run")
        print(
            json.dumps(
                {
                    "mode": "dry-run",
                    "sqlite_counts": analysis.counts,
                    "notes_converted_count": len(analysis.note_candidates),
                    "legacy_schedule_events": analysis.schedule_count,
                    "target_database": analysis.target_database_name,
                    "report_path": "docs/V2_MIGRATION_REPORT.md",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    postgres_counts, calendar_counts = apply_migration(
        sqlite_path,
        reset_dev_db=args.reset_dev_db,
        allow_non_dev_target=args.allow_non_dev_target,
        today=args.today,
    )
    write_report(
        analysis,
        mode="apply",
        postgres_counts=postgres_counts,
        calendar_counts=calendar_counts,
    )
    print(
        json.dumps(
            {
                "mode": "apply",
                "postgres_counts": postgres_counts,
                "calendar_counts": calendar_counts,
                "report_path": "docs/V2_MIGRATION_REPORT.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

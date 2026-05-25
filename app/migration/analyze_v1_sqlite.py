from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import load_config


VIETNAM_TZ = timezone(timedelta(hours=7))
REPORT_PATH = Path("docs/V2_MIGRATION_REPORT.md")


@dataclass(frozen=True)
class V1Analysis:
    sqlite_path: Path
    target_database_name: str
    today: date
    counts: dict[str, int]
    note_candidates: list[dict[str, Any]]
    task_plan_count: int
    completed_task_count: int
    open_task_count: int
    schedule_count: int
    setting_count: int
    skipped: list[str]
    sqlite_sha256: str


def open_sqlite_readonly(sqlite_path: Path) -> sqlite3.Connection:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite v1 file not found: {sqlite_path}")
    uri = sqlite_path.resolve().as_uri()
    separator = "&" if "?" in uri else "?"
    return sqlite3.connect(f"{uri}{separator}mode=ro", uri=True)


def parse_v1_date(value: str | None) -> date | None:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def v1_date_to_due_at(value: str | None) -> datetime | None:
    parsed = parse_v1_date(value)
    if parsed is None:
        return None
    return datetime.combine(parsed, time.min, tzinfo=VIETNAM_TZ)


def parse_v1_datetime(date_str: str | None, time_str: str | None) -> datetime | None:
    parsed_date = parse_v1_date(date_str)
    if parsed_date is None:
        return None
    parsed_time = parse_v1_time(time_str) or time(0, 0)
    return datetime.combine(parsed_date, parsed_time, tzinfo=VIETNAM_TZ)


def parse_v1_time(value: str | None) -> time | None:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            pass
    return None


def file_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def table_count(conn: sqlite3.Connection, table_name: str) -> int:
    cur = conn.execute(f"SELECT count(*) FROM {table_name}")
    return int(cur.fetchone()[0])


def fetch_dicts(conn: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def analyze(sqlite_path: Path, target_database_name: str, today: date) -> V1Analysis:
    skipped: list[str] = []
    with open_sqlite_readonly(sqlite_path) as conn:
        counts = {
            "tasks": table_count(conn, "tasks"),
            "subtasks": table_count(conn, "subtasks"),
            "schedule": table_count(conn, "schedule"),
            "settings": table_count(conn, "settings"),
        }
        tasks = fetch_dicts(
            conn,
            """
            SELECT id, title, is_completed, priority, date_str, note
            FROM tasks
            ORDER BY id
            """,
        )

    note_candidates: list[dict[str, Any]] = []
    completed_task_count = 0
    open_task_count = 0

    for task in tasks:
        task_date = parse_v1_date(task.get("date_str"))
        is_completed = int(task.get("is_completed") or 0) == 1
        if is_completed:
            completed_task_count += 1
        elif task_date and task_date < today:
            note_candidates.append(
                {
                    "id": task["id"],
                    "title": task.get("title") or "",
                    "old_date": task.get("date_str"),
                    "priority": task.get("priority"),
                }
            )
        else:
            open_task_count += 1
            if task.get("date_str") and task_date is None:
                skipped.append(
                    f"Task {task['id']} has unparseable date '{task.get('date_str')}', migrating as open task with null due_at."
                )

    return V1Analysis(
        sqlite_path=sqlite_path,
        target_database_name=target_database_name,
        today=today,
        counts=counts,
        note_candidates=note_candidates,
        task_plan_count=completed_task_count + open_task_count,
        completed_task_count=completed_task_count,
        open_task_count=open_task_count,
        schedule_count=counts["schedule"],
        setting_count=counts["settings"],
        skipped=skipped,
        sqlite_sha256=file_sha256(sqlite_path),
    )


def write_report(
    analysis: V1Analysis,
    *,
    mode: str,
    postgres_counts: dict[str, int] | None = None,
    calendar_counts: dict[str, int] | None = None,
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(VIETNAM_TZ).strftime("%Y-%m-%d %H:%M:%S %z")
    pg_counts = postgres_counts or {}
    cal_counts = calendar_counts or {}

    lines = [
        "# microSchedule v2 Migration Report",
        "",
        f"Generated at: {now}",
        f"Mode: {mode}",
        f"Source SQLite path: `{analysis.sqlite_path}`",
        f"Source SQLite SHA256: `{analysis.sqlite_sha256}`",
        f"Target PostgreSQL database: `{analysis.target_database_name}`",
        f"Migration today/date cutoff: `{analysis.today.isoformat()}`",
        f"Schema timestamp: `{now}`",
        "",
        "## SQLite v1 Counts",
        "",
    ]
    for key in ("tasks", "subtasks", "schedule", "settings"):
        lines.append(f"- {key}: {analysis.counts.get(key, 0)}")

    lines.extend(
        [
            "",
            "## Migration Plan",
            "",
            f"- Completed tasks to `tasks`: {analysis.completed_task_count}",
            f"- Open non-overdue tasks to `tasks`: {analysis.open_task_count}",
            f"- Incomplete overdue tasks to `notes`: {len(analysis.note_candidates)}",
            f"- Legacy schedule rows to calendar source/version/events: {analysis.schedule_count}",
            f"- Settings to `app_settings`: {analysis.setting_count}",
            "",
            "## Tasks Converted To Notes",
            "",
        ]
    )

    if analysis.note_candidates:
        lines.append("| v1 id | title | old date |")
        lines.append("|---:|---|---|")
        for task in analysis.note_candidates:
            safe_title = str(task["title"]).replace("|", "\\|")
            lines.append(f"| {task['id']} | {safe_title} | {task['old_date']} |")
    else:
        lines.append("None.")

    lines.extend(["", "## Rows Skipped Or Warnings", ""])
    if analysis.skipped:
        for warning in analysis.skipped:
            lines.append(f"- {warning}")
    else:
        lines.append("- None.")

    lines.extend(["", "## PostgreSQL v2 Counts", ""])
    if pg_counts:
        for key in sorted(pg_counts):
            lines.append(f"- {key}: {pg_counts[key]}")
    else:
        lines.append("- Not applied yet.")

    lines.extend(["", "## Calendar Legacy Source Counts", ""])
    if cal_counts:
        for key in sorted(cal_counts):
            lines.append(f"- {key}: {cal_counts[key]}")
    else:
        lines.append("- Not applied yet.")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze SQLite v1 data read-only.")
    parser.add_argument("--sqlite-path", type=Path, default=None)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    parser.add_argument("--no-report", action="store_true")
    args = parser.parse_args()

    config = load_config()
    sqlite_path = args.sqlite_path or config.sqlite_v1_path
    analysis = analyze(sqlite_path, config.database_name, args.today)

    if not args.no_report:
        write_report(analysis, mode="analyze")

    print(
        json.dumps(
            {
                "sqlite_counts": analysis.counts,
                "notes_converted_count": len(analysis.note_candidates),
                "task_rows_after_note_split": analysis.task_plan_count,
                "legacy_schedule_events": analysis.schedule_count,
                "report_path": str(REPORT_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg

from app.config import AppConfig, assert_reset_allowed, assert_safe_target_database


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(config_or_url: AppConfig | str) -> psycopg.Connection:
    database_url = (
        config_or_url.database_url
        if isinstance(config_or_url, AppConfig)
        else config_or_url
    )
    return psycopg.connect(database_url)


@contextmanager
def transaction(conn: psycopg.Connection) -> Iterator[psycopg.Connection]:
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def read_schema_sql() -> str:
    return SCHEMA_PATH.read_text(encoding="utf-8")


def apply_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(read_schema_sql())


def reset_public_schema(conn: psycopg.Connection, database_url: str) -> None:
    assert_reset_allowed(database_url)
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE;")
        cur.execute("CREATE SCHEMA public;")
        cur.execute("GRANT ALL ON SCHEMA public TO public;")


def connect_checked(
    config: AppConfig,
    *,
    allow_non_dev_target: bool = False,
) -> psycopg.Connection:
    assert_safe_target_database(
        config.database_url,
        allow_non_dev_target=allow_non_dev_target,
    )
    return connect(config)

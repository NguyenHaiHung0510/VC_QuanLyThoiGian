from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv


DEFAULT_SQLITE_V1_PATH = Path(
    r"C:\Users\os\Desktop\Tools\VC_microSchedule_home\todo.db"
)
DEFAULT_DATA_DIR = Path(r"C:\Users\os\Desktop\Tools\VC_microSchedule_home_v2")
DEFAULT_DATABASE_URL = "postgresql://postgres@localhost:5432/microschedule_v2"
DEV_DATABASE_NAME = "microschedule_v2"


@dataclass(frozen=True)
class AppConfig:
    database_url: str
    data_dir: Path
    backup_dir: Path
    sqlite_v1_path: Path
    app_env: str
    app_version: str

    @property
    def database_name(self) -> str:
        return get_database_name(self.database_url)

    @property
    def safe_database_url(self) -> str:
        return redact_database_url(self.database_url)


def load_config(dotenv_path: str | os.PathLike[str] | None = None) -> AppConfig:
    load_dotenv(dotenv_path=dotenv_path)

    data_dir = Path(os.getenv("MICROSCHEDULE_DATA_DIR", str(DEFAULT_DATA_DIR)))
    backup_dir = Path(os.getenv("MICROSCHEDULE_BACKUP_DIR", str(data_dir / "backups")))
    sqlite_v1_path = Path(
        os.getenv("SQLITE_V1_PATH", str(DEFAULT_SQLITE_V1_PATH))
    )

    return AppConfig(
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        data_dir=data_dir,
        backup_dir=backup_dir,
        sqlite_v1_path=sqlite_v1_path,
        app_env=os.getenv("APP_ENV", "development"),
        app_version=os.getenv("APP_VERSION", "2"),
    )


def get_database_name(database_url: str) -> str:
    parsed = urlparse(database_url)
    return parsed.path.lstrip("/")


def redact_database_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    if not parsed.netloc:
        return database_url

    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    if parsed.username:
        userinfo = parsed.username
        if parsed.password is not None:
            userinfo += ":***"
        netloc = f"{userinfo}@{host}{port}"
    else:
        netloc = f"{host}{port}"
    return urlunparse(parsed._replace(netloc=netloc))


def assert_safe_target_database(
    database_url: str,
    *,
    allow_non_dev_target: bool = False,
) -> None:
    database_name = get_database_name(database_url)
    if database_name == DEV_DATABASE_NAME:
        return
    if allow_non_dev_target:
        return
    raise ValueError(
        f"Refusing to target PostgreSQL database '{database_name}'. "
        f"Expected '{DEV_DATABASE_NAME}' unless --allow-non-dev-target is set."
    )


def assert_reset_allowed(database_url: str) -> None:
    database_name = get_database_name(database_url)
    if database_name != DEV_DATABASE_NAME:
        raise ValueError(
            f"--reset-dev-db is allowed only for database '{DEV_DATABASE_NAME}', "
            f"got '{database_name}'."
        )

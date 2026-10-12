import os
from pathlib import Path

import aiosqlite
from aiosqlite import Connection

from achieff import badges, gdpr

DATABASE_NAME = "achieff.sqlite3"
SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE crew (
    id INTEGER PRIMARY KEY,
    alias TEXT NOT NULL,
    alias_normalized TEXT NOT NULL UNIQUE,
    key_hash TEXT,
    role TEXT NOT NULL DEFAULT 'crew' CHECK (role IN ('crew', 'admin')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'retired')),
    sprite_variant INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE badge (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    polarity TEXT NOT NULL CHECK (polarity IN ('goody', 'baddy')),
    sort_order INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE award (
    id INTEGER PRIMARY KEY,
    crew_id INTEGER NOT NULL REFERENCES crew(id) ON DELETE CASCADE,
    badge_id INTEGER NOT NULL REFERENCES badge(id),
    awarded_by INTEGER REFERENCES crew(id) ON DELETE SET NULL,
    awarded_at TEXT NOT NULL,
    UNIQUE (crew_id, badge_id)
);

CREATE TABLE session (
    id INTEGER PRIMARY KEY,
    crew_id INTEGER NOT NULL REFERENCES crew(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL
);

DELETE FROM schema_version;
INSERT INTO schema_version (version) VALUES (1);
"""


def data_dir() -> Path:
    raw = os.environ.get("ACHIEFF_DATA_DIR", "data")
    return Path(raw)


def database_path() -> Path:
    return data_dir() / DATABASE_NAME


async def connect() -> Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = await aiosqlite.connect(path)
    connection.row_factory = aiosqlite.Row
    await connection.execute("PRAGMA foreign_keys = ON")
    return connection


async def migrate() -> None:
    connection = await connect()
    try:
        await _ensure_schema(connection)
        await badges.seed_examples(connection)
        await connection.commit()
    finally:
        await connection.close()


async def column_names(connection: Connection) -> list[str]:
    async with connection.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ) as cursor:
        tables = await cursor.fetchall()

    names: list[str] = []
    for table in tables:
        table_name = str(table["name"])
        if not table_name.isidentifier():
            continue
        async with connection.execute(f"PRAGMA table_info({table_name})") as cursor:
            columns = await cursor.fetchall()
        names.extend(str(column["name"]) for column in columns)
    return names


async def assert_schema_is_allowed(connection: Connection) -> None:
    found = gdpr.forbidden_columns(await column_names(connection))
    if not found:
        return
    joined = ", ".join(found)
    raise gdpr.ForbiddenColumnError(f"Forbidden columns: {joined}")


async def _ensure_schema(connection: Connection) -> None:
    await connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
    )
    version = await _schema_version(connection)
    if version > SCHEMA_VERSION:
        raise SchemaVersionError(
            f"Database version {version} is newer than {SCHEMA_VERSION}."
        )
    if version < SCHEMA_VERSION:
        await connection.executescript(_SCHEMA)
    await assert_schema_is_allowed(connection)


async def _schema_version(connection: Connection) -> int:
    async with connection.execute("SELECT version FROM schema_version") as cursor:
        row = await cursor.fetchone()
    if row is None:
        return 0
    return int(row["version"])


class SchemaVersionError(RuntimeError):
    pass

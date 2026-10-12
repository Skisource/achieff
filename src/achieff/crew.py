import hashlib
from datetime import UTC, datetime
from sqlite3 import IntegrityError
from typing import Optional

from aiosqlite import Connection

SPRITE_KIT_SIZE = 8
_ALIAS_MAX_LENGTH = 40
_ROLES = {"crew", "admin"}
_STATUSES = {"active", "retired"}


class CrewAliasError(ValueError):
    pass


class CrewNotFound(LookupError):
    pass


class CrewStatusError(ValueError):
    pass


class CrewRoleError(ValueError):
    pass


def normalize_alias(alias: str) -> str:
    compact = " ".join(alias.split())
    if not compact:
        raise CrewAliasError("Alias is empty.")
    if "@" in compact:
        raise CrewAliasError("Alias cannot be an email address.")
    if len(compact) > _ALIAS_MAX_LENGTH:
        raise CrewAliasError("Alias is too long.")
    return compact


def sprite_variant_for(alias_normalized: str) -> int:
    digest = hashlib.sha256(alias_normalized.encode()).digest()
    return int.from_bytes(digest[:2], "big") % SPRITE_KIT_SIZE


async def add(
    connection: Connection,
    alias: str,
    *,
    role: str = "crew",
    status: str = "active",
    key_hash: Optional[str] = None,
) -> int:
    display = normalize_alias(alias)
    if role not in _ROLES:
        raise CrewRoleError("Role must be crew or admin.")
    if status not in _STATUSES:
        raise CrewStatusError("Status must be active or retired.")

    normalized = display.casefold()
    if await find_by_alias(connection, display) is not None:
        raise CrewAliasError("That alias already exists.")

    try:
        cursor = await connection.execute(
            """
            INSERT INTO crew (
                alias,
                alias_normalized,
                key_hash,
                role,
                status,
                sprite_variant,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                display,
                normalized,
                key_hash,
                role,
                status,
                sprite_variant_for(normalized),
                _utc_now(),
            ),
        )
        await connection.commit()
    except IntegrityError as error:
        await connection.rollback()
        raise CrewAliasError("That alias already exists.") from error
    return int(cursor.lastrowid)


async def get(connection: Connection, crew_id: int):
    async with connection.execute(
        "SELECT * FROM crew WHERE id = ?", (crew_id,)
    ) as cursor:
        return await cursor.fetchone()


async def find_by_alias(connection: Connection, alias: str):
    normalized = normalize_alias(alias).casefold()
    async with connection.execute(
        "SELECT * FROM crew WHERE alias_normalized = ?",
        (normalized,),
    ) as cursor:
        return await cursor.fetchone()


async def set_status(connection: Connection, crew_id: int, status: str) -> None:
    if status not in _STATUSES:
        raise CrewStatusError("Status must be active or retired.")
    if await get(connection, crew_id) is None:
        raise CrewNotFound("That alias does not exist.")
    await connection.execute(
        "UPDATE crew SET status = ? WHERE id = ?",
        (status, crew_id),
    )
    await connection.commit()


async def list_crew(connection: Connection) -> list:
    async with connection.execute(
        "SELECT * FROM crew ORDER BY alias_normalized"
    ) as cursor:
        return await cursor.fetchall()


async def any_admin(connection: Connection) -> bool:
    async with connection.execute(
        "SELECT 1 FROM crew WHERE role = 'admin' LIMIT 1"
    ) as cursor:
        return await cursor.fetchone() is not None


async def set_station(
    connection: Connection, crew_id: int, station: Optional[str]
) -> None:
    if station not in {None, "mess", "drill"}:
        raise CrewStatusError("Station must be mess, drill, or empty.")
    if await get(connection, crew_id) is None:
        raise CrewNotFound("That alias does not exist.")
    await connection.execute(
        "UPDATE crew SET station = ? WHERE id = ?",
        (station, crew_id),
    )
    await connection.commit()


async def set_key_hash(connection: Connection, crew_id: int, key_hash: str) -> None:
    if await get(connection, crew_id) is None:
        raise CrewNotFound("That alias does not exist.")
    await connection.execute(
        "UPDATE crew SET key_hash = ? WHERE id = ?",
        (key_hash, crew_id),
    )
    await connection.commit()


async def delete(connection: Connection, crew_id: int) -> None:
    if await get(connection, crew_id) is None:
        raise CrewNotFound("That alias does not exist.")
    await connection.execute("DELETE FROM crew WHERE id = ?", (crew_id,))
    await connection.commit()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()

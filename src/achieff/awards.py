from datetime import UTC, datetime
from sqlite3 import IntegrityError
from typing import Optional

from aiosqlite import Connection

from achieff import crew


class AwardError(ValueError):
    pass


async def pin(
    connection: Connection,
    crew_id: int,
    badge_id: int,
    *,
    awarded_by: Optional[int] = None,
    awarded_at: Optional[str] = None,
) -> int:
    if await crew.get(connection, crew_id) is None:
        raise AwardError("That alias does not exist.")
    if not await _badge_exists(connection, badge_id):
        raise AwardError("That badge does not exist.")
    if awarded_by is not None and await crew.get(connection, awarded_by) is None:
        raise AwardError("The awarding alias does not exist.")

    when = awarded_at or datetime.now(UTC).isoformat()
    try:
        cursor = await connection.execute(
            """
            INSERT INTO award (crew_id, badge_id, awarded_by, awarded_at)
            VALUES (?, ?, ?, ?)
            """,
            (crew_id, badge_id, awarded_by, when),
        )
        await connection.commit()
    except IntegrityError as error:
        await connection.rollback()
        raise AwardError("That badge is already pinned on this alias.") from error
    return int(cursor.lastrowid)


async def unpin(connection: Connection, crew_id: int, badge_id: int) -> None:
    await connection.execute(
        "DELETE FROM award WHERE crew_id = ? AND badge_id = ?",
        (crew_id, badge_id),
    )
    await connection.commit()


async def _badge_exists(connection: Connection, badge_id: int) -> bool:
    async with connection.execute(
        "SELECT id FROM badge WHERE id = ?",
        (badge_id,),
    ) as cursor:
        return await cursor.fetchone() is not None

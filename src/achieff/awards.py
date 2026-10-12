from datetime import UTC, datetime
from sqlite3 import IntegrityError
from typing import Optional

from aiosqlite import Connection

from achieff import badges, crew


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
    badge = await badges.get(connection, badge_id)
    if badge is None:
        raise AwardError("That badge does not exist.")
    if badge["closed_at"] is not None:
        raise AwardError("That badge is closed to new pins.")
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


async def list_awards(connection: Connection) -> list:
    async with connection.execute(
        """
        SELECT
            award.id AS id,
            award.crew_id AS crew_id,
            award.badge_id AS badge_id,
            crew.alias AS alias,
            badge.title AS title,
            badge.polarity AS polarity
        FROM award
        JOIN crew ON crew.id = award.crew_id
        JOIN badge ON badge.id = award.badge_id
        ORDER BY crew.alias_normalized, badge.sort_order, badge.title
        """
    ) as cursor:
        return await cursor.fetchall()


async def unpin(connection: Connection, crew_id: int, badge_id: int) -> None:
    await connection.execute(
        "DELETE FROM award WHERE crew_id = ? AND badge_id = ?",
        (crew_id, badge_id),
    )
    await connection.commit()

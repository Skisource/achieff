from dataclasses import dataclass
from typing import Optional

from aiosqlite import Connection

from achieff.crew import CrewNotFound


@dataclass(frozen=True)
class Standing:
    alias: str
    merit: int
    infamy: int
    net: int
    first_award_at: Optional[str]
    status: str = "active"
    sprite_variant: int = 0


def net(merit: int, infamy: int) -> int:
    return merit - infamy


def rank(standings: list[Standing]) -> list[Standing]:
    return sorted(standings, key=_sort_key)


async def score_crew(connection: Connection, crew_id: int) -> Standing:
    row = await _standing_row(connection, crew_id)
    if row is None:
        raise CrewNotFound("That alias does not exist.")
    return _standing_from_row(row)


async def leaderboard(connection: Connection) -> list[Standing]:
    async with connection.execute(f"{_SCORE_FROM} GROUP BY c.id") as cursor:
        rows = await cursor.fetchall()
    return rank([_standing_from_row(row) for row in rows])


def _standing_from_row(row) -> Standing:
    merit = int(row["merit"])
    infamy = int(row["infamy"])
    return Standing(
        alias=str(row["alias"]),
        merit=merit,
        infamy=infamy,
        net=net(merit, infamy),
        first_award_at=row["first_award_at"],
        status=str(row["status"]),
        sprite_variant=int(row["sprite_variant"]),
    )


def _sort_key(standing: Standing) -> tuple:
    return (
        -standing.net,
        standing.first_award_at is None,
        standing.first_award_at or "",
        standing.alias.casefold(),
    )


async def _standing_row(connection: Connection, crew_id: int):
    async with connection.execute(
        f"{_SCORE_FROM} WHERE c.id = ? GROUP BY c.id",
        (crew_id,),
    ) as cursor:
        return await cursor.fetchone()


_SCORE_FROM = """
SELECT
    c.alias AS alias,
    c.status AS status,
    c.sprite_variant AS sprite_variant,
    COALESCE(SUM(CASE WHEN b.polarity = 'goody' THEN 1 ELSE 0 END), 0) AS merit,
    COALESCE(SUM(CASE WHEN b.polarity = 'baddy' THEN 1 ELSE 0 END), 0) AS infamy,
    MIN(a.awarded_at) AS first_award_at
FROM crew c
LEFT JOIN award a ON a.crew_id = c.id
LEFT JOIN badge b ON b.id = a.badge_id
"""

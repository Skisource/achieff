from datetime import UTC, datetime
from sqlite3 import IntegrityError

from aiosqlite import Connection

_TITLE_MAX_LENGTH = 60
_POLARITIES = {"goody", "baddy"}

EXAMPLES = (
    ("drilled-through-cable", "Drilled through cable", "baddy", 1),
    ("brought-rig-to-muster", "Brought rig to muster", "baddy", 2),
    ("baked-the-best-cake", "Baked the best cake", "goody", 3),
    ("bought-5-rounds", "Bought 5 rounds", "goody", 4),
)


async def seed_examples(connection: Connection) -> None:
    created_at = datetime.now(UTC).isoformat()
    await connection.executemany(
        """
        INSERT INTO badge (slug, title, polarity, sort_order, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO NOTHING
        """,
        [(*example, created_at) for example in EXAMPLES],
    )


async def list_badges(connection: Connection) -> list:
    async with connection.execute(
        "SELECT * FROM badge ORDER BY sort_order, slug"
    ) as cursor:
        return await cursor.fetchall()


async def get(connection: Connection, badge_id: int):
    async with connection.execute(
        "SELECT * FROM badge WHERE id = ?", (badge_id,)
    ) as cursor:
        return await cursor.fetchone()


async def list_open(connection: Connection) -> list:
    async with connection.execute(
        """
        SELECT * FROM badge
        WHERE closed_at IS NULL
        ORDER BY sort_order, slug
        """
    ) as cursor:
        return await cursor.fetchall()


async def create(
    connection: Connection,
    title: str,
    polarity: str,
    *,
    weight: int = 1,
) -> int:
    cleaned = clean_title(title)
    if polarity not in _POLARITIES:
        raise BadgePolarityError("Polarity must be goody or baddy.")
    slug = slug_for(cleaned)
    if not slug:
        raise BadgeTitleError("Title needs a letter or number.")
    checked = checked_weight(weight)
    sort_order = await _next_sort_order(connection)
    try:
        cursor = await connection.execute(
            """
            INSERT INTO badge (slug, title, polarity, sort_order, weight, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                slug,
                cleaned,
                polarity,
                sort_order,
                checked,
                datetime.now(UTC).isoformat(),
            ),
        )
        await connection.commit()
    except IntegrityError as error:
        await connection.rollback()
        raise BadgeTitleError("That badge already exists.") from error
    return int(cursor.lastrowid)


async def rename(connection: Connection, badge_id: int, title: str) -> None:
    cleaned = clean_title(title)
    if await get(connection, badge_id) is None:
        raise BadgeNotFound("That badge does not exist.")
    await connection.execute(
        "UPDATE badge SET title = ? WHERE id = ?",
        (cleaned, badge_id),
    )
    await connection.commit()


async def set_weight(connection: Connection, badge_id: int, weight: int) -> None:
    if await get(connection, badge_id) is None:
        raise BadgeNotFound("That badge does not exist.")
    await connection.execute(
        "UPDATE badge SET weight = ? WHERE id = ?",
        (checked_weight(weight), badge_id),
    )
    await connection.commit()


async def close(connection: Connection, badge_id: int) -> None:
    if await get(connection, badge_id) is None:
        raise BadgeNotFound("That badge does not exist.")
    await connection.execute(
        """
        UPDATE badge
        SET closed_at = ?
        WHERE id = ? AND closed_at IS NULL
        """,
        (datetime.now(UTC).isoformat(), badge_id),
    )
    await connection.commit()


def checked_weight(weight: int) -> int:
    if weight < 1 or weight > 10:
        raise BadgeWeightError("Weight must be from 1 to 10.")
    return weight


def clean_title(title: str) -> str:
    compact = " ".join(title.split())
    if not compact:
        raise BadgeTitleError("Title is empty.")
    if len(compact) > _TITLE_MAX_LENGTH:
        raise BadgeTitleError("Title is too long.")
    return compact


def slug_for(title: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in title)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


async def _next_sort_order(connection: Connection) -> int:
    async with connection.execute(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order FROM badge"
    ) as cursor:
        row = await cursor.fetchone()
    return int(row["next_order"])


class BadgeTitleError(ValueError):
    pass


class BadgePolarityError(ValueError):
    pass


class BadgeNotFound(LookupError):
    pass


class BadgeWeightError(ValueError):
    pass


async def find_by_slug(connection: Connection, slug: str):
    async with connection.execute(
        "SELECT * FROM badge WHERE slug = ?", (slug,)
    ) as cursor:
        return await cursor.fetchone()

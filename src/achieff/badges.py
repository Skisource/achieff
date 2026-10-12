from datetime import UTC, datetime

from aiosqlite import Connection

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


async def find_by_slug(connection: Connection, slug: str):
    async with connection.execute(
        "SELECT * FROM badge WHERE slug = ?", (slug,)
    ) as cursor:
        return await cursor.fetchone()

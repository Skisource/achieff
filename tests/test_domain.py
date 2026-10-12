import pytest
from aiosqlite import Connection

from achieff import awards, badges, crew, scoring
from achieff.awards import AwardError
from achieff.crew import CrewAliasError, CrewNotFound


async def test_seeded_badges_survive_a_second_migration(connection: Connection) -> None:
    from achieff import db

    await db.migrate()
    rows = await badges.list_badges(connection)

    titles = [row["title"] for row in rows]
    assert titles == [
        "Drilled through cable",
        "Brought rig to muster",
        "Baked the best cake",
        "Bought 5 rounds",
    ]
    assert [row["polarity"] for row in rows] == ["baddy", "baddy", "goody", "goody"]


async def test_new_alias_starts_active(connection: Connection) -> None:
    crew_id = await crew.add(connection, "  Sparky  ")

    row = await crew.get(connection, crew_id)

    assert row["alias"] == "Sparky"
    assert row["status"] == "active"
    assert row["role"] == "crew"
    assert row["key_hash"] is None
    assert 0 <= row["sprite_variant"] < crew.SPRITE_KIT_SIZE


async def test_empty_crew_scores_zero(connection: Connection) -> None:
    crew_id = await crew.add(connection, "Quiet")

    standing = await scoring.score_crew(connection, crew_id)

    assert standing.merit == 0
    assert standing.infamy == 0
    assert standing.net == 0
    assert standing.first_award_at is None


async def test_pin_goody_and_baddy(connection: Connection) -> None:
    crew_id = await crew.add(connection, "Sparky")
    cake = await badges.find_by_slug(connection, "baked-the-best-cake")
    cable = await badges.find_by_slug(connection, "drilled-through-cable")
    await awards.pin(connection, crew_id, int(cake["id"]))
    await awards.pin(connection, crew_id, int(cable["id"]))

    standing = await scoring.score_crew(connection, crew_id)

    assert standing.merit == 1
    assert standing.infamy == 1
    assert standing.net == 0


async def test_second_pin_of_the_same_badge_is_rejected(connection: Connection) -> None:
    crew_id = await crew.add(connection, "Sparky")
    cake = await badges.find_by_slug(connection, "baked-the-best-cake")

    await awards.pin(connection, crew_id, int(cake["id"]))

    with pytest.raises(AwardError):
        await awards.pin(connection, crew_id, int(cake["id"]))


async def test_duplicate_alias_is_rejected(connection: Connection) -> None:
    await crew.add(connection, "Sparky")

    with pytest.raises(CrewAliasError):
        await crew.add(connection, "sparky")


async def test_email_alias_is_rejected(connection: Connection) -> None:
    with pytest.raises(CrewAliasError):
        await crew.add(connection, "sparky@rig.example")


async def test_delete_crew_removes_awards_and_sessions(connection: Connection) -> None:
    crew_id = await crew.add(connection, "Sparky")
    cake = await badges.find_by_slug(connection, "baked-the-best-cake")
    await awards.pin(connection, crew_id, int(cake["id"]))
    await connection.execute(
        """
        INSERT INTO session (crew_id, token_hash, expires_at)
        VALUES (?, ?, ?)
        """,
        (crew_id, "hashed-token", "2026-01-01T00:00:00+00:00"),
    )
    await connection.commit()

    await crew.delete(connection, crew_id)

    assert await crew.get(connection, crew_id) is None
    async with connection.execute("SELECT COUNT(*) AS n FROM award") as cursor:
        awards_left = await cursor.fetchone()
    async with connection.execute("SELECT COUNT(*) AS n FROM session") as cursor:
        sessions_left = await cursor.fetchone()
    async with connection.execute("SELECT COUNT(*) AS n FROM badge") as cursor:
        badges_left = await cursor.fetchone()
    assert awards_left["n"] == 0
    assert sessions_left["n"] == 0
    assert badges_left["n"] == 4
    with pytest.raises(CrewNotFound):
        await scoring.score_crew(connection, crew_id)


async def test_retired_alias_keeps_a_career_score(connection: Connection) -> None:
    crew_id = await crew.add(connection, "Sparky")
    cake = await badges.find_by_slug(connection, "baked-the-best-cake")
    await awards.pin(
        connection,
        crew_id,
        int(cake["id"]),
        awarded_at="2026-01-01T00:00:00+00:00",
    )
    await crew.set_status(connection, crew_id, "retired")

    board = await scoring.leaderboard(connection)

    assert board[0].alias == "Sparky"
    assert board[0].status == "retired"
    assert board[0].merit == 1
    assert board[0].net == 1

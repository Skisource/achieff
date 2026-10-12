from aiosqlite import Connection
from quart import Quart, Response, jsonify, render_template

from achieff import db, pages, scoring
from achieff.retired import icon_index


def register(app: Quart) -> None:
    @app.get("/leaderboard", endpoint="leaderboard")
    async def leaderboard_page() -> str:
        return await render_template("leaderboard.html", page=_page())

    @app.get("/api/leaderboard")
    async def leaderboard_api() -> Response:
        connection = await db.connect()
        try:
            payload = await standings(connection)
        finally:
            await connection.close()
        response = jsonify(payload)
        response.headers["Cache-Control"] = "no-store"
        return response


async def standings(connection: Connection) -> dict[str, object]:
    ranked = [
        standing
        for standing in await scoring.leaderboard(connection)
        if standing.merit or standing.infamy
    ]
    badges = await _badges_by_alias(connection)
    rows = [
        _row(rank, standing, badges.get(standing.alias, []))
        for rank, standing in enumerate(ranked, start=1)
    ]
    return {
        "good_boy": rows[0] if rows else None,
        "nasty": rows[-1] if rows else None,
        "rows": rows,
    }


async def _badges_by_alias(
    connection: Connection,
) -> dict[str, list[dict[str, object]]]:
    async with connection.execute(
        """
        SELECT
            c.alias AS alias,
            b.slug AS slug,
            b.title AS title,
            b.polarity AS polarity
        FROM award
        JOIN crew c ON c.id = award.crew_id
        JOIN badge b ON b.id = award.badge_id
        ORDER BY c.alias_normalized, b.sort_order, b.title
        """
    ) as cursor:
        records = await cursor.fetchall()
    grouped: dict[str, list[dict[str, object]]] = {}
    for record in records:
        alias = str(record["alias"])
        grouped.setdefault(alias, []).append(
            {
                "title": str(record["title"]),
                "polarity": str(record["polarity"]),
                "icon": icon_index(str(record["slug"]), str(record["polarity"])),
            }
        )
    return grouped


def _row(
    rank: int, standing: scoring.Standing, badges: list[dict[str, object]]
) -> dict:
    return {
        "rank": rank,
        "alias": standing.alias,
        "status": standing.status,
        "net": standing.net,
        "merit": standing.merit,
        "infamy": standing.infamy,
        "sprite_variant": standing.sprite_variant,
        "badges": badges,
    }


def _page() -> pages.Page:
    for page in pages.PAGES:
        if page.key == "leaderboard":
            return page
    raise RuntimeError("Leaderboard page is missing from the nav.")

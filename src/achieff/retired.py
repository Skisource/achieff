from aiosqlite import Connection
from quart import Quart, Response, jsonify, render_template

from achieff import db, pages
from achieff.artkit import BADGE_ICONS


def register(app: Quart) -> None:
    @app.get("/retired")
    async def retired() -> str:
        return await render_template("retired.html", page=_page())

    @app.get("/api/retired")
    async def retired_roster() -> Response:
        connection = await db.connect()
        try:
            crew = await retired_crew(connection)
        finally:
            await connection.close()
        response = jsonify(crew=crew)
        response.headers["Cache-Control"] = "no-store"
        return response


async def retired_crew(connection: Connection) -> list[dict[str, object]]:
    async with connection.execute(
        """
        SELECT
            c.alias AS alias,
            c.sprite_variant AS sprite_variant,
            b.slug AS slug,
            b.title AS title,
            b.polarity AS polarity
        FROM crew c
        LEFT JOIN award a ON a.crew_id = c.id
        LEFT JOIN badge b ON b.id = a.badge_id
        WHERE c.status = 'retired'
        ORDER BY c.alias_normalized, b.sort_order, b.title
        """
    ) as cursor:
        rows = await cursor.fetchall()

    people: dict[str, dict[str, object]] = {}
    order: list[str] = []
    for row in rows:
        alias = str(row["alias"])
        if alias not in people:
            people[alias] = {
                "alias": alias,
                "sprite_variant": int(row["sprite_variant"]),
                "badges": [],
            }
            order.append(alias)
        if row["slug"] is None:
            continue
        badges = people[alias]["badges"]
        if isinstance(badges, list):
            badges.append(
                {
                    "title": str(row["title"]),
                    "polarity": str(row["polarity"]),
                    "icon": icon_index(str(row["slug"]), str(row["polarity"])),
                }
            )
    return [people[alias] for alias in order]


def icon_index(slug: str, polarity: str) -> int:
    try:
        return BADGE_ICONS.index(slug)
    except ValueError:
        fallback = "goody" if polarity == "goody" else "baddy"
        return BADGE_ICONS.index(fallback)


def _page() -> pages.Page:
    for page in pages.PAGES:
        if page.key == "retired":
            return page
    raise RuntimeError("Retired page is missing from the nav.")

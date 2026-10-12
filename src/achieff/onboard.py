from aiosqlite import Connection
from quart import Quart, Response, jsonify, render_template

from achieff import db, pages


def register(app: Quart) -> None:
    @app.get("/")
    async def onboard() -> str:
        page = _page()
        return await render_template("onboard.html", page=page)

    @app.get("/api/onboard")
    async def onboard_roster() -> Response:
        connection = await db.connect()
        try:
            crew = await active_crew(connection)
        finally:
            await connection.close()
        response = jsonify(crew=crew)
        response.headers["Cache-Control"] = "no-store"
        return response


async def active_crew(connection: Connection) -> list[dict[str, object]]:
    async with connection.execute(
        """
        SELECT
            c.alias AS alias,
            c.sprite_variant AS sprite_variant,
            c.station AS station,
            COALESCE(
                SUM(
                    CASE
                        WHEN b.polarity = 'goody' THEN COALESCE(b.weight, 1)
                        ELSE 0
                    END
                ),
                0
            ) AS merit,
            COALESCE(
                SUM(
                    CASE
                        WHEN b.polarity = 'baddy' THEN COALESCE(b.weight, 1)
                        ELSE 0
                    END
                ),
                0
            ) AS infamy
        FROM crew c
        LEFT JOIN award a ON a.crew_id = c.id
        LEFT JOIN badge b ON b.id = a.badge_id
        WHERE c.status = 'active'
        GROUP BY c.id
        ORDER BY c.alias_normalized
        """
    ) as cursor:
        rows = await cursor.fetchall()
    return [
        {
            "alias": str(row["alias"]),
            "sprite_variant": int(row["sprite_variant"]),
            "station": row["station"] or "",
            "merit": int(row["merit"]),
            "infamy": int(row["infamy"]),
        }
        for row in rows
    ]


def _page() -> pages.Page:
    for page in pages.PAGES:
        if page.key == "onboard":
            return page
    raise RuntimeError("Onboard page is missing from the nav.")

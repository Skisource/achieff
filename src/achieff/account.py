from quart import Quart, abort, g, redirect, render_template, request, url_for

from achieff import auth, crew, db, keys, pages


def register(app: Quart) -> None:
    @app.get("/me")
    async def me():
        viewer = _signed_in()
        if viewer is None:
            return redirect(url_for("login"))
        issued = keys.take_issued(int(viewer["id"]))
        connection = await db.connect()
        try:
            history = await _history(connection, int(viewer["id"]))
        finally:
            await connection.close()
        issued_key = "" if issued is None else issued[1]
        return await render_template(
            "me.html",
            page=_page("me", "Me", "/me"),
            history=history,
            issued_key=issued_key,
        )

    @app.post("/me/key")
    async def me_key():
        viewer = _signed_in()
        if viewer is None:
            return redirect(url_for("login"))
        form = await request.form
        if not auth.csrf_matches(str(form.get("csrf", ""))):
            abort(400)
        key = keys.generate_key()
        connection = await db.connect()
        try:
            await crew.set_key_hash(connection, int(viewer["id"]), keys.hash_key(key))
        finally:
            await connection.close()
        keys.hold_issued(int(viewer["id"]), str(viewer["alias"]), key)
        return redirect(url_for("me"), code=303)


def _signed_in():
    return getattr(g, "viewer", None)


async def _history(connection, crew_id: int) -> list[dict[str, str]]:
    async with connection.execute(
        """
        SELECT
            badge.title AS title,
            badge.polarity AS polarity,
            award.awarded_at AS awarded_at
        FROM award
        JOIN badge ON badge.id = award.badge_id
        WHERE award.crew_id = ?
        ORDER BY award.awarded_at, badge.title
        """,
        (crew_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    return [
        {
            "title": str(row["title"]),
            "polarity": str(row["polarity"]),
            "awarded_at": str(row["awarded_at"]),
        }
        for row in rows
    ]


def _page(key: str, label: str, path: str) -> pages.Page:
    return pages.Page(
        key=key,
        label=label,
        path=path,
        empty_title="",
        empty_body="",
    )

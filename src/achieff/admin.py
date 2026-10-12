from typing import Optional

from quart import Quart, Response, abort, g, redirect, render_template, request, url_for

from achieff import auth, awards, badges, crew, db, keys, pages
from achieff.awards import AwardError
from achieff.badges import BadgeNotFound, BadgePolarityError, BadgeTitleError
from achieff.crew import CrewAliasError, CrewNotFound, CrewStatusError


def register(app: Quart) -> None:
    @app.get("/admin")
    async def admin():
        blocked = _blocked()
        if blocked is not None:
            return blocked
        issued = keys.take_issued(int(g.viewer["id"]))
        return await _render(issued)

    @app.post("/admin")
    async def admin_submit():
        blocked = _blocked()
        if blocked is not None:
            return blocked
        form = await request.form
        if not auth.csrf_matches(str(form.get("csrf", ""))):
            abort(400)
        connection = await db.connect()
        try:
            error = await _dispatch(connection, form, int(g.viewer["id"]))
        finally:
            await connection.close()
        if error:
            body = await _render(None, error)
            return body, 400
        return redirect(url_for("admin"), code=303)


def _blocked() -> Optional[Response]:
    viewer = getattr(g, "viewer", None)
    if viewer is None:
        return redirect(url_for("login"))
    if viewer["role"] != "admin":
        abort(403)
    return None


async def _render(issued: Optional[tuple[str, str]], error: str = "") -> str:
    connection = await db.connect()
    try:
        people = [_person(row) for row in await crew.list_crew(connection)]
        badge_rows = [_badge(row) for row in await badges.list_badges(connection)]
        open_badges = [_badge(row) for row in await badges.list_open(connection)]
        pinned = [_award_row(row) for row in await awards.list_awards(connection)]
    finally:
        await connection.close()
    issued_alias = ""
    issued_key = ""
    if issued is not None:
        issued_alias, issued_key = issued
    return await render_template(
        "admin.html",
        page=_admin_page(),
        error=error,
        people=people,
        badges=badge_rows,
        open_badges=open_badges,
        pinned=pinned,
        issued_alias=issued_alias,
        issued_key=issued_key,
    )


async def _dispatch(connection, form, admin_id: int) -> Optional[str]:
    action = str(form.get("action", ""))
    if action == "add_crew":
        return await _add_crew(connection, form, admin_id)
    if action == "set_status":
        return await _set_status(connection, form)
    if action == "reissue":
        return await _reissue(connection, form, admin_id)
    if action == "delete_crew":
        return await _delete_crew(connection, form, admin_id)
    if action == "add_badge":
        return await _add_badge(connection, form)
    if action == "rename_badge":
        return await _rename_badge(connection, form)
    if action == "close_badge":
        return await _close_badge(connection, form)
    if action == "pin":
        return await _pin(connection, form, admin_id)
    if action == "unpin":
        return await _unpin(connection, form)
    return "Unknown action."


async def _add_crew(connection, form, admin_id: int) -> Optional[str]:
    alias = str(form.get("alias", ""))
    status = str(form.get("status", "active"))
    try:
        display = crew.normalize_alias(alias)
        key = keys.generate_key()
        await crew.add(
            connection,
            display,
            status=status,
            key_hash=keys.hash_key(key),
        )
    except (CrewAliasError, CrewStatusError) as error:
        return str(error)
    keys.hold_issued(admin_id, display, key)
    return None


async def _set_status(connection, form) -> Optional[str]:
    crew_id = _number(form, "crew_id")
    if crew_id is None:
        return "Choose an alias."
    try:
        await crew.set_status(connection, crew_id, str(form.get("status", "")))
    except (CrewNotFound, CrewStatusError) as error:
        return str(error)
    return None


async def _reissue(connection, form, admin_id: int) -> Optional[str]:
    crew_id = _number(form, "crew_id")
    if crew_id is None:
        return "Choose an alias."
    row = await crew.get(connection, crew_id)
    if row is None:
        return "That alias does not exist."
    key = keys.generate_key()
    await crew.set_key_hash(connection, crew_id, keys.hash_key(key))
    keys.hold_issued(admin_id, str(row["alias"]), key)
    return None


async def _delete_crew(connection, form, admin_id: int) -> Optional[str]:
    crew_id = _number(form, "crew_id")
    if crew_id is None:
        return "Choose an alias."
    if crew_id == admin_id:
        return "You cannot delete the alias you are signed in as."
    row = await crew.get(connection, crew_id)
    if row is None:
        return "That alias does not exist."
    if row["role"] == "admin" and await _admin_count(connection) < 2:
        return "The last admin cannot be deleted."
    await crew.delete(connection, crew_id)
    return None


async def _add_badge(connection, form) -> Optional[str]:
    try:
        await badges.create(
            connection,
            str(form.get("title", "")),
            str(form.get("polarity", "")),
        )
    except (BadgeTitleError, BadgePolarityError) as error:
        return str(error)
    return None


async def _rename_badge(connection, form) -> Optional[str]:
    badge_id = _number(form, "badge_id")
    if badge_id is None:
        return "Choose a badge."
    try:
        await badges.rename(connection, badge_id, str(form.get("title", "")))
    except (BadgeNotFound, BadgeTitleError) as error:
        return str(error)
    return None


async def _close_badge(connection, form) -> Optional[str]:
    badge_id = _number(form, "badge_id")
    if badge_id is None:
        return "Choose a badge."
    try:
        await badges.close(connection, badge_id)
    except BadgeNotFound as error:
        return str(error)
    return None


async def _pin(connection, form, admin_id: int) -> Optional[str]:
    crew_id = _number(form, "crew_id")
    badge_id = _number(form, "badge_id")
    if crew_id is None or badge_id is None:
        return "Choose an alias and a badge."
    try:
        await awards.pin(connection, crew_id, badge_id, awarded_by=admin_id)
    except AwardError as error:
        return str(error)
    return None


async def _unpin(connection, form) -> Optional[str]:
    crew_id = _number(form, "crew_id")
    badge_id = _number(form, "badge_id")
    if crew_id is None or badge_id is None:
        return "Choose an award."
    await awards.unpin(connection, crew_id, badge_id)
    return None


async def _admin_count(connection) -> int:
    async with connection.execute(
        "SELECT COUNT(*) AS n FROM crew WHERE role = 'admin'"
    ) as cursor:
        row = await cursor.fetchone()
    return int(row["n"])


def _person(row) -> dict:
    return {
        "id": int(row["id"]),
        "alias": str(row["alias"]),
        "status": str(row["status"]),
        "role": str(row["role"]),
        "has_key": row["key_hash"] is not None,
    }


def _badge(row) -> dict:
    return {
        "id": int(row["id"]),
        "title": str(row["title"]),
        "polarity": str(row["polarity"]),
        "closed": row["closed_at"] is not None,
    }


def _award_row(row) -> dict:
    return {
        "crew_id": int(row["crew_id"]),
        "badge_id": int(row["badge_id"]),
        "alias": str(row["alias"]),
        "title": str(row["title"]),
        "polarity": str(row["polarity"]),
    }


def _number(form, name: str) -> Optional[int]:
    raw = str(form.get(name, ""))
    if not raw.isdigit():
        return None
    return int(raw)


def _admin_page() -> pages.Page:
    for page in pages.PAGES:
        if page.key == "admin":
            return page
    raise RuntimeError("Admin page is missing from the nav.")

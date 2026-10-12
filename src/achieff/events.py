from datetime import UTC, datetime
from sqlite3 import IntegrityError
from typing import Optional

from aiosqlite import Connection
from quart import Quart, abort, g, redirect, render_template, request, url_for

from achieff import auth, crew, db, pages


class EventError(ValueError):
    pass


def register(app: Quart) -> None:
    @app.get("/events")
    async def events_page():
        connection = await db.connect()
        try:
            current = await open_events(connection)
        finally:
            await connection.close()
        return await render_template(
            "events.html",
            page=_nav_page(),
            events=current,
            error="",
        )

    @app.post("/events/join")
    async def events_join():
        viewer = getattr(g, "viewer", None)
        if viewer is None:
            return redirect(url_for("login"))
        form = await request.form
        if not auth.csrf_matches(str(form.get("csrf", ""))):
            abort(400)
        raw = str(form.get("event_id", ""))
        if not raw.isdigit():
            abort(400)
        connection = await db.connect()
        try:
            await join_event(connection, int(raw), int(viewer["id"]))
        except EventError as error:
            current = await open_events(connection)
            return await render_template(
                "events.html",
                page=_nav_page(),
                events=current,
                error=str(error),
            ), 400
        finally:
            await connection.close()
        return redirect(url_for("events_page"), code=303)


def _nav_page() -> pages.Page:
    return pages.Page(
        key="events",
        label="Events",
        path="/events",
        empty_title="",
        empty_body="",
    )


def stamp(moment: Optional[datetime] = None) -> str:
    current = moment or datetime.now(UTC)
    return current.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def parse_when(value: str) -> str:
    text = value.strip()
    if len(text) == 16:
        text = f"{text}:00+00:00"
    if len(text) != 25 or text[10] != "T":
        raise EventError("Choose a start and an end.")
    return text


async def create_event(
    connection: Connection,
    title: str,
    opens_at: str,
    closes_at: str,
    created_by: int,
) -> int:
    cleaned = " ".join(title.split())
    if not cleaned or len(cleaned) > 60:
        raise EventError("Give the event a short title.")
    opens = parse_when(opens_at)
    closes = parse_when(closes_at)
    if opens >= closes:
        raise EventError("The event must end after it starts.")
    cursor = await connection.execute(
        """
        INSERT INTO event (title, opens_at, closes_at, created_by)
        VALUES (?, ?, ?, ?)
        """,
        (cleaned, opens, closes, created_by),
    )
    await connection.commit()
    return int(cursor.lastrowid)


async def list_events(connection: Connection) -> list[dict[str, object]]:
    async with connection.execute(
        """
        SELECT
            event.id AS id,
            event.title AS title,
            event.opens_at AS opens_at,
            event.closes_at AS closes_at,
            crew.alias AS alias
        FROM event
        LEFT JOIN participation ON participation.event_id = event.id
        LEFT JOIN crew ON crew.id = participation.crew_id
        ORDER BY event.opens_at, event.id, crew.alias_normalized
        """
    ) as cursor:
        rows = await cursor.fetchall()
    return _group_events(rows)


async def open_events(connection: Connection) -> list[dict[str, object]]:
    now = stamp()
    events = await list_events(connection)
    return [event for event in events if event["opens_at"] <= now < event["closes_at"]]


async def join_event(connection: Connection, event_id: int, crew_id: int) -> None:
    now = stamp()
    async with connection.execute(
        "SELECT opens_at, closes_at FROM event WHERE id = ?",
        (event_id,),
    ) as cursor:
        event = await cursor.fetchone()
    if event is None:
        raise EventError("That event does not exist.")
    if not (event["opens_at"] <= now < event["closes_at"]):
        raise EventError("That event is not open.")
    if await crew.get(connection, crew_id) is None:
        raise EventError("That alias does not exist.")
    try:
        await connection.execute(
            """
            INSERT INTO participation (event_id, crew_id, joined_at)
            VALUES (?, ?, ?)
            """,
            (event_id, crew_id, now),
        )
        await connection.commit()
    except IntegrityError:
        await connection.rollback()


def _group_events(rows) -> list[dict[str, object]]:
    grouped: dict[int, dict[str, object]] = {}
    order: list[int] = []
    for row in rows:
        event_id = int(row["id"])
        if event_id not in grouped:
            grouped[event_id] = {
                "id": event_id,
                "title": str(row["title"]),
                "opens_at": str(row["opens_at"]),
                "closes_at": str(row["closes_at"]),
                "participants": [],
            }
            order.append(event_id)
        if row["alias"] is not None:
            participants = grouped[event_id]["participants"]
            if isinstance(participants, list):
                participants.append(str(row["alias"]))
    return [grouped[event_id] for event_id in order]

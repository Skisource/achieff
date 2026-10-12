import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from quart import Quart

from achieff import badges, crew, db, events, keys, live
from achieff.badges import BadgeWeightError
from achieff.crew import CrewStatusError


async def _csrf(client) -> str:
    response = await client.get("/login")
    raw = response.headers["Set-Cookie"]
    return raw.split("achieff_csrf=", 1)[1].split(";", 1)[0]


async def _login(client, alias: str, key: str) -> str:
    token = await _csrf(client)
    response = await client.post(
        "/login",
        form={"alias": alias, "key": key, "csrf": token},
    )
    assert response.status_code == 303
    return token


@pytest.mark.asyncio
async def test_badge_weight_changes_merit(application: Quart) -> None:
    connection = await db.connect()
    try:
        badge = await badges.create(connection, "Heavy lift", "goody", weight=4)
        person = await crew.add(connection, "Hauler", key_hash=keys.hash_key("a" * 32))
        await connection.execute(
            "INSERT INTO award (crew_id, badge_id, awarded_at) VALUES (?, ?, ?)",
            (person, badge, "2026-10-12T00:00:00+00:00"),
        )
        await connection.commit()
    finally:
        await connection.close()

    async with application.test_client() as client:
        response = await client.get("/api/leaderboard")

    payload = await response.get_json()
    assert payload["rows"][0]["merit"] == 4


@pytest.mark.asyncio
async def test_weight_must_stay_between_one_and_ten(application: Quart) -> None:
    connection = await db.connect()
    try:
        with pytest.raises(BadgeWeightError):
            await badges.create(connection, "Too heavy", "goody", weight=11)
            person = await crew.add(connection, "Deckhand")
            with pytest.raises(CrewStatusError):
                await crew.set_station(connection, person, "bridge")
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_signed_in_alias_can_join_an_open_event(application: Quart) -> None:
    key = keys.generate_key()
    connection = await db.connect()
    try:
        person = await crew.add(connection, "Joiner", key_hash=keys.hash_key(key))
        opens = (datetime.now(UTC) - timedelta(minutes=5)).strftime(
            "%Y-%m-%dT%H:%M:%S+00:00"
        )
        closes = (datetime.now(UTC) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%S+00:00"
        )
        event_id = await events.create_event(
            connection,
            "Safety stand-down",
            opens,
            closes,
            person,
        )
    finally:
        await connection.close()

    async with application.test_client() as client:
        token = await _login(client, "Joiner", key)
        response = await client.post(
            "/events/join",
            form={"csrf": token, "event_id": str(event_id)},
        )
        assert response.status_code == 303
        page = await client.get("/events")

    body = await page.get_data(as_text=True)
    assert "Joiner" in body
    connection = await db.connect()
    try:
        async with connection.execute("SELECT COUNT(*) AS count FROM award") as cursor:
            row = await cursor.fetchone()
        assert row["count"] == 0
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_own_key_rotation_keeps_the_session(application: Quart) -> None:
    key = keys.generate_key()
    connection = await db.connect()
    try:
        await crew.add(connection, "Keeper", key_hash=keys.hash_key(key))
    finally:
        await connection.close()

    async with application.test_client() as client:
        token = await _login(client, "Keeper", key)
        response = await client.post("/me/key", form={"csrf": token})
        assert response.status_code == 303
        page = await client.get("/me")

    body = await page.get_data(as_text=True)
    assert "New key" in body
    fresh = body.split("<code>", 1)[1].split("</code>", 1)[0]
    async with application.test_client() as other:
        token = await _csrf(other)
        denied = await other.post(
            "/login",
            form={"alias": "Keeper", "key": key, "csrf": token},
        )
        assert denied.status_code == 401
        accepted = await other.post(
            "/login",
            form={"alias": "Keeper", "key": fresh, "csrf": token},
        )
    assert accepted.status_code == 303


@pytest.mark.asyncio
async def test_live_board_hears_a_refresh(application: Quart) -> None:
    async with application.test_client() as client:
        async with client.websocket("/live") as socket:
            for _ in range(50):
                if socket.accepted:
                    break
                await asyncio.sleep(0.01)
            assert socket.accepted
            live.publish()
            assert await socket.receive() == "refresh"

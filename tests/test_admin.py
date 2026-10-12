import re
from pathlib import Path

import pytest
from pytest import CaptureFixture, MonkeyPatch
from quart import Quart

from achieff import app as app_module
from achieff import badges, crew, db, keys

_BOOTSTRAP_ALIAS = "Boss"


@pytest.fixture
def admin_app(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> tuple[Quart, str]:
    monkeypatch.setenv("ACHIEFF_DATA_DIR", str(tmp_path / "ship-data"))
    monkeypatch.setenv("ACHIEFF_SECRET_KEY", "test-secret-key-value")
    monkeypatch.setenv("ACHIEFF_BOOTSTRAP_ALIAS", _BOOTSTRAP_ALIAS)
    application = app_module.create_app()
    output = capsys.readouterr().out
    match = re.search(r"key=([0-9a-f]{4}(?:-[0-9a-f]{4}){7})", output)
    assert match is not None
    return application, match.group(1)


def test_generated_key_round_trip() -> None:
    key = keys.generate_key()
    stored = keys.hash_key(key)
    assert keys.verify_key(stored, key)
    assert keys.verify_key(stored, key.replace("-", ""))
    assert not keys.verify_key(stored, "0000-0000-0000-0000-0000-0000-0000-0000")
    assert key not in stored


async def test_admin_page_requires_an_admin(application: Quart) -> None:
    client = application.test_client()

    response = await client.get("/admin")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


async def test_fresh_database_is_managed_from_the_admin_ui(
    admin_app: tuple[Quart, str],
) -> None:
    application, admin_key = admin_app
    client = application.test_client()
    await _login(client, _BOOTSTRAP_ALIAS, admin_key)

    created = await _submit(
        client,
        {"action": "add_crew", "alias": "Rigger", "status": "active"},
    )
    assert created.status_code == 303
    shown = await client.get("/admin")
    shown_body = await shown.get_data(as_text=True)
    issued = _issued_key(shown_body)
    assert "Rigger" in shown_body
    assert issued not in shown_body.replace(f"<code>{issued}</code>", "")
    again = await client.get("/admin")
    assert issued not in await again.get_data(as_text=True)

    connection = await db.connect()
    try:
        rigger = await crew.find_by_alias(connection, "Rigger")
        assert rigger is not None
        assert issued.encode() not in db.database_path().read_bytes()
        assert keys.verify_key(rigger["key_hash"], issued)
        await _submit(
            client,
            {"action": "add_badge", "title": "Won the raffle", "polarity": "goody"},
        )
        raffle = await badges.find_by_slug(connection, "won-the-raffle")
        assert raffle is not None
        pinned = await _submit(
            client,
            {
                "action": "pin",
                "crew_id": str(rigger["id"]),
                "badge_id": str(raffle["id"]),
            },
        )
        assert pinned.status_code == 303
        await badges.close(connection, int(raffle["id"]))
        closed = await _submit(
            client,
            {
                "action": "pin",
                "crew_id": str(rigger["id"]),
                "badge_id": str(raffle["id"]),
            },
        )
        assert closed.status_code == 400
        await _submit(client, {"action": "delete_crew", "crew_id": str(rigger["id"])})
        assert await crew.find_by_alias(connection, "Rigger") is None
        board = await scoring_aliases(connection)
    finally:
        await connection.close()
    assert "Rigger" not in board


async def test_reissue_replaces_the_old_key(admin_app: tuple[Quart, str]) -> None:
    application, admin_key = admin_app
    client = application.test_client()
    await _login(client, _BOOTSTRAP_ALIAS, admin_key)
    await _submit(client, {"action": "add_crew", "alias": "Rigger", "status": "active"})
    first = _issued_key(await (await client.get("/admin")).get_data(as_text=True))

    connection = await db.connect()
    try:
        rigger = await crew.find_by_alias(connection, "Rigger")
    finally:
        await connection.close()
    assert rigger is not None

    await _submit(client, {"action": "reissue", "crew_id": str(rigger["id"])})
    second = _issued_key(await (await client.get("/admin")).get_data(as_text=True))
    connection = await db.connect()
    try:
        refreshed = await crew.find_by_alias(connection, "Rigger")
    finally:
        await connection.close()
    assert refreshed is not None
    assert not keys.verify_key(refreshed["key_hash"], first)
    assert keys.verify_key(refreshed["key_hash"], second)


async def test_crew_login_lands_on_the_leaderboard(admin_app: tuple[Quart, str]) -> None:
    application, admin_key = admin_app
    client = application.test_client()
    await _login(client, _BOOTSTRAP_ALIAS, admin_key)
    await _submit(client, {"action": "add_crew", "alias": "Rigger", "status": "active"})
    crew_key = _issued_key(await (await client.get("/admin")).get_data(as_text=True))
    await _logout(client)

    signed_in = await _login(client, "Rigger", crew_key)
    board = await client.get("/leaderboard")
    body = await board.get_data(as_text=True)
    onboard = await client.get("/")

    assert signed_in.status_code == 303
    assert signed_in.headers["Location"].endswith("/leaderboard")
    assert board.status_code == 200
    assert "Signed in as Rigger" in body
    assert onboard.status_code == 200


async def test_login_locks_after_repeated_failures(
    admin_app: tuple[Quart, str],
    monkeypatch: MonkeyPatch,
) -> None:
    from achieff import login_limit

    monkeypatch.setattr(login_limit, "MAX_FAILURES", 2)
    application, admin_key = admin_app
    client = application.test_client()
    wrong = await _login(client, _BOOTSTRAP_ALIAS, "0000-0000-0000-0000-0000-0000-0000-0000")
    missing = await _login(client, "Nobody", admin_key)
    blocked = await _login(client, _BOOTSTRAP_ALIAS, admin_key)

    assert wrong.status_code == 401
    assert missing.status_code == 401
    assert "Alias or key is wrong." in await wrong.get_data(as_text=True)
    assert "Alias or key is wrong." in await missing.get_data(as_text=True)
    assert blocked.status_code == 429
    assert "Too many attempts. Try again shortly." in await blocked.get_data(as_text=True)
    assert (await client.get("/admin")).status_code == 302


async def test_crew_key_cannot_open_admin(admin_app: tuple[Quart, str]) -> None:
    application, admin_key = admin_app
    client = application.test_client()
    await _login(client, _BOOTSTRAP_ALIAS, admin_key)
    await _submit(client, {"action": "add_crew", "alias": "Rigger", "status": "active"})
    crew_key = _issued_key(await (await client.get("/admin")).get_data(as_text=True))
    await _logout(client)
    await _login(client, "Rigger", crew_key)

    response = await client.get("/admin")

    assert response.status_code == 403


async def test_wrong_key_matches_unknown_alias(admin_app: tuple[Quart, str]) -> None:
    application, admin_key = admin_app
    client = application.test_client()
    wrong = await _login(client, _BOOTSTRAP_ALIAS, admin_key[:-1] + "0")
    missing = await _login(client, "Nobody", admin_key)
    wrong_body = await wrong.get_data(as_text=True)
    missing_body = await missing.get_data(as_text=True)

    assert wrong.status_code == 401
    assert missing.status_code == 401
    assert "Alias or key is wrong." in wrong_body
    assert wrong_body == missing_body or "Alias or key is wrong." in missing_body


async def test_admin_post_without_csrf_is_rejected(
    admin_app: tuple[Quart, str],
) -> None:
    application, admin_key = admin_app
    client = application.test_client()
    await _login(client, _BOOTSTRAP_ALIAS, admin_key)

    response = await client.post(
        "/admin", form={"action": "add_crew", "alias": "Rigger"}
    )

    assert response.status_code == 400


async def test_version_1_database_gains_closed_at(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("ACHIEFF_DATA_DIR", str(tmp_path / "ship-data"))
    connection = await db.connect()
    await connection.executescript(db.MIGRATIONS[0])
    await connection.close()

    await db.migrate()

    connection = await db.connect()
    try:
        names = await db.column_names(connection)
    finally:
        await connection.close()
    assert "closed_at" in names


async def _login(client, alias: str, key: str):
    page = await client.get("/login")
    token = _csrf(await page.get_data(as_text=True))
    return await client.post(
        "/login",
        form={"csrf": token, "alias": alias, "key": key},
    )


async def _logout(client) -> None:
    page = await client.get("/leaderboard")
    token = _csrf(await page.get_data(as_text=True))
    await client.post("/logout", form={"csrf": token})


async def _submit(client, fields: dict[str, str]):
    page = await client.get("/admin")
    token = _csrf(await page.get_data(as_text=True))
    payload = {"csrf": token, **fields}
    return await client.post("/admin", form=payload)


def _csrf(body: str) -> str:
    match = re.search(r'name="csrf" value="([^"]+)"', body)
    assert match is not None
    return match.group(1)


def _issued_key(body: str) -> str:
    match = re.search(r"<code>([0-9a-f]{4}(?:-[0-9a-f]{4}){7})</code>", body)
    assert match is not None
    return match.group(1)


async def scoring_aliases(connection) -> list[str]:
    from achieff import scoring

    board = await scoring.leaderboard(connection)
    return [item.alias for item in board]

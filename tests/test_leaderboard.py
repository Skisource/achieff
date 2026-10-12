from quart import Quart

from achieff import awards, badges, crew


async def test_callouts_match_the_ends_of_the_table(
    application: Quart, connection
) -> None:
    client = application.test_client()
    saint = await crew.add(connection, "Saint", status="retired")
    ann = await crew.add(connection, "Ann")
    bea = await crew.add(connection, "Bea")
    menace = await crew.add(connection, "Menace")
    await crew.add(connection, "Quiet")
    cake = await badges.find_by_slug(connection, "baked-the-best-cake")
    cable = await badges.find_by_slug(connection, "drilled-through-cable")
    await awards.pin(
        connection, saint, int(cake["id"]), awarded_at="2026-01-01T00:00:00+00:00"
    )
    await awards.pin(
        connection, ann, int(cake["id"]), awarded_at="2026-02-01T00:00:00+00:00"
    )
    await awards.pin(
        connection, ann, int(cable["id"]), awarded_at="2026-02-02T00:00:00+00:00"
    )
    await awards.pin(
        connection, bea, int(cake["id"]), awarded_at="2026-03-01T00:00:00+00:00"
    )
    await awards.pin(
        connection, bea, int(cable["id"]), awarded_at="2026-03-02T00:00:00+00:00"
    )
    await awards.pin(
        connection, menace, int(cable["id"]), awarded_at="2026-04-01T00:00:00+00:00"
    )

    page = await client.get("/leaderboard")
    body = await page.get_data(as_text=True)
    payload = await (await client.get("/api/leaderboard")).get_json()
    aliases = [row["alias"] for row in payload["rows"]]

    assert page.status_code == 200
    assert "No badges awarded yet." in body
    assert "Badges are awarded from admin." in body
    assert aliases == ["Saint", "Ann", "Bea", "Menace"]
    assert "Quiet" not in aliases
    assert payload["good_boy"]["alias"] == aliases[0]
    assert payload["nasty"]["alias"] == aliases[-1]
    assert payload["rows"][0]["rank"] == 1
    assert payload["rows"][0]["status"] == "retired"
    assert payload["rows"][0]["net"] == 1
    assert payload["rows"][-1]["rank"] == 4
    assert payload["rows"][-1]["net"] == -1
    assert payload["rows"][0]["badges"][0]["icon"] == 2

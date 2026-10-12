from quart import Quart

from achieff import awards, badges, crew
from achieff.retired import icon_index


def test_known_badge_uses_its_own_icon() -> None:
    assert icon_index("baked-the-best-cake", "goody") == 2
    assert icon_index("a-new-legend", "goody") == 4
    assert icon_index("a-new-menace", "baddy") == 5


async def test_honor_roll_and_ship_are_disjoint(application: Quart, connection) -> None:
    client = application.test_client()
    await crew.add(connection, "Walker")
    retired_id = await crew.add(connection, "Oldhand", status="retired")
    cake = await badges.find_by_slug(connection, "baked-the-best-cake")
    await awards.pin(connection, retired_id, int(cake["id"]))

    page = await client.get("/retired")
    body = await page.get_data(as_text=True)
    onboard = await (await client.get("/api/onboard")).get_json()
    honor = await (await client.get("/api/retired")).get_json()

    assert page.status_code == 200
    assert "No retired legends yet." in body
    assert [person["alias"] for person in onboard["crew"]] == ["Walker"]
    assert honor["crew"] == [
        {
            "alias": "Oldhand",
            "sprite_variant": int(
                (await crew.find_by_alias(connection, "Oldhand"))["sprite_variant"]
            ),
            "badges": [
                {
                    "title": "Baked the best cake",
                    "polarity": "goody",
                    "icon": 2,
                }
            ],
        }
    ]

    await crew.set_status(connection, retired_id, "active")
    emptied = await (await client.get("/api/retired")).get_json()
    restored = await (await client.get("/api/onboard")).get_json()
    assert emptied["crew"] == []
    assert {person["alias"] for person in restored["crew"]} == {"Oldhand", "Walker"}

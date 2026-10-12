import json
from pathlib import Path

from quart import Quart

from achieff import awards, badges, crew

_MAP = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "achieff"
    / "static"
    / "art"
    / "ship_map.json"
)
_DECK = 2


def test_waypoints_stay_on_deck_tiles() -> None:
    payload = json.loads(_MAP.read_text())
    tiles = payload["tiles"]
    columns = payload["columns"]
    assert len(tiles) == columns * payload["rows"]
    points = {point["id"]: point for point in payload["waypoints"]}
    assert len(points) == len(payload["waypoints"])
    for point in payload["waypoints"]:
        index = point["y"] * columns + point["x"]
        assert tiles[index] == _DECK
    for left, right in payload["edges"]:
        start = points[left]
        end = points[right]
        manhattan = abs(start["x"] - end["x"]) + abs(start["y"] - end["y"])
        assert start["x"] == end["x"] or start["y"] == end["y"]
        assert 1 <= manhattan <= 4


async def test_onboard_page_has_the_ship(application: Quart) -> None:
    client = application.test_client()

    response = await client.get("/")

    assert response.status_code == 200
    body = await response.get_data(as_text=True)
    assert "The drillship is empty." in body
    assert "onboard-canvas" in body
    assert "ship_map.json" in body or "onboard.js" in body


async def test_retired_alias_leaves_the_ship(application: Quart, connection) -> None:
    client = application.test_client()
    await crew.add(connection, "Walker")
    retired_id = await crew.add(connection, "Oldhand")
    cake = await badges.find_by_slug(connection, "baked-the-best-cake")
    cable = await badges.find_by_slug(connection, "drilled-through-cable")
    walker = await crew.find_by_alias(connection, "Walker")
    await awards.pin(connection, int(walker["id"]), int(cake["id"]))
    await awards.pin(connection, retired_id, int(cable["id"]))
    await crew.set_status(connection, retired_id, "retired")

    response = await client.get("/api/onboard")
    payload = await response.get_json()

    assert response.status_code == 200
    assert payload["crew"] == [
        {
            "alias": "Walker",
            "sprite_variant": int(walker["sprite_variant"]),
            "station": "",
            "merit": 1,
            "infamy": 0,
        }
    ]

    await crew.set_status(connection, retired_id, "active")
    restored = await (await client.get("/api/onboard")).get_json()
    aliases = [person["alias"] for person in restored["crew"]]
    assert aliases == ["Oldhand", "Walker"]
    oldhand = next(
        person for person in restored["crew"] if person["alias"] == "Oldhand"
    )
    assert oldhand["infamy"] == 1

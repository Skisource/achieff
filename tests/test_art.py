import struct
from pathlib import Path

from pytest import MonkeyPatch
from quart import Quart

from achieff import artkit
from achieff.crew import SPRITE_KIT_SIZE

_ART = Path(__file__).resolve().parents[1] / "src" / "achieff" / "static" / "art"


def test_sheets_use_the_16px_grid(tmp_path: Path) -> None:
    artkit.write_sheets(tmp_path)
    expected = {
        "walk.png": (64, 48),
        "idle.png": (32, 48),
        "mugshot.png": (32, 32),
        "ship.png": (112, 16),
        "badges.png": (96, 16),
    }
    for name, size in expected.items():
        assert _png_size(tmp_path / name) == size
        assert (tmp_path / name).read_bytes() == (_ART / name).read_bytes()
    assert len(artkit.VARIANTS) == SPRITE_KIT_SIZE
    assert len(artkit.SHIP_TILES) == 7
    assert len(artkit.BADGE_ICONS) == 6


def test_walk_sheet_has_recolor_keys() -> None:
    colors = set(artkit.walk_sheet().pixels)
    assert artkit.COVERALL in colors
    assert artkit.HAT in colors


async def test_art_preview_steps_are_visible(application: Quart) -> None:
    client = application.test_client()

    response = await client.get("/dev/art")

    assert response.status_code == 200
    body = await response.get_data(as_text=True)
    assert "Next frame" in body
    assert "art/walk.png" in body
    assert "art/ship.png" in body
    assert "art/badges.png" in body


async def test_art_preview_is_off_in_production(
    application: Quart,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("ACHIEFF_ENV", "production")
    client = application.test_client()

    response = await client.get("/dev/art")

    assert response.status_code == 404


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    return struct.unpack(">II", data[16:24])

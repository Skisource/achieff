import json
import os
import struct
import zlib
from pathlib import Path

from achieff.crew import SPRITE_KIT_SIZE

TRANSPARENT = (0, 0, 0, 0)
OUTLINE = (18, 24, 38, 255)
HAT = (242, 193, 78, 255)
SKIN = (242, 199, 165, 255)
COVERALL = (224, 122, 61, 255)
BOOT = (44, 51, 60, 255)
STEEL = (92, 103, 112, 255)
STEEL_LIGHT = (197, 206, 214, 255)
SEA_DARK = (26, 58, 74, 255)
SEA = (46, 107, 122, 255)
SEA_LIGHT = (126, 200, 195, 255)
WINDOW = (246, 213, 138, 255)
RED = (194, 59, 74, 255)
WHITE = (242, 242, 242, 255)
NIGHT = (18, 24, 38, 255)

VARIANTS = (
    {"coverall": "#e07a3d", "hat": "#f2c14e"},
    {"coverall": "#3d6ea8", "hat": "#f2c14e"},
    {"coverall": "#3aa76d", "hat": "#f2f2f2"},
    {"coverall": "#c23b4a", "hat": "#f2c14e"},
    {"coverall": "#e07a3d", "hat": "#3d6ea8"},
    {"coverall": "#3d6ea8", "hat": "#3aa76d"},
    {"coverall": "#5c6770", "hat": "#f2c14e"},
    {"coverall": "#c23b4a", "hat": "#f2f2f2"},
)

if len(VARIANTS) != SPRITE_KIT_SIZE:
    raise RuntimeError("Art kit variants must match the crew sprite kit.")

SHIP_TILES = ("sea", "hull", "deck", "derrick", "moonpool", "mess", "helideck")
BADGE_ICONS = (
    "drilled-through-cable",
    "brought-rig-to-muster",
    "baked-the-best-cake",
    "bought-5-rounds",
    "goody",
    "baddy",
)

_COLORS = {
    "Y": HAT,
    "S": SKIN,
    "O": COVERALL,
    "B": BOOT,
    "L": STEEL_LIGHT,
    "D": SEA_DARK,
    "W": WHITE,
    "R": RED,
}


class Image:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.pixels = [TRANSPARENT] * (width * height)

    def get(self, x: int, y: int) -> tuple[int, int, int, int]:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return TRANSPARENT
        return self.pixels[y * self.width + x]

    def set(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        if color[3] == 0:
            return
        self.pixels[y * self.width + x] = color

    def blit(self, other: Image, dx: int, dy: int) -> None:
        for y in range(other.height):
            for x in range(other.width):
                self.set(x + dx, y + dy, other.get(x, y))

    def copy(self) -> Image:
        clone = Image(self.width, self.height)
        clone.pixels = list(self.pixels)
        return clone


def preview_enabled() -> bool:
    return os.environ.get("ACHIEFF_ENV", "").casefold() != "production"


def walk_sheet() -> Image:
    right = (
        _figure(_STRIDE_A),
        _shift_up(_figure(_TOGETHER)),
        _figure(_STRIDE_B),
        _shift_up(_figure(_TOGETHER)),
    )
    left = tuple(_mirror(frame) for frame in right)
    return _sheet([*right, *left], columns=4)


def idle_sheet() -> Image:
    standing = _figure(_TOGETHER)
    bob = _shift_up(standing)
    return _sheet([standing, bob, _mirror(standing), _mirror(bob)], columns=2)


def mugshot_sheet() -> Image:
    return _mugshot()


def ship_sheet() -> Image:
    tiles = (
        _sea_tile(),
        _hull_tile(),
        _deck_tile(),
        _derrick_tile(),
        _moonpool_tile(),
        _mess_tile(),
        _helideck_tile(),
    )
    return _sheet(list(tiles), columns=len(tiles))


def badge_sheet() -> Image:
    icons = (
        _cable_icon(),
        _muster_icon(),
        _cake_icon(),
        _rounds_icon(),
        _star_icon(),
        _cross_icon(),
    )
    return _sheet(list(icons), columns=len(icons))


def write_sheets(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, image in _named_sheets():
        _write_png(directory / name, image)
    payload = {
        "coverall": "#e07a3d",
        "hat": "#f2c14e",
        "variants": list(VARIANTS),
    }
    (directory / "variants.json").write_text(json.dumps(payload, indent=2) + "\n")


def _named_sheets() -> tuple[tuple[str, Image], ...]:
    return (
        ("walk.png", walk_sheet()),
        ("idle.png", idle_sheet()),
        ("mugshot.png", mugshot_sheet()),
        ("ship.png", ship_sheet()),
        ("badges.png", badge_sheet()),
    )


def _figure(legs: tuple[str, ...]) -> Image:
    return _outline(_parse((*_BODY, *legs)))


def _parse(lines: tuple[str, ...]) -> Image:
    if not lines:
        raise ValueError("Empty sprite.")
    width = len(lines[0])
    image = Image(width, len(lines))
    for y, line in enumerate(lines):
        if len(line) != width:
            raise ValueError("Sprite rows must share one width.")
        for x, symbol in enumerate(line):
            if symbol == ".":
                continue
            image.set(x, y, _COLORS[symbol])
    return image


def _outline(source: Image) -> Image:
    outlined = source.copy()
    for y in range(source.height):
        for x in range(source.width):
            if source.get(x, y)[3]:
                continue
            neighbors = (
                source.get(x - 1, y),
                source.get(x + 1, y),
                source.get(x, y - 1),
                source.get(x, y + 1),
            )
            if any(color[3] for color in neighbors):
                outlined.set(x, y, OUTLINE)
    return outlined


def _mirror(source: Image) -> Image:
    mirrored = Image(source.width, source.height)
    for y in range(source.height):
        for x in range(source.width):
            mirrored.set(source.width - 1 - x, y, source.get(x, y))
    return mirrored


def _shift_up(source: Image) -> Image:
    shifted = Image(source.width, source.height)
    for y in range(source.height):
        for x in range(source.width):
            shifted.set(x, y - 1, source.get(x, y))
    return shifted


def _sheet(frames: list[Image], columns: int) -> Image:
    frame = frames[0]
    rows = (len(frames) + columns - 1) // columns
    image = Image(frame.width * columns, frame.height * rows)
    for index, sprite in enumerate(frames):
        image.blit(
            sprite, (index % columns) * frame.width, (index // columns) * frame.height
        )
    return image


def _fill(image: Image, color: tuple[int, int, int, int]) -> None:
    for y in range(image.height):
        for x in range(image.width):
            image.set(x, y, color)


def _rect(
    image: Image,
    x: int,
    y: int,
    width: int,
    height: int,
    color: tuple[int, int, int, int],
) -> None:
    for yy in range(y, y + height):
        for xx in range(x, x + width):
            image.set(xx, yy, color)


def _sea_tile() -> Image:
    image = Image(16, 16)
    _fill(image, SEA_DARK)
    _rect(image, 0, 9, 16, 3, SEA)
    _rect(image, 0, 13, 16, 3, SEA_LIGHT)
    return image


def _hull_tile() -> Image:
    image = Image(16, 16)
    _fill(image, BOOT)
    _rect(image, 0, 4, 16, 1, STEEL)
    _rect(image, 0, 10, 16, 1, STEEL)
    for x in (3, 11):
        image.set(x, 6, STEEL_LIGHT)
        image.set(x, 12, STEEL_LIGHT)
    return image


def _deck_tile() -> Image:
    image = Image(16, 16)
    _fill(image, STEEL)
    for y in range(0, 16, 4):
        _rect(image, 0, y, 16, 1, BOOT)
    return image


def _derrick_tile() -> Image:
    image = Image(16, 16)
    _fill(image, NIGHT)
    _rect(image, 2, 0, 2, 16, STEEL_LIGHT)
    _rect(image, 12, 0, 2, 16, STEEL_LIGHT)
    _rect(image, 2, 7, 12, 2, HAT)
    return image


def _moonpool_tile() -> Image:
    image = Image(16, 16)
    _fill(image, BOOT)
    _rect(image, 3, 3, 10, 10, SEA_DARK)
    _rect(image, 5, 6, 6, 2, SEA_LIGHT)
    return image


def _mess_tile() -> Image:
    image = Image(16, 16)
    _fill(image, BOOT)
    _rect(image, 2, 2, 12, 6, WINDOW)
    _rect(image, 3, 3, 4, 4, NIGHT)
    _rect(image, 9, 3, 4, 4, WHITE)
    _rect(image, 2, 12, 12, 2, STEEL)
    return image


def _helideck_tile() -> Image:
    image = Image(16, 16)
    _fill(image, STEEL)
    _rect(image, 4, 4, 8, 8, HAT)
    _rect(image, 7, 5, 2, 6, BOOT)
    return image


def _cable_icon() -> Image:
    image = Image(16, 16)
    _rect(image, 2, 7, 5, 2, HAT)
    _rect(image, 9, 7, 5, 2, HAT)
    image.set(7, 6, WINDOW)
    image.set(8, 9, RED)
    return _outline(image)


def _muster_icon() -> Image:
    image = Image(16, 16)
    _rect(image, 5, 2, 6, 5, HAT)
    _rect(image, 4, 7, 8, 2, STEEL_LIGHT)
    _rect(image, 7, 9, 2, 4, RED)
    return _outline(image)


def _cake_icon() -> Image:
    image = Image(16, 16)
    _rect(image, 3, 8, 10, 5, COVERALL)
    _rect(image, 3, 6, 10, 2, WHITE)
    image.set(8, 4, RED)
    return _outline(image)


def _rounds_icon() -> Image:
    image = Image(16, 16)
    for x in (2, 7, 12):
        _rect(image, x, 6, 3, 6, SEA_LIGHT)
        _rect(image, x, 5, 3, 2, WHITE)
    return _outline(image)


def _star_icon() -> Image:
    image = Image(16, 16)
    _rect(image, 7, 2, 2, 12, HAT)
    _rect(image, 2, 7, 12, 2, HAT)
    return _outline(image)


def _cross_icon() -> Image:
    image = Image(16, 16)
    for offset in range(4, 12):
        image.set(offset, offset, RED)
        image.set(15 - offset, offset, RED)
    return _outline(image)


def _write_png(path: Path, image: Image) -> None:
    raw = bytearray()
    for y in range(image.height):
        raw.append(0)
        for x in range(image.width):
            raw.extend(image.get(x, y))
    ihdr = struct.pack(">IIBBBBB", image.width, image.height, 8, 6, 0, 0, 0)
    payload = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
    payload += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    payload += _chunk(b"IEND", b"")
    path.write_bytes(payload)


def _chunk(tag: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", checksum)


_BODY = (
    "................",
    "................",
    ".....YYYYY......",
    "....YYYYYYY.....",
    "....YYY.YYY.....",
    ".....YYYYY......",
    "......SSSS......",
    ".....SSSSSS.....",
    ".....S.SS.S.....",
    "......SSSS......",
    ".....OOOOOO.....",
    "....OOOOOOOO....",
    "....OOOOOOOO....",
    "....OOO..OOO....",
    ".....OOOOOO.....",
    ".....OOOOOO.....",
)
_STRIDE_A = (
    "....OO....OOO...",
    "...OO......OO...",
    "...OO.......OO..",
    "...BB.......BB..",
    "...BB.......BB..",
    "................",
    "................",
    "................",
)
_STRIDE_B = (
    "...OOO....OO....",
    "...OO......OO...",
    "..OO.......OO...",
    "..BB.......BB...",
    "..BB.......BB...",
    "................",
    "................",
    "................",
)
_TOGETHER = (
    ".....OO..OO.....",
    ".....OO..OO.....",
    ".....OO..OO.....",
    ".....BB..BB.....",
    ".....BB..BB.....",
    "................",
    "................",
    "................",
)


def _mugshot() -> Image:
    image = Image(32, 32)
    _rect(image, 8, 3, 16, 4, HAT)
    _rect(image, 6, 6, 20, 3, HAT)
    _rect(image, 4, 9, 24, 2, HAT)
    _rect(image, 10, 11, 12, 9, SKIN)
    image.set(13, 14, OUTLINE)
    image.set(18, 14, OUTLINE)
    _rect(image, 6, 21, 20, 4, COVERALL)
    _rect(image, 3, 25, 26, 6, COVERALL)
    return _outline(image)

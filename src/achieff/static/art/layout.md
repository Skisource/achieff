# Art kit layout

Pixel art on a 16px grid. The browser shows it at an integer scale with `image-rendering: pixelated`.

The walk, idle, and mugshot sheets use one body. Runtime recolor swaps only these source colors:

- Coverall `#e07a3d` (224, 122, 61)
- Hard hat `#f2c14e` (242, 193, 78)

`variants.json` lists the eight pairs, in the same order as `SPRITE_KIT_SIZE`.

## Palette

- Night sky and outline `#121826`
- Sea `#1a3a4a` `#2e6b7a` `#7ec8c3`
- Hull and concrete `#2c333c` `#5c6770` `#c5ced6`
- Caution yellow `#f2c14e`
- Coveralls `#e07a3d` `#3d6ea8` `#3aa76d` `#c23b4a`
- Window light `#f6d58a`
- Generic skin `#f2c7a5`
- White `#f2f2f2`

## Walk `walk.png`

16×24 frames. Sheet is 4 columns by 2 rows (64×48).

| Frame | Pose |
| --- | --- |
| 0 | Right, stride A |
| 1 | Right, feet together, bobbed up 1px |
| 2 | Right, stride B |
| 3 | Right, feet together, bobbed up 1px |
| 4–7 | The same four poses, mirrored left |

## Idle `idle.png`

16×24 frames. Sheet is 2 columns by 2 rows (32×48).

| Frame | Pose |
| --- | --- |
| 0 | Right, standing |
| 1 | Right, bobbed up 1px |
| 2 | Left, standing |
| 3 | Left, bobbed up 1px |

## Mugshot `mugshot.png`

One 32×32 frame. Head, hard hat, and shoulders.

## Ship `ship.png`

Seven 16×16 tiles in one row (112×16), left to right:

sea, hull, deck, derrick, moonpool, mess, helideck.

## Badges `badges.png`

Six 16×16 icons in one row (96×16), left to right:

drilled-through-cable, brought-rig-to-muster, baked-the-best-cake, bought-5-rounds, goody, baddy.

## Preview

`/dev/art` steps through frames and paints the eight recolors. It answers 404 when `ACHIEFF_ENV=production`.

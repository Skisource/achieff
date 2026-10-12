# Achieff change log

Living plan and change record for the crew achievement board. Newest entries go at the top. Phase 5 art kit is in place. The drillship scene has not started.

## Unreleased

### 2026-10-12 — Phase 5 art kit

Pixel sheets on the 16px grid, drawn by `scripts/build_art.py` so every frame shares one outline and one recolor pair. Layout is in `static/art/layout.md`.

- Walk is 16×24, four poses, right then mirrored left. Idle is standing and a 1px bob, both directions. Mugshot is 32×32.
- Ship tiles, left to right: sea, hull, deck, derrick, moonpool, mess, helideck. Badge icons follow the four seeded titles, then a generic goody and a generic baddy.
- Coverall `#e07a3d` and hard hat `#f2c14e` are the only colors the eight variants replace. The pairs live in `variants.json`.
- `/dev/art` steps through frames at 4×. It answers 404 when `ACHIEFF_ENV=production`.

### 2026-10-12 — Phase 4 crew login

Crew can sign in with the same alias and key as an admin. The boards stay readable without a session.

- A crew key lands on the leaderboard. The navbar shows "Signed in as {alias}" and a log out button. An admin key still opens `/admin`. A crew key gets 403 there.
- A wrong key and an unknown alias share the message "Alias or key is wrong."
- Eight failures from the same address within 15 minutes lock the login route. Later attempts get "Too many attempts. Try again shortly." A successful login clears that address.

### 2026-10-12 — Phase 3 admin and keys

Admin can sign in with an alias and a hex key, then run the roster from `/admin`. The public boards stay open.

- If the database has no admin, `ACHIEFF_BOOTSTRAP_ALIAS` creates one and prints the key once in the process log. The key is stored only as an argon2 hash.
- Adding or reissuing a key shows the new key once on the admin page. The old key stops working at reissue.
- Admin can add an alias, set active or retired, delete an alias, add and rename badges, close a badge to new pins, and pin or unpin awards. Forms carry a CSRF token. A crew session gets 403 on `/admin`.
- Deleting an alias removes it from queries. The signed-in admin and the last admin cannot be deleted.
- Login rate limiting is in Phase 4.

### 2026-10-12 — Phase 2 domain

SQLite on the data volume, seeded badges, and career scoring. The four pages are unchanged.

- Startup migrates `achieff.sqlite3` and seeds Drilled through cable, Brought rig to muster, Baked the best cake, and Bought 5 rounds.
- Crew status is `active` or `retired`, default `active`. Deleting an alias cascades awards and sessions. An alias cannot contain `@`.
- Score is merit minus infamy. Ties break by earlier first award, then alias. A row with no awards sorts after a row that has one when the net is equal.
- A test rejects forbidden column stems (`email`, `name`, `phone`, `dob`, `photo`) on the live schema.

### 2026-10-12 — Retired replaces At home

The board is a fantasy drillship for the industry, not a live personnel-on-board tracker. Hitch and leave are too noisy to follow. The ship shows aliases still in the job. People who have left the workforce leave the ship and keep their badges on a Retired honor roll.

- Nav route `/home` is gone. `/retired` is the honor roll. The shell empty states match that.
- Crew status is `active` or `retired`. Default is `active`. There is no `home` placement and no skyscraper.
- The leaderboard stays one career list, active and retired together. A retired row is marked. The ship shows active aliases only.
- Badge "retire" still means a badge is closed to new pins. That is separate from a person leaving the job.

### 2026-10-10 — Phase 1 skeleton

Bulma shell with four empty pages on the existing container. Tooling, health, Docker, and the `/data` volume were already in place.

- Vendored Bulma 1.0.4 (`static/css/bulma.min.css`, MIT) so the ship UI does not depend on a CDN.
- `/`, `/home`, `/leaderboard`, and `/admin` share a dark navbar and an empty-state message. The navbar burger is vanilla JavaScript.
- Admin is a placeholder and is not gated. Sign-in and rejection of non-admins stay in Phases 3 and 4.
- `GET /health` is unchanged.

### 2026-10-10 — Git and container environment

Repository ignore rules, a Python 3.14.8 virtualenv, and a single runtime container. No boards, admin, or login yet.

- `.gitignore` keeps the virtualenv, local data, and `.env` out of git. There is still no remote.
- Runtime deps are `quart` and `hypercorn`, locked in `requirements.txt`. Dev deps (`pytest`, `pytest-asyncio`, `ruff`) are locked in `requirements-development.txt`. `pyproject.toml` lists the same top-level names.
- `GET /health` returns `{"status": "ok"}` and ensures `ACHIEFF_DATA_DIR` exists (default `data/` locally, `/data` in the container).
- `compose.yaml` builds `achieff:local`, publishes host port 10000 to container port 8080, and mounts a named volume at `/data`. The process drops to uid 10001 after fixing that directory's owner.
- Local check: `./.venv/bin/pytest`. Container check: `docker compose up --build` then `curl http://127.0.0.1:10000/health`.
- Verified: pytest passed, the container is healthy, Hypercorn runs as uid 10001, and `/data` is writable by that user.

### 2026-10-10 — Product plan

Greenfield plan for a single Docker container that shows a drillship crew as pixel-art figures, hands out good and nasty achievement badges, and ranks them on one leaderboard. Identity is an alias plus a hex key. No email, no real names, no photographs.

---

## 1. What we are building

Achieff is a fantasy drillship for the whole industry. Crew appear only as nicknames and generated pixel-art mugshots. Admins pin badges on them for folklore highs and lows. The ship is the roster of legends still in the job. Three public boards tell the story; admin is a fourth, gated surface.

| View | Who is on it | What it looks like |
| --- | --- | --- |
| Onboard | Aliases still in the job | Cutaway drillship, Terraria-style, figures walking the decks like an ant farm |
| Retired | Aliases who have left the workforce | Honor roll: mugshot, alias, and the badges they earned. No second animated scene |
| Leaderboard | Everyone with at least one badge, active and retired | One ranked list: rank, mugshot, alias, merit, infamy, badge icons, retired mark |
| Admin | Admins only | Crew, keys, badges, awards, active/retired status |

The boards are the product. Login exists so a later event layer can say "this alias did this" without collecting a mailbox. Account management beyond key issue and rotation waits until the boards are real.

Example badges, seeded so the tone is obvious:

- Nasty: Drilled through cable. Brought rig to muster.
- Good: Baked the best cake. Bought 5 rounds.

Badges are short titles plus a 16×16 icon. They are mess-room folklore, not an incident file. The schema has no field for a real name, employer id, cabin number tied to a person, or free-text incident report.

## 2. Decisions locked for v1

These are the defaults the phases below build on.

**Stack.** Python 3.14, Quart (async, Jinja templates), Bulma, vanilla JavaScript, SQLite on a Docker volume. One process, one container. `uv` for dependencies. `pytest` and `ruff` from the first commit that contains code. Dev server binds to port 10000 or higher. The container listens on 8080.

**Art.** Side-view 2D pixel art on a 16px grid, nearest-neighbor scaled 3× in the browser (`image-rendering: pixelated`). Terraria is the reference: chunky outlines, small palette, readable at a glance across a mess-room TV. Characters are generic rig workers (hard hat, coveralls, boots), varied by palette. They are not likenesses of real people.

**Who can see what.** The three boards are readable without login, so a bridge or rec-room screen can show them. Mutations go through admin. Crew login is alias + hex key and, in v1, only proves who is at the keyboard. It does not unlock a social profile.

**Scoring.** Each goody badge adds 1 merit. Each baddy badge adds 1 infamy. Net = merit − infamy. The leaderboard sorts by net descending, so the reigning good boy sits at the top and the reigning nasty sits at the bottom. Two callouts above the table name those two. Ties break by earlier first award, then alias. Badge weights can wait.

**Keys.** 128-bit random, shown once as 32 hex characters grouped in fours (`a1b2-c3d4-…`). Stored as an argon2 hash. Login compares alias + key. Loss of a key is an admin reissue, because there is no email to reset against. The plaintext key is never written to the database or to git.

**Crew list.** There is no HR import. An admin types aliases. The git repo never contains a real roster.

**Status.** Each crew row is `active` or `retired`. New aliases start `active` and walk the ship. `retired` takes them off the ship and onto the honor roll. Career badges stay. The app does not track hitch, leave, or which real vessel someone is on.

## 3. GDPR posture

An alias the crew already knows is still personal data once it is tied to behaviour. The app minimizes that data and keeps it on the ship. It does not claim to take the operator outside GDPR.

Stored per person:

- Alias (unique, case-insensitive)
- Argon2 hash of the hex key
- Role (`crew` or `admin`)
- Status (`active` or `retired`)
- Sprite variant (an integer into a shared art kit, not a photo)
- Awards: badge id, timestamp, awarding admin id

Explicitly absent from the schema and from every form: legal name, email, phone, date of birth, nationality, passport or seamans-book number, photograph, biometric, medical note, free-text incident narrative.

Operational rules the app enforces:

- Delete crew cascades their awards and sessions. That is the erasure path.
- Keys are shown once in the admin UI and in the one-time bootstrap log line. Reissue replaces the hash; the old key dies immediately.
- SQLite lives on a volume on the ship, not in the image.
- A test fails the build if a migration or model introduces a forbidden column name (`email`, `name`, `phone`, `dob`, `photo`, and the same stems).

Lawful basis, retention period, and who is controller stay with the company. The app ships a delete button and a data dictionary so that conversation is short.

## 4. Domain model

```
crew
  id, alias, alias_normalized, key_hash, role, status,
  sprite_variant, created_at

badge
  id, slug, title, polarity (goody|baddy), sort_order, created_at

award
  id, crew_id, badge_id, awarded_by, awarded_at
  unique (crew_id, badge_id) in v1 — one pin per badge per alias

session
  id, crew_id, token_hash, expires_at
```

Sprite variant is `hash(alias) mod kit_size` at creation, overridable by admin when two people would read as the same hard-hat color.

Sessions are random tokens, hashed at rest, cookie `HttpOnly`, `SameSite=Lax`, `Secure` when the request is HTTPS. Shipboard HTTP on a closed network still works; the compose file documents putting TLS in front if the screen is not the only client.

## 5. Pages

**Onboard.** A static tile map of a drillship cutaway: sea, hull, engine room, moonpool, drill floor, derrick, accommodation (mess, gym, cabins), helideck. Walkable floors are a waypoint graph. Each active alias is a sprite that idles, then walks a short random route, then idles again. No pathfinding library: the map author lists the edges. Hover or tap shows alias and badge counts. The board polls status every 15 seconds so a retirement shows up without a deploy. Retired aliases do not appear.

**Retired.** An honor roll of aliases with status `retired`: mugshot, alias, and badge icons. Sorted by alias. No walk cycle and no skyscraper. Active aliases do not appear.

**Leaderboard.** Callout pair (good boy, nasty), then one table of active and retired aliases together. Columns: rank, mugshot, alias, net, merit, infamy, badge icons, and a retired mark when status is `retired`. A retired alias can still hold a callout; the score is a career score. Goody icons and baddy icons are visually distinct (gold rim vs red rim) so the row reads without opening a legend. Empty state explains that badges are awarded from admin.

**Login.** Two fields, alias and key. Generic failure text. Rate limit on the route. Successful login lands on the leaderboard with a small "signed in as {alias}" chip. Logout clears the session.

**Admin.**

- Crew: add alias, set status (`active` or `retired`), reissue key (modal shows the new key once), delete crew.
- Badges: add, edit title, set polarity, retire (hidden from new awards, kept on old rows).
- Awards: pick alias, pick badge, pin or unpin.
- First boot: if the database has no admin, read `ACHIEFF_BOOTSTRAP_ALIAS` and generate a key, print it once to stdout, store the hash. If the env var is missing, the process refuses to serve admin and the boards render empty.

## 6. Art kit

Generated in-repo as PNG, committed, style-matched to one palette. Procedural recolor at runtime does the rest, so we do not generate a unique portrait per real person.

Palette:

- Sea `#1a3a4a` `#2e6b7a` `#7ec8c3`
- Hull and concrete `#2c333c` `#5c6770` `#c5ced6`
- Caution yellow `#f2c14e`
- Coveralls `#e07a3d` `#3d6ea8` `#3aa76d` `#c23b4a`
- Window light `#f6d58a`
- Night sky `#121826`

Sheets:

| Asset | Size | Notes |
| --- | --- | --- |
| Character walk | 16×24, 4 frames, left and right | One base body. Coverall and hard-hat colors swapped per variant |
| Character idle | 16×24, 2 frames | Used when a walking route finishes |
| Mugshot | 32×32 | Head and shoulders, same variant colors, used on the leaderboard and the retired roll |
| Ship tiles | 16×16 | Hull, deck, derrick, moonpool, mess, helideck, sea |
| Badge icons | 16×16 | One per seeded badge, plus a generic goody and generic baddy for admin-created badges |

Maps are JSON: tile layers plus a waypoint graph. The renderer is a single canvas (or a stack of canvases: tiles, then sprites) driven by `requestAnimationFrame`. Integer scale only, so pixels stay square.

Art is produced in the art phase with the image generator, then adjusted so every sheet shares the same grid and outline weight. If a generated sheet is off-grid, it gets redrawn before any page uses it.

## 7. Repository shape

```
change_log.md
pyproject.toml
requirements.piptools
requirements-development.piptools
pytest.ini
ruff.toml
Dockerfile
compose.yaml
src/achieff/
  app.py
  db.py
  auth.py
  scoring.py
  crew.py
  badges.py
  gdpr.py
  templates/
  static/css/
  static/js/scene.js
  static/art/
tests/
```

Functions live in modules and are called as `module.function`. Classes are reserved for exceptions and for row types that are genuinely records. Paths use `pathlib`. Optional types use `Optional[...]`.

## 8. Phases

Each phase is shippable on its own. A later phase does not start by rewriting the previous one. Tests cover scoring, key hashing, the forbidden-column check, and the main routes before the phase is called done.

### Phase 0 — This plan

Write this document. No application code.

**Status:** done.

**Done when:** the plan is in `change_log.md` and the scope of v1 is the three boards, admin, and hex-key login.

### Phase 1 — Skeleton

Tooling, Quart app, Bulma shell, nav for Onboard / At home / Leaderboard / Admin, health route, empty states, Dockerfile that builds, compose file with a `/data` volume, dev port ≥ 10000.

**Status:** done. Nav amended 2026-10-12: At home became Retired.

**Done when:** `docker compose up` serves the four empty pages and `/health` returns ok.

### Phase 2 — Domain

SQLite schema, migrations applied on startup, repository functions for crew, badges, awards. Seed the four example badges. GDPR column test. Scoring function with unit tests (net, ties, empty crew). Crew status is `active` or `retired`, default `active`.

**Status:** done.

**Done when:** tests create a crew row, pin a goody and a baddy, and assert net, merit, and infamy without a browser.

### Phase 3 — Admin and keys

Bootstrap admin. Crew add / set status / delete. Key issue and reissue, plaintext shown once. Badge create and retire (close a badge to new pins). Award pin and unpin. CSRF on forms. Admin routes reject a non-admin session.

**Status:** done.

**Done when:** a fresh database can be populated entirely from the admin UI, and a deleted alias disappears from queries.

### Phase 4 — Crew login

Login and logout, session cookie, rate limit, "signed in as" chip. Boards stay public. Wrong key and unknown alias share one error string.

**Status:** done.

**Done when:** a crew key opens a session and an admin key opens admin; a crew key does not.

### Phase 5 — Art kit

Generate the sheets in section 6, commit them under `static/art/`, document the palette and frame layout next to the files. A tiny preview page (admin or `/dev/art`, off in production) flips through frames so a bad sheet is obvious.

**Status:** done.

**Done when:** walk, idle, mugshot, the ship tileset, and the seeded badge icons exist and sit on the 16px grid.

### Phase 6 — Onboard scene

Ship tile map, waypoint graph, sprites for every `active` alias, idle/walk loop, hover card, 15s refresh. Retired aliases do not appear.

**Done when:** marking someone retired in admin removes their sprite after a refresh, and marking them active puts it back.

### Phase 7 — Retired honor roll

A list of retired aliases: mugshot, alias, badges. No tile map.

**Done when:** the retired set and the active set are disjoint, the ship shows only active aliases, and the honor roll shows only retired aliases.

### Phase 8 — Leaderboard

Callouts, ranked table, mugshots, badge icons, empty state. Sorting matches section 2, covered by the Phase 2 tests plus one route test against a seeded database.

**Done when:** the good-boy and nasty callouts match the top and bottom of the table.

### Phase 9 — Ship delivery

Non-root container user, volume for SQLite, documented backup (copy the db file), bootstrap env vars in `compose.yaml`, request size limits, a short runbook at the top of this log's delivery section once the commands are real. `ruff format` and `ruff check` clean. Pytest green inside the image.

**Done when:** a second machine can `docker compose up` and an admin can run the boards from a browser on the ship network.

### Phase 10 — Later, not v1

Held here so the earlier phases leave seams for them.

- **Events.** Admin opens a time-boxed event ("bake-off", "rounds"). Signed-in aliases take part. The award step still goes through admin in the first event version, so a joke cannot write the leaderboard unattended.
- **Account management.** Signed-in crew rotate their own key (old key dies, new key shown once). Award history for "me". Still no email and no extra profile fields.
- **Live boards.** Replace the 15s poll with a websocket when two screens must move together.
- **Where on the ship.** Optional waypoint bias (mess vs drill floor) chosen by admin, still not a real cabin number.
- **Badge weights.** A badge can be worth more than 1 if the mess decides a cable strike outranks buying one round.

## 9. Out of scope for the whole v1 arc

Real names, photos, HR sync, email, password reset, public internet accounts, peer voting that writes badges without admin, mobile native apps, 3D, sound, hitch and leave tracking, a live personnel-on-board board for one vessel, the skyscraper, and anything that turns a badge into a disciplinary record.

## 10. Risks

- **Identifiability.** The crew will know who an alias is. Minimization and on-ship storage are the controls; anonymity is not claimed.
- **Key loss.** No mailbox means a lost key is a walk to an admin. The reissue screen has to be obvious.
- **Art drift.** Mixed scales will break the ant-farm read. Phase 5's preview page is the gate before Phase 6.
- **Performance.** A full crew on one canvas is small (low hundreds of 16×24 sprites). The risk is map complexity, not headcount. Keep the waypoint graph hand-authored.
- **Joke vs record.** Badge titles are permanent-ish. Retire and unpin exist so a badge that stops being funny can leave the board.

## 11. Suggested build order after acceptance

Phase 1 → 2 → 3 → 5 → 6 → 7 → 8 → 4 → 9.

Login (Phase 4) can land any time after Phase 3. Art before the ship scene. Leaderboard after the ship and the retired roll, so the mugshots already exist. Delivery last, once the boards are worth putting on a TV.

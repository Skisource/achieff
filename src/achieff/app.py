import asyncio
from pathlib import Path

from quart import Quart, Response, abort, jsonify, request

from achieff import (
    account,
    admin,
    art,
    auth,
    db,
    events,
    leaderboard,
    live,
    onboard,
    pages,
    retired,
)

MAX_BODY_BYTES = 64 * 1024


def create_app() -> Quart:
    root = Path(__file__).resolve().parent
    app = Quart(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    app.config["SECRET_KEY"] = auth.secret_key()
    app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES
    app.before_request(_reject_large_body)
    asyncio.run(_startup())
    pages.register(app)
    auth.register(app)
    admin.register(app)
    art.register(app)
    onboard.register(app)
    retired.register(app)
    leaderboard.register(app)
    events.register(app)
    account.register(app)
    live.register(app)

    @app.get("/health")
    async def health() -> Response:
        return jsonify(status="ok")

    return app


async def _reject_large_body() -> None:
    if request.content_length is not None and request.content_length > MAX_BODY_BYTES:
        abort(413)


async def _startup() -> None:
    await db.migrate()
    await auth.bootstrap_admin()

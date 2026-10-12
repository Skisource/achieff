import asyncio
from pathlib import Path

from quart import Quart, Response, jsonify

from achieff import admin, art, auth, db, onboard, pages


def create_app() -> Quart:
    root = Path(__file__).resolve().parent
    app = Quart(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    app.config["SECRET_KEY"] = auth.secret_key()
    asyncio.run(_startup())
    pages.register(app)
    auth.register(app)
    admin.register(app)
    art.register(app)
    onboard.register(app)

    @app.get("/health")
    async def health() -> Response:
        return jsonify(status="ok")

    return app


async def _startup() -> None:
    await db.migrate()
    await auth.bootstrap_admin()

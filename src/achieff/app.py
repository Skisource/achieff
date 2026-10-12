import asyncio
from pathlib import Path

from quart import Quart, Response, jsonify

from achieff import db, pages


def create_app() -> Quart:
    root = Path(__file__).resolve().parent
    app = Quart(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    asyncio.run(db.migrate())
    pages.register(app)

    @app.get("/health")
    async def health() -> Response:
        return jsonify(status="ok")

    return app

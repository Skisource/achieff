import os
from pathlib import Path

from quart import Quart, Response, jsonify

from achieff import pages


def data_dir() -> Path:
    raw = os.environ.get("ACHIEFF_DATA_DIR", "data")
    return Path(raw)


def create_app() -> Quart:
    root = Path(__file__).resolve().parent
    app = Quart(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    data_dir().mkdir(parents=True, exist_ok=True)
    pages.register(app)

    @app.get("/health")
    async def health() -> Response:
        return jsonify(status="ok")

    return app

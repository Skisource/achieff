import os
from pathlib import Path

from quart import Quart, Response, jsonify


def data_dir() -> Path:
    raw = os.environ.get("ACHIEFF_DATA_DIR", "data")
    return Path(raw)


def create_app() -> Quart:
    app = Quart(__name__)
    data_dir().mkdir(parents=True, exist_ok=True)

    @app.get("/health")
    async def health() -> Response:
        return jsonify(status="ok")

    return app

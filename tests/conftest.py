from pathlib import Path

import pytest
from pytest import MonkeyPatch
from quart import Quart

from achieff import app as app_module
from achieff import db


@pytest.fixture
def application(monkeypatch: MonkeyPatch, tmp_path: Path) -> Quart:
    monkeypatch.setenv("ACHIEFF_DATA_DIR", str(tmp_path / "ship-data"))
    monkeypatch.setenv("ACHIEFF_SECRET_KEY", "test-secret-key-value")
    return app_module.create_app()


@pytest.fixture
async def connection(application: Quart):
    opened = await db.connect()
    try:
        yield opened
    finally:
        await opened.close()

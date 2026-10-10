from pathlib import Path

import pytest
from pytest import MonkeyPatch
from quart import Quart

from achieff import app as app_module


@pytest.fixture
def application(monkeypatch: MonkeyPatch, tmp_path: Path) -> Quart:
    monkeypatch.setenv("ACHIEFF_DATA_DIR", str(tmp_path / "ship-data"))
    return app_module.create_app()

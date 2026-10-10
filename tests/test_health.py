from pathlib import Path

from pytest import MonkeyPatch

from achieff import app as app_module


async def test_health(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ACHIEFF_DATA_DIR", str(tmp_path / "ship-data"))
    application = app_module.create_app()
    client = application.test_client()

    response = await client.get("/health")

    assert response.status_code == 200
    assert await response.get_json() == {"status": "ok"}
    assert (tmp_path / "ship-data").is_dir()

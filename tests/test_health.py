from pathlib import Path

from quart import Quart


async def test_health(application: Quart, tmp_path: Path) -> None:
    client = application.test_client()

    response = await client.get("/health")

    assert response.status_code == 200
    assert await response.get_json() == {"status": "ok"}
    assert (tmp_path / "ship-data").is_dir()

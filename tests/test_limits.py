from quart import Quart

from achieff.app import MAX_BODY_BYTES


async def test_oversized_body_is_rejected(application: Quart) -> None:
    client = application.test_client()

    body = b"a" * (MAX_BODY_BYTES + 1)
    response = await client.post(
        "/login",
        data=body,
        headers={
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(body)),
        },
    )

    assert response.status_code == 413

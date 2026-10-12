import asyncio

from quart import Quart, websocket

_subscribers: set[asyncio.Queue[str]] = set()


def register(app: Quart) -> None:
    @app.websocket("/live")
    async def live() -> None:
        await websocket.accept()
        queue: asyncio.Queue[str] = asyncio.Queue()
        _subscribers.add(queue)
        try:
            while True:
                await websocket.send(await queue.get())
        finally:
            _subscribers.discard(queue)


def publish() -> None:
    for queue in list(_subscribers):
        queue.put_nowait("refresh")

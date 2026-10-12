import time
from typing import Optional

MAX_FAILURES = 8
WINDOW_SECONDS = 15 * 60

_failures: dict[str, list[float]] = {}


def too_many(client: str, *, now: Optional[float] = None) -> bool:
    moment = time.monotonic() if now is None else now
    return len(_recent(client, moment)) >= MAX_FAILURES


def record_failure(client: str, *, now: Optional[float] = None) -> None:
    moment = time.monotonic() if now is None else now
    recent = _recent(client, moment)
    recent.append(moment)
    _failures[client] = recent


def clear(client: str) -> None:
    _failures.pop(client, None)


def reset() -> None:
    _failures.clear()


def _recent(client: str, now: float) -> list[float]:
    return [
        stamp for stamp in _failures.get(client, []) if now - stamp < WINDOW_SECONDS
    ]

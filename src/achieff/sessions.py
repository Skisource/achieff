import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from aiosqlite import Connection

SESSION_HOURS = 12


def make_csrf(secret: str) -> str:
    nonce = secrets.token_urlsafe(32)
    mac = _mac(secret, nonce)
    return f"{nonce}.{mac}"


def csrf_ok(secret: str, cookie_value: str, form_value: str) -> bool:
    if not cookie_value or not form_value:
        return False
    if not hmac.compare_digest(cookie_value, form_value):
        return False
    nonce, separator, mac = cookie_value.partition(".")
    if separator != "." or not nonce or not mac:
        return False
    return hmac.compare_digest(_mac(secret, nonce), mac)


async def start(connection: Connection, crew_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(hours=SESSION_HOURS)
    await connection.execute(
        """
        INSERT INTO session (crew_id, token_hash, expires_at)
        VALUES (?, ?, ?)
        """,
        (crew_id, _hash_token(token), expires.isoformat()),
    )
    await connection.commit()
    return token


async def viewer(connection: Connection, token: str):
    if not token:
        return None
    now = datetime.now(UTC).isoformat()
    async with connection.execute(
        """
        SELECT crew.id, crew.alias, crew.role, crew.status
        FROM session
        JOIN crew ON crew.id = session.crew_id
        WHERE session.token_hash = ? AND session.expires_at > ?
        """,
        (_hash_token(token), now),
    ) as cursor:
        return await cursor.fetchone()


async def end(connection: Connection, token: str) -> None:
    if not token:
        return
    await connection.execute(
        "DELETE FROM session WHERE token_hash = ?",
        (_hash_token(token),),
    )
    await connection.commit()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _mac(secret: str, nonce: str) -> str:
    return hmac.new(secret.encode(), nonce.encode(), "sha256").hexdigest()

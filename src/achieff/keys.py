import re
import secrets
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_HASHER = PasswordHasher()
_issued: dict[int, tuple[str, str]] = {}


def generate_key() -> str:
    raw = secrets.token_hex(16)
    return "-".join(raw[index : index + 4] for index in range(0, len(raw), 4))


def normalize_key(key: str) -> str:
    return re.sub(r"[\s-]", "", key).casefold()


def hash_key(key: str) -> str:
    return _HASHER.hash(normalize_key(key))


def verify_key(stored: Optional[str], key: str) -> bool:
    if not stored:
        return False
    try:
        return _HASHER.verify(stored, normalize_key(key))
    except VerifyMismatchError, VerificationError, InvalidHashError:
        return False


def hold_issued(admin_id: int, alias: str, key: str) -> None:
    _issued[admin_id] = (alias, key)


def take_issued(admin_id: int) -> Optional[tuple[str, str]]:
    return _issued.pop(admin_id, None)

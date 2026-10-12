class ForbiddenColumnError(RuntimeError):
    pass


FORBIDDEN_STEMS = ("dob", "email", "name", "phone", "photo")


def column_is_forbidden(column: str) -> bool:
    tokens = _tokens(column)
    for stem in FORBIDDEN_STEMS:
        for token in tokens:
            if token == stem or token.startswith(stem):
                return True
    return False


def forbidden_columns(columns: list[str]) -> list[str]:
    return [column for column in columns if column_is_forbidden(column)]


def _tokens(column: str) -> list[str]:
    cleaned = "".join(char if char.isalnum() else " " for char in column.casefold())
    return [token for token in cleaned.split() if token]

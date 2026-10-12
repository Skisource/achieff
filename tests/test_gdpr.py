from aiosqlite import Connection

from achieff.gdpr import column_is_forbidden


def test_forbidden_stems_match_personal_columns() -> None:
    assert column_is_forbidden("email")
    assert column_is_forbidden("email_address")
    assert column_is_forbidden("real_name")
    assert column_is_forbidden("phone")
    assert column_is_forbidden("dob")
    assert column_is_forbidden("photo_path")
    assert not column_is_forbidden("alias")
    assert not column_is_forbidden("alias_normalized")
    assert not column_is_forbidden("status")


async def test_live_schema_has_no_forbidden_columns(connection: Connection) -> None:
    from achieff import db

    await db.assert_schema_is_allowed(connection)

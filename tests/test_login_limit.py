from pytest import MonkeyPatch

from achieff import login_limit


def test_failures_age_out(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(login_limit, "MAX_FAILURES", 2)
    login_limit.record_failure("client", now=0)
    login_limit.record_failure("client", now=1)

    assert login_limit.too_many("client", now=1)
    assert not login_limit.too_many("client", now=1 + login_limit.WINDOW_SECONDS)


def test_clear_forgets_failures(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(login_limit, "MAX_FAILURES", 1)
    login_limit.record_failure("client", now=0)
    login_limit.clear("client")

    assert not login_limit.too_many("client", now=0)

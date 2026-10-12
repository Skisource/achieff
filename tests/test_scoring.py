from achieff.scoring import Standing, net, rank


def test_net_of_an_empty_record_is_zero() -> None:
    assert net(0, 0) == 0


def test_net_subtracts_infamy_from_merit() -> None:
    assert net(2, 1) == 1
    assert net(0, 3) == -3


def test_rank_of_no_one_is_empty() -> None:
    assert rank([]) == []


def test_rank_breaks_ties_by_earlier_award_then_alias() -> None:
    later = Standing(
        alias="Zed",
        merit=1,
        infamy=1,
        net=0,
        first_award_at="2026-02-01T00:00:00+00:00",
    )
    earlier = Standing(
        alias="Bea",
        merit=0,
        infamy=0,
        net=0,
        first_award_at="2026-01-01T00:00:00+00:00",
    )
    same_time = Standing(
        alias="Ann",
        merit=2,
        infamy=2,
        net=0,
        first_award_at="2026-01-01T00:00:00+00:00",
    )
    undated_z = Standing(alias="Zoe", merit=0, infamy=0, net=0, first_award_at=None)
    undated_a = Standing(alias="Ada", merit=0, infamy=0, net=0, first_award_at=None)

    ranked = rank([later, undated_z, earlier, same_time, undated_a])

    assert [item.alias for item in ranked] == ["Ann", "Bea", "Zed", "Ada", "Zoe"]


def test_rank_puts_higher_net_first() -> None:
    nasty = Standing(
        alias="Cable",
        merit=0,
        infamy=2,
        net=-2,
        first_award_at="2026-01-01T00:00:00+00:00",
    )
    good = Standing(
        alias="Cake",
        merit=2,
        infamy=0,
        net=2,
        first_award_at="2026-06-01T00:00:00+00:00",
    )

    assert [item.alias for item in rank([nasty, good])] == ["Cake", "Cable"]

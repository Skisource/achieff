from dataclasses import dataclass

from quart import Quart, render_template


@dataclass(frozen=True)
class Page:
    key: str
    label: str
    path: str
    empty_title: str
    empty_body: str


PAGES = (
    Page(
        key="onboard",
        label="Onboard",
        path="/",
        empty_title="Nobody is on the drillship board yet.",
        empty_body="Personnel marked onboard will walk the cutaway here.",
    ),
    Page(
        key="home",
        label="At home",
        path="/home",
        empty_title="Nobody is in the tower yet.",
        empty_body="Personnel marked at home will show up in the skyscraper here.",
    ),
    Page(
        key="leaderboard",
        label="Leaderboard",
        path="/leaderboard",
        empty_title="No badges awarded yet.",
        empty_body="Rank, alias, and badge icons will appear in one list.",
    ),
    Page(
        key="admin",
        label="Admin",
        path="/admin",
        empty_title="Nothing to manage yet.",
        empty_body=(
            "Crew, keys, badges, and placement will be edited here. "
            "This page stays open until sign-in lands."
        ),
    ),
)


def register(app: Quart) -> None:
    for page in PAGES:
        _bind(app, page)


def _bind(app: Quart, page: Page) -> None:
    async def view(current: Page = page) -> str:
        return await render_template("page.html", page=current, pages=PAGES)

    view.__name__ = page.key
    app.add_url_rule(page.path, endpoint=page.key, view_func=view)

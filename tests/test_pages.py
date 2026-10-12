import pytest
from quart import Quart

from achieff import pages as pages_module


@pytest.mark.parametrize("page", pages_module.PAGES, ids=lambda page: page.key)
async def test_empty_page(application: Quart, page: pages_module.Page) -> None:
    client = application.test_client()

    response = await client.get(page.path)

    assert response.status_code == 200
    body = await response.get_data(as_text=True)
    assert f"<title>{page.label} · Achieff</title>" in body
    assert page.empty_title in body
    assert f'href="{page.path}"' in body
    assert 'aria-current="page"' in body
    assert "navbar-burger" in body


async def test_at_home_route_is_gone(application: Quart) -> None:
    client = application.test_client()

    response = await client.get("/home")

    assert response.status_code == 404


async def test_bulma_is_vendored(application: Quart) -> None:
    client = application.test_client()

    response = await client.get("/static/css/bulma.min.css")

    assert response.status_code == 200
    body = await response.get_data(as_text=True)
    assert "bulma.io v1.0.4" in body

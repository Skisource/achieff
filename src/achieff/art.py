from quart import Quart, abort, render_template

from achieff import artkit


def register(app: Quart) -> None:
    @app.get("/dev/art")
    async def art_preview() -> str:
        if not artkit.preview_enabled():
            abort(404)
        return await render_template("art_preview.html", page=None)

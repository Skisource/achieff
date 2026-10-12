import os
import secrets

from quart import Quart, Response, g, redirect, render_template, request, url_for

from achieff import artkit, crew, db, keys, login_limit, pages, sessions

SESSION_COOKIE = "achieff_session"
CSRF_COOKIE = "achieff_csrf"
LOGIN_ERROR = "Alias or key is wrong."
RATE_LIMIT_ERROR = "Too many attempts. Try again shortly."
_SECRET_MIN_LENGTH = 16


def register(app: Quart) -> None:
    app.before_request(_prepare_request)
    app.after_request(_persist_csrf)
    app.context_processor(_template_context)

    @app.get("/login")
    async def login():
        if _is_admin():
            return redirect(url_for("admin"))
        return await render_template("login.html", page=None, error="")

    @app.post("/login")
    async def login_submit():
        form = await request.form
        if not csrf_matches(str(form.get("csrf", ""))):
            return await render_template(
                "login.html", page=None, error=LOGIN_ERROR
            ), 400

        client = request.remote_addr or "unknown"
        if login_limit.too_many(client):
            body = await render_template(
                "login.html", page=None, error=RATE_LIMIT_ERROR
            )
            return body, 429

        connection = await db.connect()
        try:
            row = await _matching_crew(
                connection,
                str(form.get("alias", "")),
                str(form.get("key", "")),
            )
            if row is None:
                login_limit.record_failure(client)
                body = await render_template("login.html", page=None, error=LOGIN_ERROR)
                return body, 401
            token = await sessions.start(connection, int(row["id"]))
        finally:
            await connection.close()

        login_limit.clear(client)

        destination = "admin" if row["role"] == "admin" else "leaderboard"
        response = redirect(url_for(destination), 303)
        _set_session_cookie(response, token)
        return response

    @app.post("/logout")
    async def logout():
        form = await request.form
        if not csrf_matches(str(form.get("csrf", ""))):
            return await render_template(
                "login.html", page=None, error=LOGIN_ERROR
            ), 400
        connection = await db.connect()
        try:
            await sessions.end(connection, request.cookies.get(SESSION_COOKIE, ""))
        finally:
            await connection.close()
        response = redirect(url_for("login"), 303)
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response


def secret_key() -> str:
    raw = os.environ.get("ACHIEFF_SECRET_KEY", "").strip()
    if len(raw) >= _SECRET_MIN_LENGTH:
        return raw
    print(
        "Achieff ACHIEFF_SECRET_KEY is unset; using a process-only secret.", flush=True
    )
    return secrets.token_hex(32)


async def bootstrap_admin() -> None:
    connection = await db.connect()
    try:
        if await crew.any_admin(connection):
            return
        raw = os.environ.get("ACHIEFF_BOOTSTRAP_ALIAS", "")
        if not raw.strip():
            return
        try:
            display = crew.normalize_alias(raw)
        except crew.CrewAliasError:
            print("Achieff bootstrap alias was rejected.", flush=True)
            return
        if await crew.find_by_alias(connection, display) is not None:
            print(
                "Achieff bootstrap alias already exists and is not an admin.",
                flush=True,
            )
            return
        key = keys.generate_key()
        await crew.add(
            connection,
            display,
            role="admin",
            key_hash=keys.hash_key(key),
        )
        print(f"Achieff bootstrap admin alias={display} key={key}", flush=True)
    finally:
        await connection.close()


def _template_context() -> dict:
    return {
        "viewer": getattr(g, "viewer", None),
        "csrf": getattr(g, "csrf", ""),
        "pages": pages.PAGES,
        "art_preview": artkit.preview_enabled(),
    }


async def _prepare_request() -> None:
    if request.path.startswith("/static"):
        return
    _prepare_csrf()
    g.viewer = None
    if request.path == "/health":
        return
    token = request.cookies.get(SESSION_COOKIE, "")
    if not token:
        return
    connection = await db.connect()
    try:
        row = await sessions.viewer(connection, token)
    finally:
        await connection.close()
    if row is None:
        return
    g.viewer = {
        "id": int(row["id"]),
        "alias": str(row["alias"]),
        "role": str(row["role"]),
    }


def _prepare_csrf() -> None:
    from quart import current_app

    secret = current_app.config["SECRET_KEY"]
    cookie = request.cookies.get(CSRF_COOKIE, "")
    if cookie and sessions.csrf_ok(secret, cookie, cookie):
        g.csrf = cookie
        g.new_csrf = None
        return
    g.csrf = sessions.make_csrf(secret)
    g.new_csrf = g.csrf


def _persist_csrf(response: Response) -> Response:
    fresh = getattr(g, "new_csrf", None)
    if not fresh:
        return response
    response.set_cookie(
        CSRF_COOKIE,
        fresh,
        httponly=True,
        samesite="Lax",
        secure=request.is_secure,
        path="/",
        max_age=SESSION_HOURS_SECONDS,
    )
    return response


def csrf_matches(form_token: str) -> bool:
    from quart import current_app

    return sessions.csrf_ok(current_app.config["SECRET_KEY"], g.csrf, form_token)


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="Lax",
        secure=request.is_secure,
        path="/",
        max_age=SESSION_HOURS_SECONDS,
    )


def _is_admin() -> bool:
    viewer = getattr(g, "viewer", None)
    return viewer is not None and viewer["role"] == "admin"


async def _matching_crew(connection, alias: str, key: str):
    try:
        row = await crew.find_by_alias(connection, alias)
    except crew.CrewAliasError:
        return None
    if row is None or not keys.verify_key(row["key_hash"], key):
        return None
    return row


SESSION_HOURS_SECONDS = sessions.SESSION_HOURS * 60 * 60

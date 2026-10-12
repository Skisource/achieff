FROM python:3.14.8-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app \
    && mkdir -p /data \
    && chown app:app /data

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    ACHIEFF_DATA_DIR=/data \
    PYTHONPATH=/app/src

RUN uv venv /app/.venv

COPY requirements.txt ./
RUN uv pip install --no-cache -r requirements.txt

COPY src ./src

FROM base AS test

COPY requirements-development.txt pytest.ini ruff.toml ./
COPY tests ./tests
RUN uv pip install --no-cache -r requirements-development.txt \
    && ruff format --check src tests \
    && ruff check src tests \
    && pytest

FROM base AS runtime

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')"

ENTRYPOINT ["/entrypoint.sh"]
CMD ["hypercorn", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "achieff.asgi:app"]

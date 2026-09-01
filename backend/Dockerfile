# copertine-scraper — the daily Directus → Postgres fetch of the front page.
#
# Replaces the mema3 arrangement where systemd ran `uv run python src/sd2.py`
# out of a host checkout. There is no checkout on mema4: the image carries the
# scraper and its scheduler (docker/scrape-loop.sh), and the compose file
# supplies only configuration.

FROM ghcr.io/astral-sh/uv:0.9-python3.13-bookworm-slim AS deps

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Dependencies resolve from the lockfile alone, so this layer is cached until
# the lockfile changes — the source below is a separate, always-cheap layer.
# `--no-dev` drops ruff/mypy/type stubs, which are a CI concern, not a runtime
# one. pyproject.toml sets `[tool.uv] package = false`, so this installs the
# dependencies and never the project itself.
# git is needed at build time: isagog-corpus is a git dependency. It lives in
# the deps stage only — the runtime image copies the built venv, not this layer.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project


FROM python:3.13-slim-bookworm AS runtime

# psycopg2-binary ships its own libpq, so no libpq-dev here. `date -u -d` in
# scrape-loop.sh is GNU date, which is why the runtime is Debian rather than
# Alpine — busybox date cannot parse that form.
#
# ca-certificates is not optional: every Directus call is HTTPS to
# pulse.ilmanifesto.it and requests would fail verification without it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root, and it must own the images volume mount point: the scraper writes
# cover JPEGs there, and a volume that Docker creates on an unowned path comes
# up root-owned.
RUN groupadd --system --gid 1001 copertine \
    && useradd --system --uid 1001 --gid copertine --no-create-home copertine \
    && mkdir -p /images \
    && chown copertine:copertine /images

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    COP_IMAGES_DIR=/images \
    TZ=UTC

COPY --from=deps --chown=copertine:copertine /app/.venv /app/.venv
COPY --chown=copertine:copertine src/ ./src/
COPY --chown=copertine:copertine docker/scrape-loop.sh /usr/local/bin/scrape-loop

RUN chmod +x /usr/local/bin/scrape-loop

USER copertine

# The scheduler is the entrypoint, so `docker exec copertine-scraper python
# src/sd2.py --date 2026-08-11` still works for a manual backfill without
# disturbing the loop.
CMD ["/usr/local/bin/scrape-loop"]

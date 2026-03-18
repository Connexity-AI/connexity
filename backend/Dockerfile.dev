FROM python:3.12.10-alpine3.22

# Install dependencies (tree and bash)
RUN apk update
RUN apk add --no-cache tree bash

ENV PYTHONUNBUFFERED=1

WORKDIR /backend/

# Install uv from Astral
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# Put executables in front of PATH
ENV PATH="/backend/.venv/bin:$PATH"

# Compile bytecode
ENV UV_COMPILE_BYTECODE=1

# uv cache mode
ENV UV_LINK_MODE=copy

# Install project dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

ENV PYTHONPATH=/backend

COPY ./scripts /backend/scripts
COPY ./pyproject.toml ./uv.lock ./alembic.ini /backend/
COPY ./app /backend/app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# Set entrypoint
ENTRYPOINT ["scripts/entrypoint.sh"]

# 8000 uvicorn default port

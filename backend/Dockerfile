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

# Install project dependencies (prod only, --no-dev)
COPY pyproject.toml uv.lock /backend/
RUN uv sync --frozen --no-install-project --no-dev

ENV PYTHONPATH=/backend

COPY ./scripts /backend/scripts
RUN chmod +x /backend/scripts/*.sh
COPY ./alembic.ini /backend/
COPY ./app /backend/app

# Sync the project (prod only, --no-dev)
RUN uv sync --no-dev

# Set entrypoint
ENTRYPOINT ["scripts/entrypoint.sh"]

# 8000 uvicorn default port

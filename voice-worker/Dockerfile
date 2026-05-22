FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ffmpeg \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1

WORKDIR /workspace/

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY backend/pyproject.toml backend/uv.lock backend/alembic.ini /workspace/backend/
COPY backend/app /workspace/backend/app
COPY backend/scripts /workspace/backend/scripts
COPY voice-worker/pyproject.toml voice-worker/README.md /workspace/voice-worker/
COPY voice-worker/voice_runner /workspace/voice-worker/voice_runner

WORKDIR /workspace/voice-worker

# No standalone voice-worker/uv.lock (workspace lock is at repo root); resolve at build.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

ENV PATH="/workspace/voice-worker/.venv/bin:$PATH"
ENV PYTHONPATH=/workspace/backend

EXPOSE 8765

CMD ["uv", "run", "python", "-m", "voice_runner"]

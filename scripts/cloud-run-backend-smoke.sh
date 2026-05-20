#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-connexity-backend-smoke:local}"
POSTGRES_IMAGE="${POSTGRES_IMAGE:-postgres:17-alpine}"
NETWORK_NAME="${NETWORK_NAME:-connexity-smoke-$RANDOM-$RANDOM}"
DB_CONTAINER_NAME="${DB_CONTAINER_NAME:-${NETWORK_NAME}-db}"
APP_CONTAINER_NAME="${APP_CONTAINER_NAME:-${NETWORK_NAME}-app}"
HOST_PORT="${HOST_PORT:-18000}"
CONTAINER_PORT="${CONTAINER_PORT:-8000}"
STARTUP_TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-180}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-2}"
MEMORY_LIMIT="${MEMORY_LIMIT:-512m}"
CPU_LIMIT="${CPU_LIMIT:-1}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-password}"
POSTGRES_DB="${POSTGRES_DB:-app}"
SITE_URL="${SITE_URL:-http://localhost:3000}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
JWT_SECRET_KEY="${JWT_SECRET_KEY:-smoke-test-jwt-secret}"
ENCRYPTION_KEY="${ENCRYPTION_KEY:-ybBvrlNEMQGxNudqVJ_KZ6Vj0vFqBeDq8LkQKpVGXaw=}"
RUN_DB_PRESTART="${RUN_DB_PRESTART:-1}"

cleanup() {
  docker rm -f "$APP_CONTAINER_NAME" >/dev/null 2>&1 || true
  docker rm -f "$DB_CONTAINER_NAME" >/dev/null 2>&1 || true
  docker network rm "$NETWORK_NAME" >/dev/null 2>&1 || true
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

wait_for_postgres() {
  local attempts=0
  local max_attempts=30

  until docker exec "$DB_CONTAINER_NAME" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if (( attempts >= max_attempts )); then
      echo "Postgres did not become ready in time." >&2
      docker logs "$DB_CONTAINER_NAME" || true
      exit 1
    fi
    sleep 1
  done
}

print_container_logs() {
  echo
  echo "Backend container logs:"
  docker logs "$APP_CONTAINER_NAME" || true
  echo
  echo "Postgres container logs:"
  docker logs "$DB_CONTAINER_NAME" || true
}

wait_for_backend() {
  local elapsed=0
  local url="http://127.0.0.1:${HOST_PORT}/"

  while (( elapsed < STARTUP_TIMEOUT_SECONDS )); do
    if curl --silent --show-error --fail "$url" >/dev/null; then
      echo "Backend image passed smoke test at $url"
      return 0
    fi

    if ! docker ps --format '{{.Names}}' | grep -Fxq "$APP_CONTAINER_NAME"; then
      echo "Backend container exited before becoming healthy." >&2
      print_container_logs
      exit 1
    fi

    sleep "$POLL_INTERVAL_SECONDS"
    elapsed=$((elapsed + POLL_INTERVAL_SECONDS))
  done

  echo "Backend image did not become healthy within ${STARTUP_TIMEOUT_SECONDS}s." >&2
  print_container_logs
  exit 1
}

trap cleanup EXIT

require_command docker
require_command curl

echo "Building backend production image..."
docker build -f "$ROOT_DIR/backend/Dockerfile" -t "$IMAGE_TAG" "$ROOT_DIR/backend"

echo "Creating isolated Docker network..."
docker network create "$NETWORK_NAME" >/dev/null

echo "Starting Postgres..."
docker run -d \
  --name "$DB_CONTAINER_NAME" \
  --network "$NETWORK_NAME" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  "$POSTGRES_IMAGE" >/dev/null

wait_for_postgres

echo "Starting backend container with Cloud Run-like limits..."
docker run -d \
  --name "$APP_CONTAINER_NAME" \
  --network "$NETWORK_NAME" \
  --memory "$MEMORY_LIMIT" \
  --cpus "$CPU_LIMIT" \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  -e SITE_URL="$SITE_URL" \
  -e ENVIRONMENT="$ENVIRONMENT" \
  -e JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  -e ENCRYPTION_KEY="$ENCRYPTION_KEY" \
  -e POSTGRES_SERVER="$DB_CONTAINER_NAME" \
  -e POSTGRES_PORT="5432" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -e PORT="$CONTAINER_PORT" \
  -e RUN_DB_PRESTART="$RUN_DB_PRESTART" \
  "$IMAGE_TAG" >/dev/null

wait_for_backend

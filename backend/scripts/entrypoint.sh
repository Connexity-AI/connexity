#!/usr/bin/env bash
set -e

pwd
tree .

# Run migrations and seed
./scripts/prestart.sh

# Start FastAPI server
# Railway injects PORT for public networking; fall back to 8000 locally.
exec fastapi run --workers 4 --host 0.0.0.0 --port "${PORT:-8000}" app.main:app

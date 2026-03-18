#!/usr/bin/env bash
set -e

pwd
tree .

# Run migrations and seed
./scripts/prestart.sh

# Start FastAPI server
# 8000 uvicorn default port
exec fastapi run --workers 1 app/main.py

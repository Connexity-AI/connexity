#!/usr/bin/env bash
set -euo pipefail

# Run DB readiness + migrations unless the platform handles that separately.
if [[ "${RUN_DB_PRESTART:-1}" == "1" ]]; then
  ./scripts/prestart.sh
fi

# Railway and Cloud Run both inject PORT for public networking.
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-4}"

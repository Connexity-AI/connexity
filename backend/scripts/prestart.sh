#!/usr/bin/env bash
set -euxo pipefail

# Let the DB start
python app/backend_pre_start.py

# Run migrations
python -m alembic upgrade head

# Seed FIRST_SUPERUSER (no-op when unset or already present)
python app/initial_data.py

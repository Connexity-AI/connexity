#!/bin/bash

set -e

# Todo: test this and improve
if [[ "$VIRTUAL_ENV" != "$(pwd)/.venv" ]]; then
  source .venv/bin/activate
fi

uvicorn app.main:app --reload

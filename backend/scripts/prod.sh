#!/bin/bash

set -e

# source .venv/bin/activate

fastapi run --workers 4 --host 0.0.0.0 --port 8000 app.main:app

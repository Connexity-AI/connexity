#! /usr/bin/env bash

set -e
set -x

# Must be in root because it calls both backend and frontend

# Navigate to backend
cd backend

# Activate venv, disable logging
set +x
source .venv/bin/activate
set -x

# Generate openapi.json with FastAPI
python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > ../openapi.json

# Deactivate venv, disable logging
set +x
deactivate
set -x

# Navigate to project root
cd ..

# Move to Next.js app root
mv openapi.json frontend/apps/web/

# Navigate to Next.js app
cd frontend/apps/web

# Generate client
pnpm run generate-client

# @hey-api will overwrite by default, no need for manual delete

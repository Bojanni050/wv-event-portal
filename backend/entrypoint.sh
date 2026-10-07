#!/usr/bin/env sh
# Apply database migrations, then start the API.
# Point your deploy platform's start command at this script.
set -e

alembic upgrade head
exec uvicorn server:app --host 0.0.0.0 --port "${PORT:-8000}"

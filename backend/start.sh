#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Running seed data..."
python -m snep.seed

echo "Starting SNEP API..."
exec uvicorn snep.api.app:app --host 0.0.0.0 --port ${PORT:-8000}

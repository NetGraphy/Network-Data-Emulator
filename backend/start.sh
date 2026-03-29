#!/bin/bash
set -e

echo "Waiting for database to be ready..."
for i in $(seq 1 30); do
    python -c "
import asyncio, asyncpg, os
async def check():
    url = os.environ.get('SNEP_DATABASE_URL', '').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(url)
    await conn.close()
asyncio.run(check())
" 2>/dev/null && break
    echo "  Attempt $i/30 - waiting..."
    sleep 2
done

echo "Running database migrations..."
alembic upgrade head

echo "Running seed data..."
python -m snep.seed

echo "Starting SNEP API on port ${PORT:-8000}..."
exec uvicorn snep.api.app:app --host 0.0.0.0 --port ${PORT:-8000}

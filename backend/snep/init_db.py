"""Initialize database — create all tables and run seed."""

import asyncio
import sys

from snep.db import engine
from snep.models import Base


async def init():
    print("Creating database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Tables created successfully.")
    except Exception as e:
        print(f"Warning: Could not create tables: {e}")

    print("Running seed data...")
    try:
        from snep.seed import main as seed_main
        await seed_main()
    except Exception as e:
        print(f"Warning: Seed failed (may already be seeded): {e}")


if __name__ == "__main__":
    asyncio.run(init())

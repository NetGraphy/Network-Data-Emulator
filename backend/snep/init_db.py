"""Initialize database — create all tables and run seed."""

import asyncio
import sys

from snep.db import engine
from snep.models import Base


async def init():
    import os
    reset = os.environ.get("SNEP_RESET_DB", "false").lower() == "true"

    print("Creating database tables...")
    try:
        async with engine.begin() as conn:
            if reset:
                print("SNEP_RESET_DB=true — dropping all tables first...")
                await conn.run_sync(Base.metadata.drop_all)
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

    print("Running CLI library seed...")
    try:
        from snep.seed_cli_library import main as seed_cli_main
        await seed_cli_main()
    except Exception as e:
        print(f"Warning: CLI library seed failed: {e}")

    print("Running scenario seed...")
    try:
        from snep.seed_scenarios import main as seed_scenario_main
        await seed_scenario_main()
    except Exception as e:
        print(f"Warning: Scenario seed failed: {e}")

    print("Running custom filter seed...")
    try:
        from snep.seed_filters import main as seed_filter_main
        await seed_filter_main()
    except Exception as e:
        print(f"Warning: Custom filter seed failed: {e}")


if __name__ == "__main__":
    asyncio.run(init())

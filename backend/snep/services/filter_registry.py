"""Filter registry — loads CustomFilter records from DB and registers on Jinja2 Environment.

Called at startup and on-demand when filters are created/updated/deleted.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snep.models.custom_filter import CustomFilter
from snep.services.filter_sandbox import compile_filter

logger = logging.getLogger(__name__)

# Track registered custom filter names (so we can unregister on reload)
_registered_custom_filters: set[str] = set()


async def load_custom_filters(session: AsyncSession) -> dict:
    """Load all active custom filters from DB and register on the Jinja2 environment.

    Returns: {"loaded": int, "failed": int, "errors": list}
    """
    from snep.services.rendering import _env

    # Unregister previously loaded custom filters
    for name in _registered_custom_filters:
        _env.filters.pop(name, None)
    _registered_custom_filters.clear()

    result = await session.execute(
        select(CustomFilter).where(CustomFilter.is_active == True)
    )
    filters = result.scalars().all()

    loaded = 0
    failed = 0
    errors = []

    for f in filters:
        try:
            fn = compile_filter(f.name, f.code, f.signature)
            _env.filters[f.name] = fn
            _registered_custom_filters.add(f.name)
            loaded += 1
            logger.info(f"Registered custom Jinja2 filter: {f.name}")
        except Exception as e:
            failed += 1
            errors.append({"name": f.name, "error": str(e)})
            logger.error(f"Failed to compile custom filter '{f.name}': {e}")

    logger.info(f"Custom filter registry: {loaded} loaded, {failed} failed")
    return {"loaded": loaded, "failed": failed, "errors": errors}


def get_all_filter_names() -> list[str]:
    """Get all registered Jinja2 filter names (built-in + custom)."""
    from snep.services.rendering import _env
    return sorted(_env.filters.keys())

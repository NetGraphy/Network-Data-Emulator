"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from snep.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load custom Jinja2 filters from DB
    try:
        from snep.db import async_session_factory
        from snep.services.filter_registry import load_custom_filters
        async with async_session_factory() as session:
            result = await load_custom_filters(session)
            print(f"Custom filters loaded: {result['loaded']} active, {result['failed']} failed")
    except Exception as e:
        print(f"Warning: Could not load custom filters: {e}")
    yield
    # Shutdown
    from snep.db import engine
    await engine.dispose()


app = FastAPI(
    title="SNEP - Synthetic Network Emulator Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from snep.api.platforms import router as platforms_router  # noqa: E402
from snep.api.devices import router as devices_router  # noqa: E402
from snep.api.interfaces import router as interfaces_router  # noqa: E402
from snep.api.links import router as links_router  # noqa: E402
from snep.api.cli_mappings import router as cli_mappings_router  # noqa: E402
from snep.api.scenarios import router as scenarios_router  # noqa: E402
from snep.api.topology import router as topology_router  # noqa: E402
from snep.api.export import router as export_router  # noqa: E402
from snep.api.execute import router as execute_router  # noqa: E402
from snep.api.imports import router as imports_router  # noqa: E402
from snep.api.cli_library import router as cli_library_router  # noqa: E402
from snep.api.device_models import router as device_models_router  # noqa: E402
from snep.api.software_versions import router as ref_data_router  # noqa: E402
from snep.api.networking import router as networking_router  # noqa: E402
from snep.api.settings import router as settings_router  # noqa: E402
from snep.api.custom_filters import router as custom_filters_router  # noqa: E402

app.include_router(platforms_router, prefix="/api/v1/platforms", tags=["platforms"])
app.include_router(devices_router, prefix="/api/v1/devices", tags=["devices"])
app.include_router(interfaces_router, prefix="/api/v1/interfaces", tags=["interfaces"])
app.include_router(links_router, prefix="/api/v1/links", tags=["links"])
app.include_router(cli_mappings_router, prefix="/api/v1/cli-mappings", tags=["cli-mappings"])
app.include_router(scenarios_router, prefix="/api/v1/scenarios", tags=["scenarios"])
app.include_router(topology_router, prefix="/api/v1/topology", tags=["topology"])
app.include_router(export_router, prefix="/api/v1/export", tags=["export"])
app.include_router(execute_router, prefix="/api/v1", tags=["execute"])
app.include_router(imports_router, prefix="/api/v1/import", tags=["import"])
app.include_router(cli_library_router, prefix="/api/v1/cli-library", tags=["cli-library"])
app.include_router(device_models_router, prefix="/api/v1/device-models", tags=["device-models"])
app.include_router(ref_data_router, prefix="/api/v1", tags=["reference-data"])
app.include_router(networking_router, prefix="/api/v1", tags=["networking"])
app.include_router(settings_router, prefix="/api/v1", tags=["settings"])
app.include_router(custom_filters_router, prefix="/api/v1/custom-filters", tags=["custom-filters"])


@app.get("/health")
async def health():
    return {"status": "ok"}

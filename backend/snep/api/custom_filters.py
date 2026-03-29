"""Custom Jinja2 filter CRUD, testing, and management endpoints."""

import json
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from snep.api.deps import DBSession, PaginationDep
from snep.models.custom_filter import CustomFilter
from snep.services.filter_sandbox import (
    compile_filter, test_filter, get_allowed_modules,
    add_allowed_module, remove_allowed_module, BLOCKED_MODULES,
)

router = APIRouter()


class FilterCreate(BaseModel):
    name: str
    description: str = ""
    code: str
    signature: str = "value"
    test_input: str | None = None
    test_expected: str | None = None
    category: str = "general"
    platform_id: uuid.UUID | None = None


class FilterTest(BaseModel):
    name: str = "test_filter"
    code: str
    signature: str = "value"
    test_args: list = []


# --- CRUD ---

@router.get("")
async def list_filters(db: DBSession, pg: PaginationDep):
    result = await db.execute(
        select(CustomFilter).order_by(CustomFilter.category, CustomFilter.name)
        .offset(pg.offset).limit(pg.limit)
    )
    return [
        {
            "id": str(f.id), "name": f.name, "description": f.description,
            "signature": f.signature, "code": f.code,
            "test_input": f.test_input, "test_expected": f.test_expected,
            "category": f.category, "is_active": f.is_active, "is_builtin": f.is_builtin,
        }
        for f in result.scalars().all()
    ]


@router.get("/{filter_id}")
async def get_filter(filter_id: uuid.UUID, db: DBSession):
    f = await db.get(CustomFilter, filter_id)
    if not f:
        raise HTTPException(404, "Filter not found")
    return {
        "id": str(f.id), "name": f.name, "description": f.description,
        "signature": f.signature, "code": f.code,
        "test_input": f.test_input, "test_expected": f.test_expected,
        "category": f.category, "is_active": f.is_active, "is_builtin": f.is_builtin,
    }


@router.post("", status_code=201)
async def create_filter(body: FilterCreate, db: DBSession):
    # Validate by compiling
    try:
        compile_filter(body.name, body.code, body.signature)
    except Exception as e:
        raise HTTPException(422, f"Filter compilation failed: {e}")

    # Check name uniqueness
    existing = await db.execute(select(CustomFilter).where(CustomFilter.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Filter '{body.name}' already exists")

    f = CustomFilter(**body.model_dump())
    db.add(f)
    await db.commit()
    await db.refresh(f)

    # Register on Jinja2 environment
    from snep.services.filter_registry import load_custom_filters
    await load_custom_filters(db)

    return {"id": str(f.id), "name": f.name, "status": "created_and_registered"}


@router.put("/{filter_id}")
async def update_filter(filter_id: uuid.UUID, body: FilterCreate, db: DBSession):
    f = await db.get(CustomFilter, filter_id)
    if not f:
        raise HTTPException(404, "Filter not found")

    # Validate new code
    try:
        compile_filter(body.name, body.code, body.signature)
    except Exception as e:
        raise HTTPException(422, f"Filter compilation failed: {e}")

    for key, val in body.model_dump().items():
        setattr(f, key, val)
    await db.commit()

    # Reload filters
    from snep.services.filter_registry import load_custom_filters
    await load_custom_filters(db)

    return {"id": str(f.id), "name": f.name, "status": "updated_and_reloaded"}


@router.delete("/{filter_id}", status_code=204)
async def delete_filter(filter_id: uuid.UUID, db: DBSession):
    f = await db.get(CustomFilter, filter_id)
    if not f:
        raise HTTPException(404, "Filter not found")
    if f.is_builtin:
        raise HTTPException(403, "Cannot delete built-in filters. Deactivate instead.")
    await db.delete(f)
    await db.commit()

    from snep.services.filter_registry import load_custom_filters
    await load_custom_filters(db)


# --- Test ---

@router.post("/test")
async def test_filter_endpoint(body: FilterTest):
    """Compile and execute a filter with test arguments. Does NOT save."""
    result = test_filter(body.name, body.code, body.signature, body.test_args)
    return result


# --- Reload ---

@router.post("/reload")
async def reload_filters(db: DBSession):
    """Reload all custom filters from DB into the Jinja2 environment."""
    from snep.services.filter_registry import load_custom_filters
    result = await load_custom_filters(db)
    return result


# --- Module Management ---

@router.get("/modules/allowed")
async def list_allowed_modules():
    """List all allowed Python modules for custom filters."""
    return {
        "allowed": get_allowed_modules(),
        "blocked": sorted(BLOCKED_MODULES),
    }


@router.post("/modules/add")
async def add_module(body: dict):
    """Admin: add a Python module to the allowed list."""
    module = body.get("module", "")
    if not module:
        raise HTTPException(422, "Module name required")
    result = add_allowed_module(module)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/modules/remove")
async def remove_module(body: dict):
    module = body.get("module", "")
    result = remove_allowed_module(module)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


# --- Registered Filters Info ---

@router.get("/registered")
async def list_registered_filters():
    """List all Jinja2 filters (built-in + custom)."""
    from snep.services.filter_registry import get_all_filter_names
    return {"filters": get_all_filter_names()}

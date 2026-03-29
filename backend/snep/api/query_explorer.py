"""Query Explorer — execute queries against data sources, preview mappings, and import."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from snep.api.deps import DBSession, PaginationDep
from snep.models.data_source import DataSource
from snep.models.import_mapping import ImportMapping

router = APIRouter()


# --- Data Source CRUD ---

class DataSourceCreate(BaseModel):
    name: str
    source_type: str
    url: str = ""
    auth_token: str | None = None
    auth_type: str = "token"
    query_language: str = "graphql"
    graphql_path: str = "/graphql/"
    description: str | None = None


@router.get("/data-sources")
async def list_data_sources(db: DBSession):
    result = await db.execute(select(DataSource).order_by(DataSource.name))
    return [
        {
            "id": str(s.id), "name": s.name, "source_type": s.source_type,
            "url": s.url, "auth_type": s.auth_type, "query_language": s.query_language,
            "graphql_path": s.graphql_path, "is_active": s.is_active,
            "description": s.description,
            "has_auth": bool(s.auth_token),
        }
        for s in result.scalars().all()
    ]


@router.post("/data-sources", status_code=201)
async def create_data_source(body: DataSourceCreate, db: DBSession):
    ds = DataSource(**body.model_dump())
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return {"id": str(ds.id), "name": ds.name}


@router.put("/data-sources/{source_id}")
async def update_data_source(source_id: uuid.UUID, body: DataSourceCreate, db: DBSession):
    ds = await db.get(DataSource, source_id)
    if not ds:
        raise HTTPException(404, "Data source not found")
    for k, v in body.model_dump().items():
        setattr(ds, k, v)
    await db.commit()
    return {"id": str(ds.id), "name": ds.name, "status": "updated"}


@router.delete("/data-sources/{source_id}", status_code=204)
async def delete_data_source(source_id: uuid.UUID, db: DBSession):
    ds = await db.get(DataSource, source_id)
    if not ds:
        raise HTTPException(404)
    await db.delete(ds)
    await db.commit()


# --- Import Mapping CRUD ---

@router.get("/mappings")
async def list_mappings(db: DBSession):
    result = await db.execute(select(ImportMapping).order_by(ImportMapping.name))
    return [
        {
            "id": str(m.id), "name": m.name, "source_type": m.source_type,
            "description": m.description, "is_builtin": m.is_builtin,
            "has_query": bool(m.query),
        }
        for m in result.scalars().all()
    ]


@router.get("/mappings/{mapping_id}")
async def get_mapping(mapping_id: uuid.UUID, db: DBSession):
    m = await db.get(ImportMapping, mapping_id)
    if not m:
        raise HTTPException(404)
    return {
        "id": str(m.id), "name": m.name, "source_type": m.source_type,
        "description": m.description, "query": m.query, "result_path": m.result_path,
        "device_template": m.device_template, "interface_template": m.interface_template,
        "link_template": m.link_template, "is_builtin": m.is_builtin,
    }


@router.post("/mappings", status_code=201)
async def create_mapping(body: dict, db: DBSession):
    m = ImportMapping(**{k: v for k, v in body.items() if k != "id"})
    db.add(m)
    await db.commit()
    return {"id": str(m.id), "name": m.name}


@router.put("/mappings/{mapping_id}")
async def update_mapping(mapping_id: uuid.UUID, body: dict, db: DBSession):
    m = await db.get(ImportMapping, mapping_id)
    if not m:
        raise HTTPException(404)
    for k, v in body.items():
        if k not in ("id",) and hasattr(m, k):
            setattr(m, k, v)
    await db.commit()
    return {"id": str(m.id), "status": "updated"}


# --- Query Execution ---

@router.post("/execute")
async def execute_query_endpoint(body: dict, db: DBSession):
    """Execute a query against a data source."""
    source_id = body.get("source_id")
    query = body.get("query", "")

    if not source_id or not query:
        raise HTTPException(422, "source_id and query are required")

    source = await db.get(DataSource, source_id)
    if not source:
        raise HTTPException(404, "Data source not found")

    from snep.services.import_engine import execute_query
    try:
        result = await execute_query(source, query)
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# --- Preview Mapping ---

@router.post("/preview")
async def preview_mapping_endpoint(body: dict, db: DBSession):
    """Apply a mapping template to query results and show what would be imported."""
    results = body.get("results", [])
    mapping_id = body.get("mapping_id")
    device_template = body.get("device_template", "")
    result_path = body.get("result_path", "")

    # Extract results if raw response
    if result_path:
        from snep.services.import_engine import extract_results
        results = extract_results(results, result_path)

    # Use mapping from DB or inline template
    if mapping_id:
        mapping = await db.get(ImportMapping, mapping_id)
        if mapping:
            device_template = device_template or mapping.device_template

    if not device_template:
        raise HTTPException(422, "device_template is required")

    from snep.services.import_engine import apply_device_mapping
    mapped = apply_device_mapping(results, device_template, "preview")

    return {"preview": mapped, "count": len(mapped)}


# --- Import ---

@router.post("/import")
async def import_from_query(body: dict, db: DBSession):
    """Execute query, apply mapping, and import entities."""
    source_id = body.get("source_id")
    query = body.get("query", "")
    mapping_id = body.get("mapping_id")
    device_template = body.get("device_template", "")
    result_path = body.get("result_path", "")

    # Get source
    source = await db.get(DataSource, source_id) if source_id else None

    # Get mapping
    mapping = await db.get(ImportMapping, mapping_id) if mapping_id else None
    if mapping:
        query = query or mapping.query
        device_template = device_template or mapping.device_template
        result_path = result_path or mapping.result_path

    if not query or not device_template:
        raise HTTPException(422, "query and device_template are required")

    # Execute query
    from snep.services.import_engine import execute_query, extract_results, apply_device_mapping, create_entities_from_mapping

    if source:
        raw_results = await execute_query(source, query)
    else:
        raise HTTPException(422, "source_id is required for import")

    # Extract
    items = extract_results(raw_results, result_path)

    # Map
    mapped_devices = apply_device_mapping(items, device_template, source.name if source else "import")

    # Import
    stats = await create_entities_from_mapping(db, mapped_devices, source.name if source else "import")

    return stats

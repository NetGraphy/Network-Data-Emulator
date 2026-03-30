"""Config source management — Git repo CRUD, sync, and device config access."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from snep.api.deps import DBSession, PaginationDep
from snep.models.config_source import ConfigSource, DeviceConfig

router = APIRouter()


class ConfigSourceCreate(BaseModel):
    name: str
    source_type: str = "git"
    repo_url: str
    branch: str = "main"
    auth_token: str | None = None
    path_template: str = "{{ device.hostname }}.cfg"
    file_extension: str = ".cfg"
    description: str | None = None


# --- Config Source CRUD ---

@router.get("")
async def list_config_sources(db: DBSession):
    result = await db.execute(select(ConfigSource).order_by(ConfigSource.name))
    return [
        {
            "id": str(s.id), "name": s.name, "source_type": s.source_type,
            "repo_url": s.repo_url, "branch": s.branch,
            "path_template": s.path_template, "file_extension": s.file_extension,
            "last_sync_at": s.last_sync_at.isoformat() if s.last_sync_at else None,
            "last_sync_commit": s.last_sync_commit,
            "last_sync_status": s.last_sync_status,
            "last_sync_message": s.last_sync_message,
            "is_active": s.is_active, "description": s.description,
            "has_auth": bool(s.auth_token),
        }
        for s in result.scalars().all()
    ]


@router.post("", status_code=201)
async def create_config_source(body: ConfigSourceCreate, db: DBSession):
    s = ConfigSource(**body.model_dump())
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return {"id": str(s.id), "name": s.name}


@router.put("/{source_id}")
async def update_config_source(source_id: uuid.UUID, body: ConfigSourceCreate, db: DBSession):
    s = await db.get(ConfigSource, source_id)
    if not s:
        raise HTTPException(404, "Config source not found")
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    await db.commit()
    return {"id": str(s.id), "status": "updated"}


@router.delete("/{source_id}", status_code=204)
async def delete_config_source(source_id: uuid.UUID, db: DBSession):
    s = await db.get(ConfigSource, source_id)
    if not s:
        raise HTTPException(404)
    await db.delete(s)
    await db.commit()


# --- Sync ---

@router.post("/{source_id}/sync")
async def sync_config_source_endpoint(source_id: uuid.UUID, db: DBSession):
    """Clone/pull the Git repo and match configs to devices."""
    from snep.services.config_sync import sync_config_source
    result = await sync_config_source(db, str(source_id))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


# --- Device Configs ---

@router.get("/device-configs")
async def list_device_configs(db: DBSession, pg: PaginationDep, device_id: uuid.UUID | None = None):
    q = select(DeviceConfig)
    if device_id:
        q = q.where(DeviceConfig.device_id == device_id)
    q = q.order_by(DeviceConfig.updated_at.desc()).offset(pg.offset).limit(pg.limit)
    result = await db.execute(q)
    return [
        {
            "id": str(c.id), "device_id": str(c.device_id),
            "config_type": c.config_type,
            "line_count": c.line_count,
            "source_path": c.source_path,
            "source_commit": c.source_commit,
            "config_text": c.config_text[:500] + "..." if len(c.config_text) > 500 else c.config_text,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in result.scalars().all()
    ]


@router.get("/device-configs/{device_id}/running")
async def get_running_config(device_id: uuid.UUID, db: DBSession):
    """Get the full running config for a device."""
    result = await db.execute(
        select(DeviceConfig)
        .where(DeviceConfig.device_id == device_id, DeviceConfig.config_type == "running")
    )
    dc = result.scalar_one_or_none()
    if not dc:
        return {"config_text": None, "message": "No running config available for this device"}
    return {
        "config_text": dc.config_text,
        "line_count": dc.line_count,
        "source_path": dc.source_path,
        "source_commit": dc.source_commit,
        "updated_at": dc.updated_at.isoformat() if dc.updated_at else None,
    }


@router.get("/stats")
async def config_stats(db: DBSession):
    """Get config sync statistics."""
    total_configs = await db.scalar(select(func.count()).select_from(DeviceConfig))
    total_sources = await db.scalar(select(func.count()).select_from(ConfigSource))
    return {
        "total_config_sources": total_sources or 0,
        "total_device_configs": total_configs or 0,
    }

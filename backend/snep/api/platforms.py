"""Platform CRUD endpoints."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from snep.api.deps import DBSession, PaginationDep
from snep.models.platform import Platform

router = APIRouter()


class PlatformCreate(BaseModel):
    name: str
    display_name: str
    vendor: str
    prompt_template: str
    error_template: str
    cli_modes: dict = {}
    default_credentials: dict | None = None


class PlatformOut(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    vendor: str
    prompt_template: str
    error_template: str
    cli_modes: dict
    default_credentials: dict | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[PlatformOut])
async def list_platforms(db: DBSession, pg: PaginationDep):
    result = await db.execute(select(Platform).offset(pg.offset).limit(pg.limit))
    return result.scalars().all()


@router.get("/{platform_id}", response_model=PlatformOut)
async def get_platform(platform_id: uuid.UUID, db: DBSession):
    result = await db.execute(select(Platform).where(Platform.id == platform_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Platform not found")
    return p


@router.post("", response_model=PlatformOut, status_code=201)
async def create_platform(body: PlatformCreate, db: DBSession):
    p = Platform(**body.model_dump())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@router.put("/{platform_id}", response_model=PlatformOut)
async def update_platform(platform_id: uuid.UUID, body: PlatformCreate, db: DBSession):
    result = await db.execute(select(Platform).where(Platform.id == platform_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Platform not found")
    for k, v in body.model_dump().items():
        setattr(p, k, v)
    await db.commit()
    await db.refresh(p)
    return p


@router.delete("/{platform_id}", status_code=204)
async def delete_platform(platform_id: uuid.UUID, db: DBSession):
    result = await db.execute(select(Platform).where(Platform.id == platform_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Platform not found")
    await db.delete(p)
    await db.commit()

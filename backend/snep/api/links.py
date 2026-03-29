"""Link CRUD endpoints."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from snep.api.deps import DBSession, PaginationDep
from snep.models.interface import Interface
from snep.models.link import Link

router = APIRouter()


class LinkCreate(BaseModel):
    interface_a_id: uuid.UUID
    interface_b_id: uuid.UUID
    link_type: str = "physical"
    discovery_protocol: str = "cdp"


class LinkOut(BaseModel):
    id: uuid.UUID
    interface_a_id: uuid.UUID
    interface_b_id: uuid.UUID
    link_type: str
    discovery_protocol: str
    admin_state: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[LinkOut])
async def list_links(db: DBSession, pg: PaginationDep):
    result = await db.execute(select(Link).offset(pg.offset).limit(pg.limit))
    return result.scalars().all()


@router.get("/{link_id}", response_model=LinkOut)
async def get_link(link_id: uuid.UUID, db: DBSession):
    link = await db.get(Link, link_id)
    if not link:
        raise HTTPException(404, "Link not found")
    return link


@router.post("", response_model=LinkOut, status_code=201)
async def create_link(body: LinkCreate, db: DBSession):
    # Ensure both interfaces exist and are on different devices
    iface_a = await db.get(Interface, body.interface_a_id)
    iface_b = await db.get(Interface, body.interface_b_id)
    if not iface_a or not iface_b:
        raise HTTPException(404, "One or both interfaces not found")
    if iface_a.device_id == iface_b.device_id:
        raise HTTPException(422, "Both interfaces are on the same device")

    # Normalize order (lower UUID first)
    a_id, b_id = sorted([body.interface_a_id, body.interface_b_id])
    link = Link(
        interface_a_id=a_id,
        interface_b_id=b_id,
        link_type=body.link_type,
        discovery_protocol=body.discovery_protocol,
        admin_state="up",
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


@router.delete("/{link_id}", status_code=204)
async def delete_link(link_id: uuid.UUID, db: DBSession):
    link = await db.get(Link, link_id)
    if not link:
        raise HTTPException(404, "Link not found")
    await db.delete(link)
    await db.commit()

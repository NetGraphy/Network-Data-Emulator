"""Interface CRUD endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from snep.api.deps import DBSession, PaginationDep
from snep.models.interface import Interface, InterfaceCounter
from snep.services.state import compute_interface_counters

router = APIRouter()


class InterfaceOut(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    name: str
    short_name: str
    if_index: int
    interface_type: str
    admin_status: str
    oper_status: str
    speed_mbps: int
    mtu: int
    mac_address: str
    ip_address: str | None
    description: str | None
    counters: dict | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[InterfaceOut])
async def list_interfaces(db: DBSession, pg: PaginationDep, device_id: uuid.UUID | None = None):
    q = select(Interface).options(selectinload(Interface.counter))
    if device_id:
        q = q.where(Interface.device_id == device_id)
    q = q.order_by(Interface.sort_order).offset(pg.offset).limit(pg.limit)
    result = await db.execute(q)
    interfaces = result.scalars().all()

    out = []
    for iface in interfaces:
        d = InterfaceOut(
            id=iface.id,
            device_id=iface.device_id,
            name=iface.name,
            short_name=iface.short_name,
            if_index=iface.if_index,
            interface_type=iface.interface_type,
            admin_status=iface.admin_status,
            oper_status=iface.oper_status,
            speed_mbps=iface.speed_mbps,
            mtu=iface.mtu,
            mac_address=iface.mac_address,
            ip_address=str(iface.ip_address) if iface.ip_address else None,
            description=iface.description,
            counters=compute_interface_counters(iface.counter) if iface.counter else None,
        )
        out.append(d)
    return out


@router.get("/{interface_id}", response_model=InterfaceOut)
async def get_interface(interface_id: uuid.UUID, db: DBSession):
    result = await db.execute(
        select(Interface).options(selectinload(Interface.counter)).where(Interface.id == interface_id)
    )
    iface = result.scalar_one_or_none()
    if not iface:
        raise HTTPException(404, "Interface not found")
    return InterfaceOut(
        id=iface.id,
        device_id=iface.device_id,
        name=iface.name,
        short_name=iface.short_name,
        if_index=iface.if_index,
        interface_type=iface.interface_type,
        admin_status=iface.admin_status,
        oper_status=iface.oper_status,
        speed_mbps=iface.speed_mbps,
        mtu=iface.mtu,
        mac_address=iface.mac_address,
        ip_address=str(iface.ip_address) if iface.ip_address else None,
        description=iface.description,
        counters=compute_interface_counters(iface.counter) if iface.counter else None,
    )


@router.patch("/{interface_id}")
async def update_interface(interface_id: uuid.UUID, body: dict, db: DBSession):
    iface = await db.get(Interface, interface_id)
    if not iface:
        raise HTTPException(404, "Interface not found")

    allowed = {"admin_status", "oper_status", "description", "ip_address", "mtu", "speed_mbps"}
    now = datetime.now(timezone.utc)
    for k, v in body.items():
        if k in allowed:
            setattr(iface, k, v)

    # Side effects: if oper goes down, freeze counters
    if "oper_status" in body:
        iface.last_state_change = now
        counter = await db.get(InterfaceCounter, iface.id) if False else None
        # Load counter via relationship
        result = await db.execute(
            select(InterfaceCounter).where(InterfaceCounter.interface_id == interface_id)
        )
        counter = result.scalar_one_or_none()
        if counter:
            if body["oper_status"] == "down":
                counter.rate_in_bps = 0
                counter.rate_out_bps = 0
                counter.rate_reference = now
            elif body["oper_status"] == "up":
                counter.rate_in_bps = 300_000_000
                counter.rate_out_bps = 150_000_000
                counter.rate_reference = now

    # If admin goes down, oper also goes down
    if body.get("admin_status") == "down":
        iface.oper_status = "down"
        iface.last_state_change = now

    await db.commit()
    return {"id": str(iface.id), "name": iface.name, "oper_status": iface.oper_status}

"""Topology endpoints — returns graph data for visualization."""

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from snep.api.deps import DBSession
from snep.models import Device, DeviceModel, Interface, Link

router = APIRouter()


@router.get("")
async def get_topology(db: DBSession):
    """Return full topology as nodes + edges."""
    # Nodes
    device_result = await db.execute(
        select(Device).options(
            selectinload(Device.device_model).selectinload(DeviceModel.platform),
            selectinload(Device.interfaces),
        )
    )
    devices = device_result.scalars().all()

    nodes = []
    for d in devices:
        nodes.append({
            "id": str(d.id),
            "hostname": d.hostname,
            "platform": d.device_model.platform.name if d.device_model and d.device_model.platform else None,
            "model": d.device_model.display_name if d.device_model else None,
            "admin_state": d.admin_state,
            "interface_count": len(d.interfaces),
            "management_ip": str(d.management_ip) if d.management_ip else None,
            "tags": d.tags,
        })

    # Edges
    link_result = await db.execute(
        select(Link)
        .options(
            selectinload(Link.interface_a).selectinload(Interface.device),
            selectinload(Link.interface_b).selectinload(Interface.device),
        )
    )
    links = link_result.scalars().all()

    edges = []
    for lk in links:
        ia = lk.interface_a
        ib = lk.interface_b
        oper_state = "up" if (ia.oper_status == "up" and ib.oper_status == "up" and lk.admin_state == "up") else "down"
        edges.append({
            "id": str(lk.id),
            "source_device_id": str(ia.device_id),
            "source_interface": ia.name,
            "target_device_id": str(ib.device_id),
            "target_interface": ib.name,
            "link_type": lk.link_type,
            "admin_state": lk.admin_state,
            "oper_state": oper_state,
        })

    return {"nodes": nodes, "edges": edges}

"""Device Model, Software Version, and Vendor endpoints."""

import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from snep.api.deps import DBSession, PaginationDep
from snep.models.device import DeviceModel
from snep.models.software_version import SoftwareVersion
from snep.models.vendor import Vendor

router = APIRouter()


# --- Device Models ---

@router.get("")
async def list_device_models(db: DBSession, pg: PaginationDep, platform_id: uuid.UUID | None = None):
    q = select(DeviceModel).options(selectinload(DeviceModel.platform), selectinload(DeviceModel.vendor))
    if platform_id:
        q = q.where(DeviceModel.platform_id == platform_id)
    q = q.order_by(DeviceModel.display_name).offset(pg.offset).limit(pg.limit)
    result = await db.execute(q)
    return [
        {
            "id": str(m.id),
            "name": m.name,
            "slug": m.slug,
            "display_name": m.display_name,
            "platform_id": str(m.platform_id),
            "platform_name": m.platform.name if m.platform else None,
            "vendor_id": str(m.vendor_id) if m.vendor_id else None,
            "vendor_name": m.vendor.name if m.vendor else None,
            "part_number": m.part_number,
            "u_height": m.u_height,
            "interface_count": m.interface_count,
        }
        for m in result.scalars().all()
    ]


@router.get("/{model_id}")
async def get_device_model(model_id: uuid.UUID, db: DBSession):
    result = await db.execute(
        select(DeviceModel).options(selectinload(DeviceModel.platform), selectinload(DeviceModel.vendor))
        .where(DeviceModel.id == model_id)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Device model not found")
    return {
        "id": str(m.id), "name": m.name, "slug": m.slug,
        "display_name": m.display_name, "platform_id": str(m.platform_id),
        "vendor_id": str(m.vendor_id) if m.vendor_id else None,
        "vendor_name": m.vendor.name if m.vendor else None,
        "part_number": m.part_number,
        "default_interface_pattern": m.default_interface_pattern,
        "hardware_details": m.hardware_details,
    }

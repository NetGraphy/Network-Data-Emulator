"""Software Version and Vendor endpoints."""

import uuid

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from snep.api.deps import DBSession, PaginationDep
from snep.models.software_version import SoftwareVersion
from snep.models.vendor import Vendor

router = APIRouter()


# --- Software Versions ---

@router.get("/software-versions")
async def list_software_versions(db: DBSession, pg: PaginationDep, platform_id: uuid.UUID | None = None):
    q = select(SoftwareVersion).options(selectinload(SoftwareVersion.platform))
    if platform_id:
        q = q.where(SoftwareVersion.platform_id == platform_id)
    q = q.order_by(SoftwareVersion.version_string).offset(pg.offset).limit(pg.limit)
    result = await db.execute(q)
    return [
        {
            "id": str(sv.id),
            "platform_id": str(sv.platform_id),
            "platform_name": sv.platform.name if sv.platform else None,
            "version_string": sv.version_string,
            "major": sv.major,
            "minor": sv.minor,
            "patch": sv.patch,
            "status": sv.status,
        }
        for sv in result.scalars().all()
    ]


# --- Vendors ---

@router.get("/vendors")
async def list_vendors(db: DBSession, pg: PaginationDep):
    result = await db.execute(select(Vendor).order_by(Vendor.name).offset(pg.offset).limit(pg.limit))
    return [
        {"id": str(v.id), "name": v.name, "slug": v.slug, "url": v.url}
        for v in result.scalars().all()
    ]

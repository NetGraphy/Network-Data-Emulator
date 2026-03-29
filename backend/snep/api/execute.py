"""Command execution preview endpoint."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from snep.api.deps import DBSession
from snep.services.state import get_device_full

router = APIRouter()


class ExecuteRequest(BaseModel):
    command: str


@router.post("/devices/{device_id}/execute")
async def execute_command(device_id: uuid.UUID, body: ExecuteRequest, db: DBSession):
    """Execute a CLI command against a device and return rendered output."""
    device = await get_device_full(db, str(device_id))
    if not device:
        raise HTTPException(404, "Device not found")

    from snep.services.rendering import render_command
    result = await render_command(db, device, body.command)

    return {
        "command": body.command,
        "output": result["output"],
        "rendering_mode": result["mode"],
    }

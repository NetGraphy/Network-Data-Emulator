"""CLI Output Mapping endpoints — paste and manage CLI output samples."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from snep.api.deps import DBSession, PaginationDep
from snep.models.cli_mapping import CLIOutputMapping

router = APIRouter()


class CLIMappingCreate(BaseModel):
    device_id: uuid.UUID
    command: str
    raw_output: str
    mode: str = "static"
    field_annotations: list | None = None
    source_description: str | None = None


class CLIMappingOut(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    command: str
    raw_output: str
    mode: str
    field_annotations: list | None
    is_active: bool
    source_description: str | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[CLIMappingOut])
async def list_mappings(db: DBSession, pg: PaginationDep, device_id: uuid.UUID | None = None):
    q = select(CLIOutputMapping)
    if device_id:
        q = q.where(CLIOutputMapping.device_id == device_id)
    q = q.offset(pg.offset).limit(pg.limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{mapping_id}", response_model=CLIMappingOut)
async def get_mapping(mapping_id: uuid.UUID, db: DBSession):
    m = await db.get(CLIOutputMapping, mapping_id)
    if not m:
        raise HTTPException(404, "Mapping not found")
    return m


@router.post("", response_model=CLIMappingOut, status_code=201)
async def create_mapping(body: CLIMappingCreate, db: DBSession):
    # Deactivate existing active mapping for same device+command
    result = await db.execute(
        select(CLIOutputMapping)
        .where(CLIOutputMapping.device_id == body.device_id)
        .where(CLIOutputMapping.command == body.command)
        .where(CLIOutputMapping.is_active == True)
    )
    for existing in result.scalars().all():
        existing.is_active = False

    m = CLIOutputMapping(**body.model_dump())
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m


@router.put("/{mapping_id}", response_model=CLIMappingOut)
async def update_mapping(mapping_id: uuid.UUID, body: dict, db: DBSession):
    m = await db.get(CLIOutputMapping, mapping_id)
    if not m:
        raise HTTPException(404, "Mapping not found")
    allowed = {"raw_output", "mode", "field_annotations", "is_active", "source_description"}
    for k, v in body.items():
        if k in allowed:
            setattr(m, k, v)
    await db.commit()
    await db.refresh(m)
    return m


@router.delete("/{mapping_id}", status_code=204)
async def delete_mapping(mapping_id: uuid.UUID, db: DBSession):
    m = await db.get(CLIOutputMapping, mapping_id)
    if not m:
        raise HTTPException(404, "Mapping not found")
    await db.delete(m)
    await db.commit()


@router.post("/parse-neighbors")
async def parse_neighbors(body: dict, db: DBSession):
    """Parse CDP/LLDP neighbor output and match against inventory.

    Input: { "raw_output": "...", "command_type": "cdp" | "lldp" }
    Returns: list of parsed neighbor entries with match status.
    """
    raw = body.get("raw_output", "")
    cmd_type = body.get("command_type", "cdp")

    entries = _parse_neighbor_output(raw, cmd_type)

    # Try to match each neighbor against existing devices
    from snep.models.device import Device
    for entry in entries:
        result = await db.execute(
            select(Device).where(Device.hostname == entry["device_id"])
        )
        device = result.scalar_one_or_none()
        if device:
            entry["matched_device_id"] = str(device.id)
            entry["match_status"] = "matched"
        else:
            # Try partial match
            result = await db.execute(
                select(Device).where(Device.hostname.ilike(f"%{entry['device_id']}%"))
            )
            partial = result.scalars().first()
            if partial:
                entry["matched_device_id"] = str(partial.id)
                entry["match_status"] = "partial_match"
                entry["matched_hostname"] = partial.hostname
            else:
                entry["matched_device_id"] = None
                entry["match_status"] = "unmatched"

    return entries


def _parse_neighbor_output(raw: str, cmd_type: str) -> list[dict]:
    """Parse CDP or LLDP neighbor output into structured entries."""
    lines = raw.strip().split("\n")
    entries = []

    if cmd_type == "cdp":
        # Find header line
        header_idx = -1
        for i, line in enumerate(lines):
            if "Device ID" in line and "Local Intrfce" in line:
                header_idx = i
                break

        if header_idx < 0:
            return entries

        for line in lines[header_idx + 1:]:
            line = line.strip()
            if not line or line.startswith("Total"):
                continue
            # CDP format: DeviceID  Local_Intf  Holdtime  Capability  Platform  Port_ID
            parts = line.split()
            if len(parts) >= 6:
                entries.append({
                    "device_id": parts[0],
                    "local_interface": _expand_parts(parts, 1, 2),
                    "holdtime": parts[3] if len(parts) > 3 else "162",
                    "capabilities": parts[4] if len(parts) > 4 else "",
                    "platform": parts[5] if len(parts) > 5 else "",
                    "remote_interface": _expand_parts(parts, -2, -1) if len(parts) > 6 else parts[-1],
                })
            elif len(parts) >= 2:
                entries.append({
                    "device_id": parts[0],
                    "local_interface": parts[1] if len(parts) > 1 else "",
                    "remote_interface": parts[-1] if len(parts) > 2 else "",
                })
    elif cmd_type == "lldp":
        header_idx = -1
        for i, line in enumerate(lines):
            if "System Name" in line or "Device ID" in line:
                header_idx = i
                break

        if header_idx < 0:
            return entries

        for line in lines[header_idx + 1:]:
            line = line.strip()
            if not line or line.startswith("Total"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                entries.append({
                    "device_id": parts[0],
                    "local_interface": parts[1] if len(parts) > 1 else "",
                    "remote_interface": parts[-1] if len(parts) > 2 else "",
                })

    return entries


def _expand_parts(parts: list[str], start: int, end: int) -> str:
    """Join interface name parts (e.g., 'Gig' '0/1' -> 'Gig 0/1')."""
    try:
        return " ".join(parts[start:end + 1])
    except (IndexError, TypeError):
        return parts[start] if abs(start) <= len(parts) else ""

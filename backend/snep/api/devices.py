"""Device CRUD endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from snep.api.deps import DBSession, PaginationDep
from snep.models import (
    ConnectionMapping,
    Device,
    DeviceCredential,
    DeviceModel,
    Interface,
    SNMPProfile,
)
from snep.services.networking import allocate_connection_mappings

router = APIRouter()


class DeviceCreate(BaseModel):
    device_model_id: uuid.UUID
    hostname: str
    management_ip: str | None = None
    serial_number: str | None = None
    software_version: str | None = None
    tags: dict | None = None
    auto_create_interfaces: bool = True
    auto_create_snmp_profile: bool = True
    username: str = "admin"
    password: str = "cisco123"
    enable_password: str | None = "enable456"


class DeviceOut(BaseModel):
    id: uuid.UUID
    hostname: str
    management_ip: str | None
    serial_number: str
    software_version: str | None
    admin_state: str
    tags: dict | None
    interface_count: int = 0
    connection_info: dict | None = None

    model_config = {"from_attributes": True}


class DeviceSummary(BaseModel):
    id: uuid.UUID
    hostname: str
    management_ip: str | None
    admin_state: str
    tags: dict | None
    platform_name: str | None = None
    model_name: str | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[DeviceSummary])
async def list_devices(db: DBSession, pg: PaginationDep):
    result = await db.execute(
        select(Device)
        .options(selectinload(Device.device_model).selectinload(DeviceModel.platform))
        .offset(pg.offset)
        .limit(pg.limit)
        .order_by(Device.hostname)
    )
    devices = result.scalars().all()
    out = []
    for d in devices:
        out.append(DeviceSummary(
            id=d.id,
            hostname=d.hostname,
            management_ip=str(d.management_ip) if d.management_ip else None,
            admin_state=d.admin_state,
            tags=d.tags,
            platform_name=d.device_model.platform.name if d.device_model and d.device_model.platform else None,
            model_name=d.device_model.display_name if d.device_model else None,
        ))
    return out


@router.get("/{device_id}")
async def get_device(device_id: uuid.UUID, db: DBSession):
    result = await db.execute(
        select(Device)
        .options(
            selectinload(Device.interfaces),
            selectinload(Device.device_model).selectinload(DeviceModel.platform),
            selectinload(Device.snmp_profile),
            selectinload(Device.credentials),
            selectinload(Device.connection_mappings),
            selectinload(Device.cli_mappings),
        )
        .where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(404, "Device not found")

    conn_info = {}
    for cm in device.connection_mappings:
        conn_info[cm.protocol] = {"host": cm.listen_address, "port": cm.listen_port}

    now = datetime.now(timezone.utc)
    uptime = device.uptime_seconds + int((now - device.uptime_reference).total_seconds())

    return {
        "id": str(device.id),
        "hostname": device.hostname,
        "management_ip": str(device.management_ip) if device.management_ip else None,
        "serial_number": device.serial_number,
        "software_version": device.software_version or (device.device_model.software_version if device.device_model else None),
        "admin_state": device.admin_state,
        "current_uptime_seconds": uptime,
        "tags": device.tags,
        "device_model": {
            "id": str(device.device_model.id),
            "name": device.device_model.name,
            "display_name": device.device_model.display_name,
        } if device.device_model else None,
        "platform": {
            "id": str(device.device_model.platform.id),
            "name": device.device_model.platform.name,
        } if device.device_model and device.device_model.platform else None,
        "interface_count": len(device.interfaces),
        "connection_info": conn_info,
        "snmp_profile": {
            "v2_enabled": device.snmp_profile.v2_enabled,
            "v2_community": device.snmp_profile.v2_community,
            "v3_enabled": device.snmp_profile.v3_enabled,
        } if device.snmp_profile else None,
        "cli_mapping_count": len(device.cli_mappings),
    }


@router.post("", status_code=201)
async def create_device(body: DeviceCreate, db: DBSession):
    # Generate serial if not provided
    serial = body.serial_number or f"FCW{uuid.uuid4().hex[:8].upper()}"

    device = Device(
        device_model_id=body.device_model_id,
        hostname=body.hostname,
        management_ip=body.management_ip,
        serial_number=serial,
        software_version=body.software_version,
        uptime_seconds=7_776_000,
        uptime_reference=datetime.now(timezone.utc),
        admin_state="active",
        tags=body.tags,
    )
    db.add(device)
    await db.flush()

    # Credential
    db.add(DeviceCredential(
        device_id=device.id,
        username=body.username,
        password=body.password,
        enable_password=body.enable_password,
        privilege_level=1,
    ))

    # SNMP Profile
    if body.auto_create_snmp_profile:
        db.add(SNMPProfile(
            device_id=device.id,
            v2_enabled=True,
            v2_community="public",
        ))

    # Auto-create interfaces from model
    if body.auto_create_interfaces:
        model = await db.get(DeviceModel, body.device_model_id)
        if model and model.default_interface_pattern:
            from snep.models.interface import InterfaceCounter
            idx = 1
            now = datetime.now(timezone.utc)
            for pattern in model.default_interface_pattern:
                prefix = pattern["prefix"]
                r = pattern.get("range", [0, 0])
                for n in range(r[0], r[1] + 1):
                    name = f"{prefix}{n}"
                    short = _abbreviate(name)
                    iface = Interface(
                        device_id=device.id,
                        name=name,
                        short_name=short,
                        if_index=idx,
                        interface_type=pattern.get("type", "ethernet"),
                        speed_mbps=pattern.get("speed", 1000),
                        mtu=1500 if pattern.get("type") != "loopback" else 65535,
                        mac_address=f"aabb.cc00.{idx:04x}",
                        last_state_change=now,
                        sort_order=idx,
                    )
                    db.add(iface)
                    await db.flush()
                    db.add(InterfaceCounter(
                        interface_id=iface.id,
                        rate_in_bps=300_000_000 if pattern.get("speed", 1000) >= 1000 else 0,
                        rate_out_bps=150_000_000 if pattern.get("speed", 1000) >= 1000 else 0,
                        rate_reference=now,
                        updated_at=now,
                    ))
                    idx += 1

    # Connection mappings
    await allocate_connection_mappings(db, device.id)

    await db.commit()
    return {"id": str(device.id), "hostname": device.hostname}


@router.patch("/{device_id}")
async def update_device(device_id: uuid.UUID, body: dict, db: DBSession):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(404, "Device not found")
    allowed = {"hostname", "management_ip", "admin_state", "tags", "software_version"}
    for k, v in body.items():
        if k in allowed:
            setattr(device, k, v)
    await db.commit()
    return {"id": str(device.id), "hostname": device.hostname}


@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: uuid.UUID, db: DBSession):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(404, "Device not found")
    await db.delete(device)
    await db.commit()


@router.get("/{device_id}/neighbors")
async def get_device_neighbors(device_id: uuid.UUID, db: DBSession):
    from snep.services.state import get_neighbors
    return await get_neighbors(db, str(device_id))


def _abbreviate(name: str) -> str:
    """Generate short interface name."""
    abbrevs = {
        "GigabitEthernet": "Gi",
        "TenGigabitEthernet": "Te",
        "FastEthernet": "Fa",
        "Ethernet": "Et",
        "Loopback": "Lo",
        "Vlan": "Vl",
        "Port-channel": "Po",
        "Tunnel": "Tu",
        "Management": "Ma",
    }
    for long, short in abbrevs.items():
        if name.startswith(long):
            return name.replace(long, short, 1)
    return name

"""Networking status endpoint — shows detected environment and connection strategy."""

from fastapi import APIRouter
from sqlalchemy import func, select

from snep.api.deps import DBSession
from snep.config import settings
from snep.models.connection import ConnectionMapping
from snep.services.environment import detect_environment

router = APIRouter()


@router.get("/networking/status")
async def networking_status(db: DBSession):
    """Return detected environment, connection mode, and address info."""
    env = detect_environment()

    # Get port ranges
    ssh_ports = await db.execute(
        select(func.min(ConnectionMapping.listen_port), func.max(ConnectionMapping.listen_port))
        .where(ConnectionMapping.protocol == "ssh")
    )
    snmp_ports = await db.execute(
        select(func.min(ConnectionMapping.listen_port), func.max(ConnectionMapping.listen_port))
        .where(ConnectionMapping.protocol == "snmp")
    )
    ssh_range = ssh_ports.one_or_none()
    snmp_range = snmp_ports.one_or_none()

    device_count = await db.scalar(
        select(func.count(func.distinct(ConnectionMapping.device_id)))
    )

    # Sample connect info
    sample = await db.execute(
        select(ConnectionMapping).where(ConnectionMapping.protocol == "ssh").limit(1)
    )
    sample_mapping = sample.scalar_one_or_none()

    return {
        "environment": env,
        "config": {
            "mode": settings.networking.mode,
            "bind_address": settings.networking.bind_address,
            "connect_address_override": settings.networking.connect_address or None,
            "connect_hostname": settings.networking.connect_hostname or None,
            "loopback_range": settings.networking.loopback_range,
            "ssh_base_port": settings.networking.ssh_base_port,
            "snmp_base_port": settings.networking.snmp_base_port,
        },
        "allocation": {
            "device_count": device_count or 0,
            "ssh_port_range": f"{ssh_range[0]}-{ssh_range[1]}" if ssh_range and ssh_range[0] else "none",
            "snmp_port_range": f"{snmp_range[0]}-{snmp_range[1]}" if snmp_range and snmp_range[0] else "none",
        },
        "example_connection": {
            "ssh": f"ssh admin@{sample_mapping.connect_address} -p {sample_mapping.connect_port}" if sample_mapping else None,
            "snmp": f"snmpwalk -v2c -c public {sample_mapping.connect_address}:{sample_mapping.connect_port + 10000}" if sample_mapping else None,
        } if sample_mapping else None,
    }

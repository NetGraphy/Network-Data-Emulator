"""Settings API — runtime-configurable networking and connection settings.

Stores settings in the database so they survive container restarts
and can be changed from the UI without redeployment.
"""

import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from snep.api.deps import DBSession
from snep.models.connection import ConnectionMapping
from snep.services.environment import detect_environment, get_connect_address

router = APIRouter()


class NetworkingConfig(BaseModel):
    connect_address: str = ""  # empty = auto-detect
    connect_hostname: str = ""  # friendly label
    ssh_gateway_port: int = 2222
    mode: str = "port_multiplex"  # port_multiplex, loopback, auto
    notes: str = ""


@router.get("/settings/networking")
async def get_networking_settings(db: DBSession):
    """Return current networking configuration and detected environment."""
    env = detect_environment()

    # Get actual stored connect addresses from DB
    result = await db.execute(
        select(ConnectionMapping).where(ConnectionMapping.protocol == "ssh").limit(1)
    )
    sample = result.scalar_one_or_none()

    # Count devices
    from sqlalchemy import func
    device_count = await db.scalar(
        select(func.count(func.distinct(ConnectionMapping.device_id)))
    )

    # Get all unique connect addresses in use
    addrs = await db.execute(
        select(ConnectionMapping.connect_address).distinct().where(ConnectionMapping.protocol == "ssh")
    )
    unique_addrs = [r[0] for r in addrs.all()]

    return {
        "detected_environment": env,
        "current_config": {
            "connect_address": sample.connect_address if sample else "NOT_SET",
            "mode": env.get("type", "unknown"),
            "device_count": device_count or 0,
            "unique_connect_addresses": unique_addrs,
        },
        "connection_methods": _build_connection_methods(env, sample, device_count or 0),
    }


@router.post("/settings/networking/connect-address")
async def update_connect_address(body: dict, db: DBSession):
    """Update the connect address for all devices.

    This is the address external tools use to reach the emulated devices.
    Set to a real IP, hostname, or empty string to auto-detect.
    """
    new_address = body.get("connect_address", "").strip()

    if not new_address:
        # Auto-detect
        new_address = get_connect_address()

    # Update all connection mappings
    await db.execute(
        update(ConnectionMapping).values(connect_address=new_address)
    )
    await db.commit()

    # Verify
    result = await db.execute(
        select(ConnectionMapping.connect_address).distinct().where(ConnectionMapping.protocol == "ssh")
    )
    updated = [r[0] for r in result.all()]

    return {
        "connect_address": new_address,
        "updated_addresses": updated,
        "message": f"All devices now connectable at {new_address}",
    }


def _build_connection_methods(env: dict, sample, device_count: int) -> list[dict]:
    """Build a list of connection methods with documentation."""
    methods = []
    connect = sample.connect_address if sample else "127.0.0.1"
    ssh_port = sample.listen_port if sample else 10000

    # Method 1: Direct port-per-device
    methods.append({
        "id": "port_per_device",
        "name": "Direct Port (per device)",
        "description": "Each device has its own SSH port. Simple, works with all tools.",
        "when_to_use": "Local Docker, lab environments, small deployments",
        "example_ssh": f"ssh admin@{connect} -p {ssh_port}",
        "example_nornir": {
            "hostname": connect,
            "port": ssh_port,
            "username": "admin",
            "password": "cisco123",
        },
        "pros": ["Works with any SSH tool", "Standard Nornir/Ansible inventory", "No special client config"],
        "cons": [f"Requires {device_count} ports exposed", "Port numbers must be tracked"],
        "available": connect != "NOT_REACHABLE",
    })

    # Method 2: SSH Gateway
    methods.append({
        "id": "ssh_gateway",
        "name": "SSH Gateway (single port)",
        "description": "One port for all devices. Device selected via username: admin%hostname",
        "when_to_use": "Cloud, NAT, firewalled environments, large deployments",
        "example_ssh": f"ssh admin%core-rtr-01@{connect} -p 2222",
        "example_nornir": {
            "hostname": connect,
            "port": 2222,
            "username": "admin%core-rtr-01",
            "password": "cisco123",
        },
        "pros": ["Only 1 port needed", "Works behind NAT/firewall", "Scales to thousands of devices"],
        "cons": ["Username format requires % separator", "Some tools may not support % in username"],
        "available": connect != "NOT_REACHABLE",
    })

    # Method 3: Loopback aliases (native only)
    methods.append({
        "id": "loopback_aliases",
        "name": "Loopback Aliases (native)",
        "description": "Each device gets its own 127.x.x.x IP with standard ports (22, 161).",
        "when_to_use": "Native (non-Docker) environments, maximum realism",
        "example_ssh": "ssh admin@127.0.0.2 -p 22",
        "example_nornir": {
            "hostname": "127.0.0.2",
            "port": 22,
            "username": "admin",
            "password": "cisco123",
        },
        "setup_required": "Run: sudo ifconfig lo0 alias 127.0.0.2 (macOS) or ip addr add 127.0.0.2/32 dev lo (Linux)",
        "pros": ["Standard ports (22/161)", "Most realistic", "Tools work with zero config"],
        "cons": ["Requires sudo/root for alias setup", "Not available in Docker"],
        "available": env.get("type") in ("native", "native_loopback"),
    })

    return methods

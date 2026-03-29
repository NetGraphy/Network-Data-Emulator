"""Flexible IP/port allocation for device connection mappings.

Supports multiple modes and auto-detects the correct connect address
based on runtime environment (Docker, Railway, native).

Key distinction:
- listen_address: where the server binds (0.0.0.0, 127.0.0.x)
- connect_address: where external tools connect (127.0.0.1, host IP, hostname)
"""

import ipaddress

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from snep.config import settings
from snep.models.connection import ConnectionMapping
from snep.services.environment import get_connect_address


async def allocate_connection_mappings(
    session: AsyncSession,
    device_id: str,
    mode: str | None = None,
) -> tuple[ConnectionMapping, ConnectionMapping]:
    """Allocate SSH and SNMP connection mappings for a device.

    Automatically detects the correct connect_address based on environment.
    Returns (ssh_mapping, snmp_mapping).
    """
    mode = mode or settings.networking.mode

    if mode == "auto":
        device_count = await session.scalar(
            select(func.count()).select_from(ConnectionMapping).where(ConnectionMapping.protocol == "ssh")
        )
        if device_count < 254 and settings.networking.prefer_standard_ports:
            mode = "loopback"
        else:
            mode = "port_multiplex"

    if mode == "loopback":
        return await _allocate_loopback(session, device_id)
    elif mode == "hybrid":
        try:
            return await _allocate_loopback(session, device_id)
        except RuntimeError:
            return await _allocate_port_multiplex(session, device_id)
    else:
        return await _allocate_port_multiplex(session, device_id)


async def _allocate_port_multiplex(
    session: AsyncSession,
    device_id: str,
) -> tuple[ConnectionMapping, ConnectionMapping]:
    """Assign next available port pair on the bind address."""
    base_ssh = settings.networking.ssh_base_port
    base_snmp = settings.networking.snmp_base_port
    bind = settings.networking.bind_address
    connect = get_connect_address()

    # Find highest allocated SSH port
    result = await session.scalar(
        select(func.max(ConnectionMapping.listen_port))
        .where(ConnectionMapping.protocol == "ssh")
        .where(ConnectionMapping.listen_address == bind)
    )
    next_ssh_port = (result + 1) if result else base_ssh

    result = await session.scalar(
        select(func.max(ConnectionMapping.listen_port))
        .where(ConnectionMapping.protocol == "snmp")
        .where(ConnectionMapping.listen_address == bind)
    )
    next_snmp_port = (result + 1) if result else base_snmp

    ssh = ConnectionMapping(
        device_id=device_id, protocol="ssh",
        listen_address=bind, listen_port=next_ssh_port,
        connect_address=connect, connect_port=next_ssh_port,
    )
    snmp = ConnectionMapping(
        device_id=device_id, protocol="snmp",
        listen_address=bind, listen_port=next_snmp_port,
        connect_address=connect, connect_port=next_snmp_port,
    )
    session.add_all([ssh, snmp])
    return ssh, snmp


async def _allocate_loopback(
    session: AsyncSession,
    device_id: str,
) -> tuple[ConnectionMapping, ConnectionMapping]:
    """Assign next available loopback IP with standard ports (22/161).

    In loopback mode, listen and connect addresses are the same.
    """
    network = ipaddress.ip_network(settings.networking.loopback_range, strict=False)

    result = await session.scalar(
        select(func.max(ConnectionMapping.listen_address))
        .where(ConnectionMapping.protocol == "ssh")
        .where(ConnectionMapping.listen_port == 22)
    )

    if result:
        last_ip = ipaddress.ip_address(result)
        next_ip = last_ip + 1
    else:
        next_ip = network.network_address + 2

    if next_ip not in network:
        raise RuntimeError(f"Loopback range {network} exhausted")

    ip_str = str(next_ip)
    ssh = ConnectionMapping(
        device_id=device_id, protocol="ssh",
        listen_address=ip_str, listen_port=22,
        connect_address=ip_str, connect_port=22,
    )
    snmp = ConnectionMapping(
        device_id=device_id, protocol="snmp",
        listen_address=ip_str, listen_port=161,
        connect_address=ip_str, connect_port=161,
    )
    session.add_all([ssh, snmp])
    return ssh, snmp

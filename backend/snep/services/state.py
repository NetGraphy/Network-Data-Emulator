"""State service — reads device/interface state with computed counters and neighbors."""

from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from snep.models import Device, DeviceModel, Interface, InterfaceCounter, Link, Platform
from snep.services.counter import compute_current_counter, compute_current_packets


async def get_device_full(session: AsyncSession, device_id: str) -> Device | None:
    """Load a device with all relationships including nested platform."""
    result = await session.execute(
        select(Device)
        .options(
            selectinload(Device.interfaces).selectinload(Interface.counter),
            selectinload(Device.device_model).selectinload(DeviceModel.platform),
            selectinload(Device.snmp_profile),
            selectinload(Device.credentials),
            selectinload(Device.connection_mappings),
            selectinload(Device.cli_mappings),
        )
        .where(Device.id == device_id)
    )
    return result.scalar_one_or_none()


async def get_device_by_hostname(session: AsyncSession, hostname: str) -> Device | None:
    result = await session.execute(
        select(Device)
        .options(
            selectinload(Device.interfaces).selectinload(Interface.counter),
            selectinload(Device.device_model),
            selectinload(Device.snmp_profile),
            selectinload(Device.credentials),
            selectinload(Device.connection_mappings),
        )
        .where(Device.hostname == hostname)
    )
    return result.scalar_one_or_none()


async def get_neighbors(session: AsyncSession, device_id: str) -> list[dict]:
    """Get resolved neighbor data for a device (from links)."""
    # Get all interfaces for this device
    iface_result = await session.execute(
        select(Interface).where(Interface.device_id == device_id)
    )
    device_interfaces = {str(i.id): i for i in iface_result.scalars().all()}
    iface_ids = list(device_interfaces.keys())

    if not iface_ids:
        return []

    # Get all links involving this device's interfaces
    link_result = await session.execute(
        select(Link)
        .where(or_(Link.interface_a_id.in_(iface_ids), Link.interface_b_id.in_(iface_ids)))
        .where(Link.admin_state == "up")
    )
    links = link_result.scalars().all()

    neighbors = []
    for link in links:
        a_id = str(link.interface_a_id)
        b_id = str(link.interface_b_id)

        if a_id in device_interfaces:
            local_iface = device_interfaces[a_id]
            remote_iface_id = link.interface_b_id
        else:
            local_iface = device_interfaces[b_id]
            remote_iface_id = link.interface_a_id

        # Check local interface is up
        if local_iface.oper_status != "up":
            continue

        # Load remote interface and its device
        remote_result = await session.execute(
            select(Interface)
            .options(selectinload(Interface.device).selectinload(Device.device_model))
            .where(Interface.id == remote_iface_id)
        )
        remote_iface = remote_result.scalar_one_or_none()
        if not remote_iface or remote_iface.oper_status != "up":
            continue

        remote_device = remote_iface.device
        neighbors.append({
            "local_interface": local_iface.name,
            "local_short_name": local_iface.short_name,
            "remote_hostname": remote_device.hostname,
            "remote_interface": remote_iface.name,
            "remote_short_name": remote_iface.short_name,
            "remote_platform": remote_device.device_model.display_name if remote_device.device_model else "",
            "remote_ip": remote_iface.ip_address,
            "discovery_protocol": link.discovery_protocol,
            "holdtime": 162,
            "capabilities": "R S I",
        })

    return neighbors


def compute_interface_counters(counter: InterfaceCounter, now: datetime | None = None) -> dict:
    """Compute current counter values with rate progression."""
    if now is None:
        now = datetime.now(timezone.utc)

    current_in = compute_current_counter(counter.in_octets, counter.rate_in_bps, counter.rate_reference, now)
    current_out = compute_current_counter(counter.out_octets, counter.rate_out_bps, counter.rate_reference, now)
    current_in_pkts = compute_current_packets(counter.in_octets, counter.rate_in_bps, counter.rate_reference, counter.in_unicast_pkts, now)
    current_out_pkts = compute_current_packets(counter.out_octets, counter.rate_out_bps, counter.rate_reference, counter.out_unicast_pkts, now)

    return {
        "in_octets": current_in,
        "out_octets": current_out,
        "in_unicast_pkts": current_in_pkts,
        "out_unicast_pkts": current_out_pkts,
        "in_multicast_pkts": counter.in_multicast_pkts,
        "out_multicast_pkts": counter.out_multicast_pkts,
        "in_broadcast_pkts": counter.in_broadcast_pkts,
        "out_broadcast_pkts": counter.out_broadcast_pkts,
        "in_errors": counter.in_errors,
        "out_errors": counter.out_errors,
        "in_discards": counter.in_discards,
        "out_discards": counter.out_discards,
        "crc_errors": counter.crc_errors,
        "collisions": counter.collisions,
        "rate_in_bps": counter.rate_in_bps,
        "rate_out_bps": counter.rate_out_bps,
    }

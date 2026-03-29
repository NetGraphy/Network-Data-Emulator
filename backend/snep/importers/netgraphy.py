"""NetGraphy importer — reads devices, interfaces, and CONNECTED_TO edges directly from Neo4j."""

import logging
from datetime import datetime, timezone

from neo4j import AsyncGraphDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snep.models import Device, DeviceModel, Interface, InterfaceCounter, Link, Platform, SNMPProfile
from snep.services.networking import allocate_connection_mappings

logger = logging.getLogger(__name__)

PLATFORM_MAP = {
    "Cisco IOS": "cisco_ios",
    "Cisco IOS-XE": "cisco_ios",
    "Cisco NX-OS": "cisco_ios",
    "Arista EOS": "arista_eos",
    "Juniper JunOS": "juniper_junos",
}


async def import_netgraphy(
    session: AsyncSession,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    hostname_filter: str | None = None,
) -> dict:
    """Import devices and topology from a NetGraphy Neo4j database."""
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    stats = {"imported_devices": 0, "imported_interfaces": 0, "imported_links": 0, "skipped": []}
    now = datetime.now(timezone.utc)

    try:
        async with driver.session() as neo_session:
            # Query devices with their interfaces and platform
            device_query = """
            MATCH (d:Device)-[:HAS_INTERFACE]->(i:Interface)
            OPTIONAL MATCH (d)-[:RUNS_PLATFORM]->(p:Platform)
            OPTIONAL MATCH (d)-[:HAS_MODEL]->(hm:HardwareModel)
            """
            if hostname_filter:
                device_query += f" WHERE d.hostname CONTAINS '{hostname_filter}'"
            device_query += """
            RETURN d.hostname AS hostname,
                   d.management_ip AS management_ip,
                   d.serial_number AS serial_number,
                   d.status AS status,
                   d.role AS role,
                   p.name AS platform_name,
                   hm.model AS hardware_model,
                   hm.slug AS hardware_slug,
                   collect({
                       name: i.name,
                       interface_type: i.interface_type,
                       enabled: i.enabled,
                       oper_status: i.oper_status,
                       speed_mbps: i.speed_mbps,
                       mtu: i.mtu,
                       mac_address: i.mac_address,
                       ip_addresses: i.ip_addresses,
                       description: i.description
                   }) AS interfaces
            """

            device_result = await neo_session.run(device_query)
            device_records = [record async for record in device_result]

            # Import devices
            hostname_to_device_id = {}

            for record in device_records:
                hostname = record["hostname"]
                if not hostname:
                    continue

                # Skip existing
                existing = await session.execute(select(Device).where(Device.hostname == hostname))
                if existing.scalar_one_or_none():
                    stats["skipped"].append(hostname)
                    continue

                # Map platform
                ng_platform = record.get("platform_name") or "Cisco IOS"
                snep_platform_name = PLATFORM_MAP.get(ng_platform, "cisco_ios")

                platform_q = await session.execute(select(Platform).where(Platform.name == snep_platform_name))
                platform = platform_q.scalar_one_or_none()
                if not platform:
                    stats["skipped"].append(f"{hostname} (no platform {ng_platform})")
                    continue

                # Get or create model
                model_slug = record.get("hardware_slug") or "generic"
                model_q = await session.execute(
                    select(DeviceModel).where(DeviceModel.platform_id == platform.id, DeviceModel.name == model_slug)
                )
                model = model_q.scalar_one_or_none()
                if not model:
                    model = DeviceModel(
                        platform_id=platform.id,
                        name=model_slug,
                        display_name=record.get("hardware_model") or model_slug,
                        software_version="17.06.05",
                        default_interface_pattern=[],
                    )
                    session.add(model)
                    await session.flush()

                mgmt_ip = record.get("management_ip")
                device = Device(
                    device_model_id=model.id,
                    hostname=hostname,
                    management_ip=mgmt_ip,
                    serial_number=record.get("serial_number") or f"NG-{hostname[:16].upper()}",
                    uptime_seconds=7_776_000,
                    uptime_reference=now,
                    admin_state="active",
                    tags={"source": "netgraphy", "role": record.get("role", "unknown")},
                )
                session.add(device)
                await session.flush()
                hostname_to_device_id[hostname] = device.id

                session.add(SNMPProfile(device_id=device.id, v2_enabled=True, v2_community="public"))
                await allocate_connection_mappings(session, device.id)

                # Interfaces
                ifaces = record.get("interfaces") or []
                for idx, iface_data in enumerate(ifaces, start=1):
                    iface_type = _map_ng_interface_type(iface_data.get("interface_type", "physical"))
                    ip_list = iface_data.get("ip_addresses") or []
                    ip_addr = ip_list[0] if ip_list else None

                    iface = Interface(
                        device_id=device.id,
                        name=iface_data["name"],
                        short_name=_abbreviate(iface_data["name"]),
                        if_index=idx,
                        interface_type=iface_type,
                        admin_status="up" if iface_data.get("enabled", True) else "down",
                        oper_status=_map_ng_oper_status(iface_data.get("oper_status", "up")),
                        speed_mbps=iface_data.get("speed_mbps") or 1000,
                        mtu=iface_data.get("mtu") or 1500,
                        mac_address=iface_data.get("mac_address") or f"aabb.cc00.{idx:04x}",
                        ip_address=ip_addr,
                        description=iface_data.get("description"),
                        last_state_change=now,
                        sort_order=idx,
                    )
                    session.add(iface)
                    await session.flush()

                    session.add(InterfaceCounter(
                        interface_id=iface.id,
                        rate_in_bps=300_000_000 if iface.speed_mbps >= 1000 else 10_000_000,
                        rate_out_bps=150_000_000 if iface.speed_mbps >= 1000 else 5_000_000,
                        rate_reference=now,
                        updated_at=now,
                    ))
                    stats["imported_interfaces"] += 1

                stats["imported_devices"] += 1

            # Query CONNECTED_TO relationships
            cable_query = """
            MATCH (i1:Interface)-[:CONNECTED_TO]->(i2:Interface)
            MATCH (d1:Device)-[:HAS_INTERFACE]->(i1)
            MATCH (d2:Device)-[:HAS_INTERFACE]->(i2)
            RETURN d1.hostname AS source_device,
                   i1.name AS source_interface,
                   d2.hostname AS target_device,
                   i2.name AS target_interface
            """
            cable_result = await neo_session.run(cable_query)
            cable_records = [record async for record in cable_result]

            for record in cable_records:
                lq = await session.execute(
                    select(Interface).join(Device)
                    .where(Device.hostname == record["source_device"], Interface.name == record["source_interface"])
                )
                rq = await session.execute(
                    select(Interface).join(Device)
                    .where(Device.hostname == record["target_device"], Interface.name == record["target_interface"])
                )
                local = lq.scalar_one_or_none()
                remote = rq.scalar_one_or_none()

                if local and remote and local.device_id != remote.device_id:
                    a_id, b_id = sorted([local.id, remote.id])
                    existing = await session.execute(
                        select(Link).where(Link.interface_a_id == a_id, Link.interface_b_id == b_id)
                    )
                    if not existing.scalar_one_or_none():
                        session.add(Link(
                            interface_a_id=a_id, interface_b_id=b_id,
                            link_type="physical", discovery_protocol="cdp", admin_state="up",
                        ))
                        stats["imported_links"] += 1

        await session.commit()

    finally:
        await driver.close()

    return stats


def _abbreviate(name: str) -> str:
    abbrevs = {"GigabitEthernet": "Gi", "TenGigabitEthernet": "Te", "Ethernet": "Et",
               "Loopback": "Lo", "Vlan": "Vl", "Management": "Ma"}
    for long, short in abbrevs.items():
        if name.startswith(long):
            return name.replace(long, short, 1)
    return name


def _map_ng_interface_type(ng_type: str) -> str:
    mapping = {"physical": "ethernet", "virtual": "vlan", "lag": "port_channel",
               "loopback": "loopback", "tunnel": "tunnel", "management": "management"}
    return mapping.get(ng_type, "ethernet")


def _map_ng_oper_status(status: str) -> str:
    mapping = {"up": "up", "down": "down", "testing": "down", "unknown": "down",
               "dormant": "dormant", "not_present": "notPresent", "lower_layer_down": "lowerLayerDown"}
    return mapping.get(status, "up")

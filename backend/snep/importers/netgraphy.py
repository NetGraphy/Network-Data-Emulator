"""NetGraphy importer — reads devices, interfaces, cables, hardware models, software versions, and vendors from Neo4j."""

import logging
from datetime import datetime, timezone

from neo4j import AsyncGraphDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snep.models import Device, DeviceModel, Interface, InterfaceCounter, Link, Platform, SNMPProfile, SoftwareVersion, Vendor
from snep.services.networking import allocate_connection_mappings

logger = logging.getLogger(__name__)

PLATFORM_MAP = {
    "Cisco IOS": "cisco_ios", "Cisco IOS-XE": "cisco_ios", "Cisco NX-OS": "cisco_ios",
    "Arista EOS": "arista_eos", "Juniper JunOS": "juniper_junos",
}


async def import_netgraphy(
    session: AsyncSession, neo4j_uri: str, neo4j_user: str, neo4j_password: str,
    hostname_filter: str | None = None,
) -> dict:
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    stats = {"imported_devices": 0, "imported_interfaces": 0, "imported_links": 0,
             "imported_vendors": 0, "imported_models": 0, "imported_versions": 0, "skipped": []}
    now = datetime.now(timezone.utc)

    try:
        async with driver.session() as neo_session:
            # --- Import Vendors ---
            vendor_result = await neo_session.run("MATCH (v:Vendor) RETURN v.name AS name, v.slug AS slug, v.url AS url")
            async for record in vendor_result:
                slug = record["slug"]
                if not slug:
                    continue
                existing = (await session.execute(select(Vendor).where(Vendor.slug == slug))).scalar_one_or_none()
                if not existing:
                    session.add(Vendor(name=record["name"] or slug, slug=slug, url=record.get("url")))
                    stats["imported_vendors"] += 1
            await session.flush()

            # --- Import Software Versions ---
            sv_result = await neo_session.run("""
                MATCH (sv:SoftwareVersion)
                OPTIONAL MATCH (d:Device)-[:RUNS_VERSION]->(sv)
                OPTIONAL MATCH (d)-[:RUNS_PLATFORM]->(p:Platform)
                RETURN sv.version_string AS version, sv.status AS status,
                       sv.major AS major, sv.minor AS minor, sv.patch AS patch,
                       collect(DISTINCT p.name) AS platforms
            """)
            async for record in sv_result:
                version_str = record["version"]
                if not version_str:
                    continue
                # Map to SNEP platform from first associated platform
                platform_names = record["platforms"] or []
                snep_platform_name = None
                for pn in platform_names:
                    if pn in PLATFORM_MAP:
                        snep_platform_name = PLATFORM_MAP[pn]
                        break
                if not snep_platform_name:
                    snep_platform_name = "cisco_ios"  # default

                platform = (await session.execute(select(Platform).where(Platform.name == snep_platform_name))).scalar_one_or_none()
                if not platform:
                    continue

                existing = (await session.execute(
                    select(SoftwareVersion).where(SoftwareVersion.platform_id == platform.id, SoftwareVersion.version_string == version_str)
                )).scalar_one_or_none()
                if not existing:
                    session.add(SoftwareVersion(
                        platform_id=platform.id, version_string=version_str,
                        major=record.get("major"), minor=record.get("minor"), patch=record.get("patch"),
                        status=record.get("status", "current"),
                    ))
                    stats["imported_versions"] += 1
            await session.flush()

            # --- Import Hardware Models ---
            model_result = await neo_session.run("""
                MATCH (hm:HardwareModel)
                OPTIONAL MATCH (hm)-[:MANUFACTURED_BY]->(v:Vendor)
                OPTIONAL MATCH (d:Device)-[:HAS_MODEL]->(hm)
                OPTIONAL MATCH (d)-[:RUNS_PLATFORM]->(p:Platform)
                RETURN hm.model AS model, hm.slug AS slug, hm.part_number AS part_number,
                       hm.u_height AS u_height, hm.interface_count AS interface_count,
                       v.slug AS vendor_slug,
                       collect(DISTINCT p.name) AS platforms
            """)
            async for record in model_result:
                model_slug = record["slug"]
                if not model_slug:
                    continue

                # Resolve platform
                platform_names = record["platforms"] or []
                snep_platform_name = None
                for pn in platform_names:
                    if pn in PLATFORM_MAP:
                        snep_platform_name = PLATFORM_MAP[pn]
                        break
                if not snep_platform_name:
                    snep_platform_name = "cisco_ios"

                platform = (await session.execute(select(Platform).where(Platform.name == snep_platform_name))).scalar_one_or_none()
                if not platform:
                    continue

                existing = (await session.execute(
                    select(DeviceModel).where(DeviceModel.platform_id == platform.id, DeviceModel.name == model_slug)
                )).scalar_one_or_none()
                if existing:
                    continue

                vendor = None
                if record.get("vendor_slug"):
                    vendor = (await session.execute(select(Vendor).where(Vendor.slug == record["vendor_slug"]))).scalar_one_or_none()

                session.add(DeviceModel(
                    platform_id=platform.id, vendor_id=vendor.id if vendor else None,
                    name=model_slug, slug=model_slug,
                    display_name=record.get("model", model_slug),
                    part_number=record.get("part_number"),
                    u_height=record.get("u_height", 1) or 1,
                    interface_count=record.get("interface_count"),
                    software_version="imported",
                    default_interface_pattern=[],
                ))
                stats["imported_models"] += 1
            await session.flush()

            # --- Import Devices with Interfaces ---
            device_query = """
            MATCH (d:Device)-[:HAS_INTERFACE]->(i:Interface)
            OPTIONAL MATCH (d)-[:RUNS_PLATFORM]->(p:Platform)
            OPTIONAL MATCH (d)-[:HAS_MODEL]->(hm:HardwareModel)
            OPTIONAL MATCH (d)-[:RUNS_VERSION]->(sv:SoftwareVersion)
            """
            if hostname_filter:
                device_query += f" WHERE d.hostname CONTAINS '{hostname_filter}'"
            device_query += """
            RETURN d.hostname AS hostname, d.management_ip AS management_ip,
                   d.serial_number AS serial_number, d.status AS status, d.role AS role,
                   p.name AS platform_name, hm.slug AS model_slug,
                   sv.version_string AS software_version,
                   collect({
                       name: i.name, interface_type: i.interface_type,
                       enabled: i.enabled, oper_status: i.oper_status,
                       speed_mbps: i.speed_mbps, mtu: i.mtu,
                       mac_address: i.mac_address, ip_addresses: i.ip_addresses,
                       description: i.description
                   }) AS interfaces
            """
            device_result = await neo_session.run(device_query)
            device_records = [record async for record in device_result]

            for record in device_records:
                hostname = record["hostname"]
                if not hostname:
                    continue
                existing = (await session.execute(select(Device).where(Device.hostname == hostname))).scalar_one_or_none()
                if existing:
                    stats["skipped"].append(hostname)
                    continue

                ng_platform = record.get("platform_name") or "Cisco IOS"
                snep_platform_name = PLATFORM_MAP.get(ng_platform, "cisco_ios")
                platform = (await session.execute(select(Platform).where(Platform.name == snep_platform_name))).scalar_one_or_none()
                if not platform:
                    stats["skipped"].append(f"{hostname} (no platform {ng_platform})")
                    continue

                # Resolve model
                model_slug = record.get("model_slug") or "generic"
                model = (await session.execute(
                    select(DeviceModel).where(DeviceModel.platform_id == platform.id, DeviceModel.name == model_slug)
                )).scalar_one_or_none()
                if not model:
                    model = DeviceModel(
                        platform_id=platform.id, name=model_slug, slug=model_slug,
                        display_name=model_slug, software_version="imported",
                        default_interface_pattern=[],
                    )
                    session.add(model)
                    await session.flush()

                # Resolve software version
                sv_id = None
                sv_str = record.get("software_version")
                if sv_str:
                    sv = (await session.execute(
                        select(SoftwareVersion).where(SoftwareVersion.platform_id == platform.id, SoftwareVersion.version_string == sv_str)
                    )).scalar_one_or_none()
                    if sv:
                        sv_id = sv.id

                device = Device(
                    device_model_id=model.id, software_version_id=sv_id,
                    hostname=hostname, management_ip=record.get("management_ip"),
                    serial_number=record.get("serial_number") or f"NG-{hostname[:16].upper()}",
                    software_version=sv_str,
                    uptime_seconds=7_776_000, uptime_reference=now, admin_state="active",
                    tags={"source": "netgraphy", "role": record.get("role", "unknown")},
                )
                session.add(device)
                await session.flush()
                session.add(SNMPProfile(device_id=device.id, v2_enabled=True, v2_community="public"))
                await allocate_connection_mappings(session, device.id)

                for idx, iface_data in enumerate(record.get("interfaces") or [], start=1):
                    ip_list = iface_data.get("ip_addresses") or []
                    iface = Interface(
                        device_id=device.id, name=iface_data["name"],
                        short_name=_abbreviate(iface_data["name"]),
                        if_index=idx,
                        interface_type=_map_type(iface_data.get("interface_type", "physical")),
                        admin_status="up" if iface_data.get("enabled", True) else "down",
                        oper_status=_map_oper(iface_data.get("oper_status", "up")),
                        speed_mbps=iface_data.get("speed_mbps") or 1000,
                        mtu=iface_data.get("mtu") or 1500,
                        mac_address=iface_data.get("mac_address") or f"aabb.cc00.{idx:04x}",
                        ip_address=ip_list[0] if ip_list else None,
                        description=iface_data.get("description"),
                        last_state_change=now, sort_order=idx,
                    )
                    session.add(iface)
                    await session.flush()
                    session.add(InterfaceCounter(
                        interface_id=iface.id,
                        rate_in_bps=300_000_000 if iface.speed_mbps >= 1000 else 10_000_000,
                        rate_out_bps=150_000_000 if iface.speed_mbps >= 1000 else 5_000_000,
                        rate_reference=now, updated_at=now,
                    ))
                    stats["imported_interfaces"] += 1

                stats["imported_devices"] += 1

            # --- Import Links ---
            cable_result = await neo_session.run("""
                MATCH (i1:Interface)-[:CONNECTED_TO]->(i2:Interface)
                MATCH (d1:Device)-[:HAS_INTERFACE]->(i1)
                MATCH (d2:Device)-[:HAS_INTERFACE]->(i2)
                RETURN d1.hostname AS src_host, i1.name AS src_iface,
                       d2.hostname AS tgt_host, i2.name AS tgt_iface
            """)
            async for record in cable_result:
                lq = (await session.execute(select(Interface).join(Device).where(Device.hostname == record["src_host"], Interface.name == record["src_iface"]))).scalar_one_or_none()
                rq = (await session.execute(select(Interface).join(Device).where(Device.hostname == record["tgt_host"], Interface.name == record["tgt_iface"]))).scalar_one_or_none()
                if lq and rq and lq.device_id != rq.device_id:
                    a_id, b_id = sorted([lq.id, rq.id])
                    if not (await session.execute(select(Link).where(Link.interface_a_id == a_id, Link.interface_b_id == b_id))).scalar_one_or_none():
                        session.add(Link(interface_a_id=a_id, interface_b_id=b_id, link_type="physical", discovery_protocol="cdp", admin_state="up"))
                        stats["imported_links"] += 1

        await session.commit()
    finally:
        await driver.close()

    return stats


def _abbreviate(name: str) -> str:
    for long, short in {"GigabitEthernet": "Gi", "TenGigabitEthernet": "Te", "Ethernet": "Et",
                        "Loopback": "Lo", "Vlan": "Vl", "Management": "Ma"}.items():
        if name.startswith(long):
            return name.replace(long, short, 1)
    return name


def _map_type(t: str) -> str:
    return {"physical": "ethernet", "virtual": "vlan", "lag": "port_channel",
            "loopback": "loopback", "tunnel": "tunnel", "management": "management"}.get(t, "ethernet")


def _map_oper(s: str) -> str:
    return {"up": "up", "down": "down", "dormant": "dormant",
            "not_present": "notPresent", "lower_layer_down": "lowerLayerDown"}.get(s, "up")

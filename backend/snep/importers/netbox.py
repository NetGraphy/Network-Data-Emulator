"""NetBox importer — pulls devices, interfaces, cables, hardware models, software versions, and vendors via GraphQL."""

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snep.models import Device, DeviceModel, Interface, InterfaceCounter, Link, Platform, SNMPProfile, SoftwareVersion, Vendor
from snep.services.networking import allocate_connection_mappings

logger = logging.getLogger(__name__)

NETBOX_GRAPHQL_QUERY = """
query ($site: [String], $role: [String], $tag: [String]) {
  device_list(
    filters: {
      site: $site
      role: $role
      tag: $tag
    }
  ) {
    name
    serial
    status
    primary_ip4 { address }
    platform { slug name }
    device_type {
      model
      slug
      part_number
      u_height
      manufacturer { name slug }
    }
    config_context
    local_context_data
    interfaces {
      name
      type
      enabled
      mac_address
      mtu
      speed
      description
      ip_addresses { address }
      connected_endpoints {
        ... on InterfaceType {
          name
          device { name }
        }
      }
    }
  }
  software_version_list {
    version
    status
    platform { slug }
    release_date
    end_of_support
  }
}
"""

PLATFORM_MAP = {
    "cisco_ios": "cisco_ios", "ios": "cisco_ios", "ios-xe": "cisco_ios",
    "cisco_iosxe": "cisco_ios", "arista_eos": "arista_eos", "eos": "arista_eos",
    "juniper_junos": "juniper_junos", "junos": "juniper_junos",
    "cisco_nxos": "cisco_ios",
}


async def import_netbox(
    session: AsyncSession, url: str, token: str,
    site_filter: str | None = None, role_filter: str | None = None, tag_filter: str | None = None,
) -> dict:
    graphql_url = f"{url.rstrip('/')}/graphql/"
    variables = {}
    if site_filter:
        variables["site"] = [site_filter]
    if role_filter:
        variables["role"] = [role_filter]
    if tag_filter:
        variables["tag"] = [tag_filter]

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            graphql_url,
            json={"query": NETBOX_GRAPHQL_QUERY, "variables": variables},
            headers={"Authorization": f"Token {token}", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    if "errors" in data:
        raise ValueError(f"GraphQL errors: {data['errors']}")

    devices_data = data.get("data", {}).get("device_list", [])
    versions_data = data.get("data", {}).get("software_version_list", [])

    stats = {"imported_devices": 0, "imported_interfaces": 0, "imported_links": 0,
             "imported_vendors": 0, "imported_models": 0, "imported_versions": 0, "skipped": []}
    cable_pairs = []
    now = datetime.now(timezone.utc)

    # Import software versions
    for sv_data in versions_data or []:
        platform_slug = sv_data.get("platform", {}).get("slug", "") if sv_data.get("platform") else ""
        snep_platform_name = PLATFORM_MAP.get(platform_slug)
        if not snep_platform_name:
            continue
        platform = (await session.execute(select(Platform).where(Platform.name == snep_platform_name))).scalar_one_or_none()
        if not platform:
            continue

        version_str = sv_data.get("version", "")
        existing_sv = (await session.execute(
            select(SoftwareVersion).where(SoftwareVersion.platform_id == platform.id, SoftwareVersion.version_string == version_str)
        )).scalar_one_or_none()
        if not existing_sv:
            sv = SoftwareVersion(platform_id=platform.id, version_string=version_str, status=sv_data.get("status", "current"))
            session.add(sv)
            stats["imported_versions"] += 1

    await session.flush()

    for dev_data in devices_data:
        hostname = dev_data["name"]
        existing = (await session.execute(select(Device).where(Device.hostname == hostname))).scalar_one_or_none()
        if existing:
            stats["skipped"].append(hostname)
            continue

        # Resolve platform
        platform_slug = dev_data.get("platform", {}).get("slug", "cisco_ios") if dev_data.get("platform") else "cisco_ios"
        snep_platform = PLATFORM_MAP.get(platform_slug, "cisco_ios")
        platform = (await session.execute(select(Platform).where(Platform.name == snep_platform))).scalar_one_or_none()
        if not platform:
            stats["skipped"].append(f"{hostname} (unknown platform)")
            continue

        # Get or create vendor
        dt = dev_data.get("device_type", {})
        manufacturer = dt.get("manufacturer", {})
        vendor = None
        if manufacturer and manufacturer.get("slug"):
            vendor = (await session.execute(select(Vendor).where(Vendor.slug == manufacturer["slug"]))).scalar_one_or_none()
            if not vendor:
                vendor = Vendor(name=manufacturer.get("name", manufacturer["slug"]), slug=manufacturer["slug"])
                session.add(vendor)
                await session.flush()
                stats["imported_vendors"] += 1

        # Get or create device model
        model_slug = dt.get("slug", "generic")
        model = (await session.execute(
            select(DeviceModel).where(DeviceModel.platform_id == platform.id, DeviceModel.name == model_slug)
        )).scalar_one_or_none()
        if not model:
            model = DeviceModel(
                platform_id=platform.id, vendor_id=vendor.id if vendor else None,
                name=model_slug, slug=model_slug,
                display_name=dt.get("model", model_slug),
                part_number=dt.get("part_number"),
                u_height=dt.get("u_height", 1),
                software_version="unknown",
                default_interface_pattern=[],
            )
            session.add(model)
            await session.flush()
            stats["imported_models"] += 1

        # Create device
        mgmt_ip = dev_data["primary_ip4"]["address"].split("/")[0] if dev_data.get("primary_ip4") else None
        device = Device(
            device_model_id=model.id, hostname=hostname, management_ip=mgmt_ip,
            serial_number=dev_data.get("serial") or f"IMPORT-{hostname[:16].upper()}",
            uptime_seconds=7_776_000, uptime_reference=now, admin_state="active",
            tags={"source": "netbox", "site": site_filter or "all"},
        )
        session.add(device)
        await session.flush()
        session.add(SNMPProfile(device_id=device.id, v2_enabled=True, v2_community="public"))
        await allocate_connection_mappings(session, device.id)

        # Interfaces
        for idx, iface_data in enumerate(dev_data.get("interfaces", []), start=1):
            iface = Interface(
                device_id=device.id, name=iface_data["name"],
                short_name=_abbreviate(iface_data["name"]),
                if_index=idx, interface_type=_map_interface_type(iface_data.get("type", "")),
                admin_status="up" if iface_data.get("enabled", True) else "down",
                oper_status="up" if iface_data.get("enabled", True) else "down",
                speed_mbps=iface_data.get("speed", 1000) or 1000,
                mtu=iface_data.get("mtu") or 1500,
                mac_address=iface_data.get("mac_address") or f"aabb.cc00.{idx:04x}",
                ip_address=iface_data["ip_addresses"][0]["address"] if iface_data.get("ip_addresses") else None,
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

            for endpoint in iface_data.get("connected_endpoints", []) or []:
                if endpoint and endpoint.get("device") and endpoint.get("name"):
                    cable_pairs.append((hostname, iface_data["name"], endpoint["device"]["name"], endpoint["name"]))

        stats["imported_devices"] += 1

    # Links
    for lh, li, rh, ri in cable_pairs:
        lq = (await session.execute(select(Interface).join(Device).where(Device.hostname == lh, Interface.name == li))).scalar_one_or_none()
        rq = (await session.execute(select(Interface).join(Device).where(Device.hostname == rh, Interface.name == ri))).scalar_one_or_none()
        if lq and rq and lq.device_id != rq.device_id:
            a_id, b_id = sorted([lq.id, rq.id])
            if not (await session.execute(select(Link).where(Link.interface_a_id == a_id, Link.interface_b_id == b_id))).scalar_one_or_none():
                session.add(Link(interface_a_id=a_id, interface_b_id=b_id, link_type="physical", discovery_protocol="cdp", admin_state="up"))
                stats["imported_links"] += 1

    await session.commit()
    return stats


def _abbreviate(name: str) -> str:
    for long, short in {"GigabitEthernet": "Gi", "TenGigabitEthernet": "Te", "FastEthernet": "Fa",
                        "Ethernet": "Et", "Loopback": "Lo", "Vlan": "Vl", "Management": "Ma"}.items():
        if name.startswith(long):
            return name.replace(long, short, 1)
    return name


def _map_interface_type(nb_type: str) -> str:
    t = nb_type.lower()
    if "virtual" in t or "lag" in t:
        return "port_channel"
    if "loopback" in t:
        return "loopback"
    if "vlan" in t:
        return "vlan"
    return "ethernet"

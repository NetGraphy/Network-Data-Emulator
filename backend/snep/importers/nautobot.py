"""Nautobot importer — pulls devices via GraphQL (compatible with NetBox importer pattern)."""

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from snep.importers.netbox import (
    PLATFORM_MAP,
    _abbreviate,
    _map_interface_type,
)
from snep.models import Device, DeviceModel, Interface, InterfaceCounter, Link, Platform, SNMPProfile
from snep.services.networking import allocate_connection_mappings
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Nautobot GraphQL is slightly different from NetBox
NAUTOBOT_GRAPHQL_QUERY = """
query ($site: [String], $role: [String], $tag: [String]) {
  devices(
    site: $site
    role: $role
    tag: $tag
  ) {
    name
    serial
    status
    primary_ip4 { address }
    platform { slug name }
    device_type {
      model
      slug
      manufacturer { name slug }
    }
    interfaces {
      name
      type
      enabled
      mac_address
      mtu
      description
      ip_addresses { address }
      connected_endpoint {
        ... on InterfaceType {
          name
          device { name }
        }
      }
    }
  }
}
"""


async def import_nautobot(
    session: AsyncSession,
    url: str,
    token: str,
    site_filter: str | None = None,
    role_filter: str | None = None,
    tag_filter: str | None = None,
) -> dict:
    """Import devices from Nautobot GraphQL API."""
    graphql_url = f"{url.rstrip('/')}/api/graphql/"

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
            json={"query": NAUTOBOT_GRAPHQL_QUERY, "variables": variables},
            headers={"Authorization": f"Token {token}", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    if "errors" in data:
        raise ValueError(f"GraphQL errors: {data['errors']}")

    devices_data = data.get("data", {}).get("devices", [])
    if not devices_data:
        return {"imported_devices": 0, "imported_interfaces": 0, "imported_links": 0}

    stats = {"imported_devices": 0, "imported_interfaces": 0, "imported_links": 0, "skipped": []}
    cable_pairs = []
    now = datetime.now(timezone.utc)

    for dev_data in devices_data:
        hostname = dev_data["name"]
        existing = await session.execute(select(Device).where(Device.hostname == hostname))
        if existing.scalar_one_or_none():
            stats["skipped"].append(hostname)
            continue

        platform_slug = dev_data.get("platform", {}).get("slug", "cisco_ios") if dev_data.get("platform") else "cisco_ios"
        snep_platform = PLATFORM_MAP.get(platform_slug, "cisco_ios")

        platform = await session.execute(select(Platform).where(Platform.name == snep_platform))
        platform = platform.scalar_one_or_none()
        if not platform:
            stats["skipped"].append(f"{hostname} (unknown platform)")
            continue

        dt = dev_data.get("device_type", {})
        model_name = dt.get("slug", "generic")
        model = await session.execute(
            select(DeviceModel).where(DeviceModel.platform_id == platform.id, DeviceModel.name == model_name)
        )
        model = model.scalar_one_or_none()
        if not model:
            model = DeviceModel(
                platform_id=platform.id, name=model_name,
                display_name=dt.get("model", model_name),
                software_version="17.06.05", default_interface_pattern=[],
            )
            session.add(model)
            await session.flush()

        mgmt_ip = None
        if dev_data.get("primary_ip4"):
            mgmt_ip = dev_data["primary_ip4"]["address"].split("/")[0]

        device = Device(
            device_model_id=model.id, hostname=hostname, management_ip=mgmt_ip,
            serial_number=dev_data.get("serial") or f"IMPORT-{hostname[:16].upper()}",
            uptime_seconds=7_776_000, uptime_reference=now, admin_state="active",
            tags={"source": "nautobot"},
        )
        session.add(device)
        await session.flush()
        session.add(SNMPProfile(device_id=device.id, v2_enabled=True, v2_community="public"))
        await allocate_connection_mappings(session, device.id)

        for idx, iface_data in enumerate(dev_data.get("interfaces", []), start=1):
            iface = Interface(
                device_id=device.id, name=iface_data["name"],
                short_name=_abbreviate(iface_data["name"]),
                if_index=idx, interface_type=_map_interface_type(iface_data.get("type", "")),
                admin_status="up" if iface_data.get("enabled", True) else "down",
                oper_status="up" if iface_data.get("enabled", True) else "down",
                speed_mbps=1000, mtu=iface_data.get("mtu") or 1500,
                mac_address=iface_data.get("mac_address") or f"aabb.cc00.{idx:04x}",
                ip_address=iface_data["ip_addresses"][0]["address"] if iface_data.get("ip_addresses") else None,
                description=iface_data.get("description"),
                last_state_change=now, sort_order=idx,
            )
            session.add(iface)
            await session.flush()
            session.add(InterfaceCounter(
                interface_id=iface.id, rate_in_bps=300_000_000, rate_out_bps=150_000_000,
                rate_reference=now, updated_at=now,
            ))
            stats["imported_interfaces"] += 1

            ep = iface_data.get("connected_endpoint")
            if ep and ep.get("device") and ep.get("name"):
                cable_pairs.append((hostname, iface_data["name"], ep["device"]["name"], ep["name"]))

        stats["imported_devices"] += 1

    # Links
    for lh, li, rh, ri in cable_pairs:
        lq = await session.execute(select(Interface).join(Device).where(Device.hostname == lh, Interface.name == li))
        rq = await session.execute(select(Interface).join(Device).where(Device.hostname == rh, Interface.name == ri))
        local = lq.scalar_one_or_none()
        remote = rq.scalar_one_or_none()
        if local and remote and local.device_id != remote.device_id:
            a_id, b_id = sorted([local.id, remote.id])
            existing_link = await session.execute(select(Link).where(Link.interface_a_id == a_id, Link.interface_b_id == b_id))
            if not existing_link.scalar_one_or_none():
                session.add(Link(interface_a_id=a_id, interface_b_id=b_id, link_type="physical", discovery_protocol="lldp", admin_state="up"))
                stats["imported_links"] += 1

    await session.commit()
    return stats

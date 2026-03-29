"""Import engine — executes queries against data sources and maps results to SNEP entities via Jinja2.

Flow:
1. Execute query against data source (GraphQL or Cypher)
2. Extract result array using result_path (e.g., "data.device_list")
3. For each item, render device_template/interface_template/link_template via Jinja2
4. Parse rendered YAML into dicts
5. Create SNEP entities from dicts
"""

import json
import logging
from datetime import datetime, timezone

import httpx
import yaml
from jinja2 import Environment

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snep.models import (
    Device, DeviceModel, Interface, InterfaceCounter, Link,
    Platform, SNMPProfile, SoftwareVersion, Vendor,
)
from snep.models.data_source import DataSource
from snep.models.import_mapping import ImportMapping
from snep.services.networking import allocate_connection_mappings

logger = logging.getLogger(__name__)

# Mapping-specific Jinja2 env (reuses custom filters from rendering)
def _get_mapping_env():
    from snep.services.rendering import _env
    return _env


# --- Query Execution ---

async def execute_query(source: DataSource, query: str) -> dict:
    """Execute a query against a data source and return raw results."""
    if source.source_type in ("netbox", "nautobot"):
        return await _execute_graphql(source, query)
    elif source.source_type == "netgraphy":
        return await _execute_cypher(source, query)
    else:
        return {"error": f"Unknown source type: {source.source_type}"}


async def _execute_graphql(source: DataSource, query: str) -> dict:
    url = f"{source.url.rstrip('/')}{source.graphql_path}"
    headers = {"Content-Type": "application/json"}
    if source.auth_token:
        headers["Authorization"] = f"Token {source.auth_token}"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json={"query": query}, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def _execute_cypher(source: DataSource, query: str) -> dict:
    url = f"{source.url.rstrip('/')}/api/v1/query/cypher"
    headers = {"Content-Type": "application/json"}
    if source.auth_token:
        headers["Authorization"] = f"Bearer {source.auth_token}"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json={"query": query, "parameters": {}}, headers=headers)
        resp.raise_for_status()
        return resp.json()


# --- Result Extraction ---

def extract_results(raw_response: dict, result_path: str) -> list[dict]:
    """Navigate JSON path to find the result array."""
    if not result_path:
        # Try common paths
        if isinstance(raw_response, list):
            return raw_response
        if "data" in raw_response:
            data = raw_response["data"]
            if isinstance(data, list):
                return data
            # GraphQL: find first list in data
            for key, val in data.items():
                if isinstance(val, list):
                    return val
            # Cypher: check rows
            if "rows" in data:
                return data["rows"]
        return [raw_response]

    # Navigate dot-separated path
    current = raw_response
    for part in result_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return []

    return current if isinstance(current, list) else [current]


# --- Mapping Application ---

def apply_device_mapping(items: list[dict], device_template: str, source_name: str = "") -> list[dict]:
    """Apply Jinja2 device mapping template to each result item."""
    env = _get_mapping_env()
    results = []

    for item in items:
        try:
            tmpl = env.from_string(device_template)
            rendered = tmpl.render(item=item, _source_name=source_name)
            parsed = yaml.safe_load(rendered)
            if parsed and isinstance(parsed, dict):
                results.append(parsed)
        except Exception as e:
            logger.warning(f"Device mapping failed for item: {e}")
            results.append({"_error": str(e), "_item": item})

    return results


def apply_interface_mapping(item: dict, interface_template: str) -> list[dict]:
    """Apply Jinja2 interface mapping to a single device's data."""
    env = _get_mapping_env()
    try:
        tmpl = env.from_string(interface_template)
        rendered = tmpl.render(item=item)
        parsed = yaml.safe_load(rendered)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            return [parsed]
    except Exception as e:
        logger.warning(f"Interface mapping failed: {e}")
    return []


# --- Entity Creation ---

PLATFORM_MAP = {
    "cisco_ios": "cisco_ios", "ios": "cisco_ios", "ios-xe": "cisco_ios",
    "cisco_iosxe": "cisco_ios", "arista_eos": "arista_eos", "eos": "arista_eos",
    "juniper_junos": "juniper_junos", "junos": "juniper_junos",
    "Cisco IOS": "cisco_ios", "Cisco IOS-XE": "cisco_ios", "Arista EOS": "arista_eos",
}


async def create_entities_from_mapping(
    session: AsyncSession,
    device_data_list: list[dict],
    source_name: str = "",
) -> dict:
    """Create SNEP entities from mapped device data."""
    now = datetime.now(timezone.utc)
    stats = {"imported_devices": 0, "imported_interfaces": 0, "imported_links": 0, "skipped": [], "errors": []}

    for dd in device_data_list:
        if "_error" in dd:
            stats["errors"].append(dd["_error"])
            continue

        hostname = dd.get("hostname", "").strip()
        if not hostname:
            stats["errors"].append("Missing hostname in mapped data")
            continue

        # Skip existing
        existing = (await session.execute(select(Device).where(Device.hostname == hostname))).scalar_one_or_none()
        if existing:
            stats["skipped"].append(hostname)
            continue

        # Resolve platform
        platform_slug = dd.get("platform", "cisco_ios")
        snep_platform = PLATFORM_MAP.get(platform_slug, platform_slug)
        platform = (await session.execute(select(Platform).where(Platform.name == snep_platform))).scalar_one_or_none()
        if not platform:
            stats["skipped"].append(f"{hostname} (unknown platform: {platform_slug})")
            continue

        # Get or create vendor
        vendor = None
        vendor_slug = dd.get("vendor", "")
        if vendor_slug:
            vendor = (await session.execute(select(Vendor).where(Vendor.slug == vendor_slug))).scalar_one_or_none()
            if not vendor:
                vendor = Vendor(name=vendor_slug, slug=vendor_slug)
                session.add(vendor)
                await session.flush()

        # Get or create model
        model_name = dd.get("model_name", "generic")
        model = (await session.execute(
            select(DeviceModel).where(DeviceModel.platform_id == platform.id, DeviceModel.name == model_name)
        )).scalar_one_or_none()
        if not model:
            model = DeviceModel(
                platform_id=platform.id, vendor_id=vendor.id if vendor else None,
                name=model_name, slug=model_name,
                display_name=dd.get("model_display", model_name),
                software_version="imported", default_interface_pattern=[],
            )
            session.add(model)
            await session.flush()

        # Create device
        device = Device(
            device_model_id=model.id, hostname=hostname,
            management_ip=dd.get("management_ip") or None,
            serial_number=dd.get("serial_number", f"IMPORT-{hostname[:16].upper()}"),
            uptime_seconds=7_776_000, uptime_reference=now, admin_state="active",
            tags=dd.get("tags", {"source": source_name}),
        )
        session.add(device)
        await session.flush()

        session.add(SNMPProfile(device_id=device.id, v2_enabled=True, v2_community="public"))
        await allocate_connection_mappings(session, device.id)

        # Create interfaces
        for idx, iface_data in enumerate(dd.get("interfaces", []), start=1):
            iface_name = iface_data.get("name", f"Interface{idx}")
            iface = Interface(
                device_id=device.id, name=iface_name,
                short_name=_abbreviate(iface_name),
                if_index=idx,
                interface_type=iface_data.get("interface_type", "ethernet"),
                admin_status="up" if iface_data.get("enabled", True) else "down",
                oper_status="up" if iface_data.get("enabled", True) else "down",
                speed_mbps=iface_data.get("speed_mbps", 1000),
                mtu=iface_data.get("mtu", 1500),
                mac_address=iface_data.get("mac_address", f"aabb.cc00.{idx:04x}"),
                ip_address=iface_data.get("ip_address"),
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

    await session.commit()
    return stats


def _abbreviate(name: str) -> str:
    for long, short in {"GigabitEthernet": "Gi", "TenGigabitEthernet": "Te",
                        "Ethernet": "Et", "Loopback": "Lo", "Vlan": "Vl", "Management": "Ma"}.items():
        if name.startswith(long):
            return name.replace(long, short, 1)
    return name

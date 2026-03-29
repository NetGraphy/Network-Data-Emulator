"""Seed default import mappings for NetBox, Nautobot, and NetGraphy."""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from snep.db import async_session_factory
from snep.models.import_mapping import ImportMapping

NETBOX_QUERY = """query ($site: [String]) {
  device_list(filters: { site: $site }) {
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
}"""

NETBOX_DEVICE_TEMPLATE = """hostname: {{ item.name }}
serial_number: {{ item.serial | default("IMPORT-" + item.name[:16] | upper) }}
management_ip: {{ item.primary_ip4.address | ip_only if item.primary_ip4 else "" }}
platform: {{ item.platform.slug if item.platform else "cisco_ios" }}
model_name: {{ item.device_type.slug if item.device_type else "generic" }}
model_display: {{ item.device_type.model if item.device_type else "Generic" }}
vendor: {{ item.device_type.manufacturer.slug if item.device_type and item.device_type.manufacturer else "" }}
tags:
  source: {{ _source_name }}
interfaces:
{% for iface in item.interfaces | default([]) %}
  - name: {{ iface.name }}
    interface_type: {{ "loopback" if "loopback" in (iface.type | default("") | lower) else "vlan" if "vlan" in (iface.type | default("") | lower) else "ethernet" }}
    enabled: {{ iface.enabled | default(true) }}
    mac_address: {{ iface.mac_address | default("") }}
    mtu: {{ iface.mtu | default(1500) }}
    speed_mbps: {{ iface.speed | default(1000) }}
    ip_address: {{ iface.ip_addresses[0].address if iface.ip_addresses else "" }}
    description: {{ iface.description | default("") }}
{% endfor %}"""

NAUTOBOT_QUERY = """query ($site: [String]) {
  devices(site: $site) {
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
}"""

NETGRAPHY_QUERY = """MATCH (d:Device)-[:HAS_INTERFACE]->(i:Interface)
OPTIONAL MATCH (d)-[:RUNS_PLATFORM]->(p:Platform)
OPTIONAL MATCH (d)-[:HAS_MODEL]->(hm:HardwareModel)
OPTIONAL MATCH (d)-[:RUNS_VERSION]->(sv:SoftwareVersion)
RETURN d.hostname AS hostname,
       d.management_ip AS management_ip,
       d.serial_number AS serial_number,
       d.role AS role,
       p.name AS platform_name,
       hm.slug AS model_slug,
       hm.model AS model_name,
       sv.version_string AS software_version,
       collect({
           name: i.name,
           interface_type: i.interface_type,
           enabled: i.enabled,
           oper_status: i.oper_status,
           speed_mbps: i.speed_mbps,
           mtu: i.mtu,
           mac_address: i.mac_address,
           description: i.description
       }) AS interfaces"""

NETGRAPHY_DEVICE_TEMPLATE = """hostname: {{ item.hostname }}
serial_number: {{ item.serial_number | default("NG-" + item.hostname[:16] | upper) }}
management_ip: {{ item.management_ip | default("") }}
platform: {{ item.platform_name | default("cisco_ios") }}
model_name: {{ item.model_slug | default("generic") }}
model_display: {{ item.model_name | default(item.model_slug | default("Generic")) }}
tags:
  source: {{ _source_name }}
  role: {{ item.role | default("unknown") }}
interfaces:
{% for iface in item.interfaces | default([]) %}
  - name: {{ iface.name }}
    interface_type: {{ iface.interface_type | default("ethernet") }}
    enabled: {{ iface.enabled | default(true) }}
    mac_address: {{ iface.mac_address | default("") }}
    mtu: {{ iface.mtu | default(1500) }}
    speed_mbps: {{ iface.speed_mbps | default(1000) }}
    description: {{ iface.description | default("") }}
{% endfor %}"""

MAPPINGS = [
    {
        "name": "NetBox Standard Import",
        "source_type": "netbox",
        "description": "Import devices, interfaces, and connections from NetBox via GraphQL. Includes manufacturer/model mapping.",
        "query": NETBOX_QUERY,
        "result_path": "data.device_list",
        "device_template": NETBOX_DEVICE_TEMPLATE,
        "interface_template": "",
        "link_template": "",
    },
    {
        "name": "Nautobot Standard Import",
        "source_type": "nautobot",
        "description": "Import devices and interfaces from Nautobot via GraphQL.",
        "query": NAUTOBOT_QUERY,
        "result_path": "data.devices",
        "device_template": NETBOX_DEVICE_TEMPLATE,  # Same template works, different query
        "interface_template": "",
        "link_template": "",
    },
    {
        "name": "NetGraphy Standard Import",
        "source_type": "netgraphy",
        "description": "Import devices and interfaces from NetGraphy via Cypher. Maps HardwareModel, Platform, SoftwareVersion.",
        "query": NETGRAPHY_QUERY,
        "result_path": "data.rows",
        "device_template": NETGRAPHY_DEVICE_TEMPLATE,
        "interface_template": "",
        "link_template": "",
    },
]


async def seed_mappings(session: AsyncSession) -> None:
    result = await session.execute(select(ImportMapping).where(ImportMapping.is_builtin == True).limit(1))
    if result.scalar_one_or_none():
        print("Import mappings already seeded, skipping.")
        return

    for m in MAPPINGS:
        session.add(ImportMapping(**m, is_builtin=True, is_active=True))

    await session.commit()
    print(f"Seeded {len(MAPPINGS)} import mappings.")


async def main():
    async with async_session_factory() as session:
        await seed_mappings(session)


if __name__ == "__main__":
    asyncio.run(main())

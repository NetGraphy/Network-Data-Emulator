"""Template variable resolver — substitutes {{ device.hostname }}, {{ interface.name }}, etc.

Used by:
- Custom syslog messages in scenarios
- CLI output modeling (annotation field mapping)
- Any user-facing text that references device/interface state

Variables use dot notation: {{ device.hostname }}, {{ interface.GigabitEthernet1/0/1.ip_address }}
"""

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from snep.models import Device, DeviceModel, Interface, InterfaceCounter, Link, SNMPProfile

# Pattern to match {{ variable.path }} in templates
VAR_PATTERN = re.compile(r"\{\{\s*([\w./]+)\s*\}\}")


# All available variables with descriptions and examples
VARIABLE_CATALOG = [
    # Device variables
    {"path": "device.hostname", "description": "Device hostname", "example": "core-rtr-01", "category": "Device"},
    {"path": "device.management_ip", "description": "Management IP address", "example": "10.1.1.1", "category": "Device"},
    {"path": "device.serial_number", "description": "Serial number", "example": "FCW2145L0RN", "category": "Device"},
    {"path": "device.software_version", "description": "Software version", "example": "17.06.05", "category": "Device"},
    {"path": "device.admin_state", "description": "Admin state", "example": "active", "category": "Device"},
    {"path": "device.uptime", "description": "Current uptime (human readable)", "example": "2 years, 14 weeks, 3 days", "category": "Device"},

    # Model variables
    {"path": "model.display_name", "description": "Hardware model name", "example": "Cisco Catalyst 9300-48T", "category": "Model"},
    {"path": "model.chassis", "description": "Chassis identifier", "example": "C9300-48T", "category": "Model"},
    {"path": "platform.name", "description": "Platform name", "example": "cisco_ios", "category": "Model"},
    {"path": "platform.display_name", "description": "Platform display name", "example": "Cisco IOS", "category": "Model"},

    # Interface variables (by name)
    {"path": "interface.<name>.name", "description": "Full interface name", "example": "GigabitEthernet1/0/1", "category": "Interface"},
    {"path": "interface.<name>.short_name", "description": "Short interface name", "example": "Gi1/0/1", "category": "Interface"},
    {"path": "interface.<name>.ip_address", "description": "IP address", "example": "10.0.1.1/30", "category": "Interface"},
    {"path": "interface.<name>.mac_address", "description": "MAC address", "example": "aabb.cc01.0001", "category": "Interface"},
    {"path": "interface.<name>.admin_status", "description": "Admin status", "example": "up", "category": "Interface"},
    {"path": "interface.<name>.oper_status", "description": "Operational status", "example": "up", "category": "Interface"},
    {"path": "interface.<name>.speed_mbps", "description": "Speed in Mbps", "example": "1000", "category": "Interface"},
    {"path": "interface.<name>.mtu", "description": "MTU", "example": "1500", "category": "Interface"},
    {"path": "interface.<name>.description", "description": "Interface description", "example": "Uplink to dist-sw-01", "category": "Interface"},

    # Counter variables
    {"path": "counter.<name>.in_octets", "description": "Input bytes", "example": "584792031847", "category": "Counter"},
    {"path": "counter.<name>.out_octets", "description": "Output bytes", "example": "291034958271", "category": "Counter"},
    {"path": "counter.<name>.in_errors", "description": "Input errors", "example": "0", "category": "Counter"},
    {"path": "counter.<name>.crc_errors", "description": "CRC errors", "example": "0", "category": "Counter"},
    {"path": "counter.<name>.rate_in_bps", "description": "Input rate (bps)", "example": "450000000", "category": "Counter"},

    # SNMP variables
    {"path": "snmp.community", "description": "SNMPv2 community string", "example": "public", "category": "SNMP"},
    {"path": "snmp.sys_contact", "description": "sysContact", "example": "noc@example.com", "category": "SNMP"},
    {"path": "snmp.sys_location", "description": "sysLocation", "example": "DC-East Rack A14", "category": "SNMP"},

    # Neighbor variables
    {"path": "neighbor.<local_intf>.remote_hostname", "description": "Neighbor hostname via interface", "example": "dist-sw-01", "category": "Neighbor"},
    {"path": "neighbor.<local_intf>.remote_interface", "description": "Neighbor interface", "example": "GigabitEthernet1/0/49", "category": "Neighbor"},

    # Time variables
    {"path": "now.timestamp", "description": "Current timestamp (ISO 8601)", "example": "2026-03-29T14:30:00Z", "category": "Time"},
    {"path": "now.cisco_timestamp", "description": "Cisco syslog timestamp", "example": "*Mar 29 14:30:00.123", "category": "Time"},
    {"path": "now.date", "description": "Current date", "example": "2026-03-29", "category": "Time"},
]


async def resolve_variables(
    session: AsyncSession,
    template: str,
    device_id: str,
) -> str:
    """Resolve all {{ variable }} placeholders in a template string.

    Loads the device state and substitutes all variables found.
    Unknown variables are left as-is with a [?] marker.
    """
    # Load device with all relationships
    result = await session.execute(
        select(Device)
        .options(
            selectinload(Device.interfaces).selectinload(Interface.counter),
            selectinload(Device.device_model).selectinload(DeviceModel.platform),
            selectinload(Device.snmp_profile),
        )
        .where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        return template

    context = _build_context(device)

    def replace_var(match):
        path = match.group(1)
        value = _resolve_path(context, path)
        if value is not None:
            return str(value)
        return f"{{{{ {path} [?] }}}}"

    return VAR_PATTERN.sub(replace_var, template)


def resolve_variables_sync(template: str, context: dict) -> str:
    """Resolve variables from a pre-built context dict (no DB needed)."""
    def replace_var(match):
        path = match.group(1)
        value = _resolve_path(context, path)
        if value is not None:
            return str(value)
        return f"{{{{ {path} [?] }}}}"
    return VAR_PATTERN.sub(replace_var, template)


def _build_context(device: Device) -> dict:
    """Build a flat context dict from a device and its relationships."""
    now = datetime.now(timezone.utc)
    from snep.services.counter import uptime_to_ios_string

    uptime_secs = device.uptime_seconds + int((now - device.uptime_reference).total_seconds())

    ctx: dict = {
        "device.hostname": device.hostname,
        "device.management_ip": str(device.management_ip) if device.management_ip else "",
        "device.serial_number": device.serial_number,
        "device.software_version": device.software_version or (device.device_model.software_version if device.device_model else ""),
        "device.admin_state": device.admin_state,
        "device.uptime": uptime_to_ios_string(uptime_secs),
        "now.timestamp": now.isoformat(),
        "now.cisco_timestamp": now.strftime("*%b %d %H:%M:%S.") + f"{now.microsecond // 1000:03d}",
        "now.date": now.strftime("%Y-%m-%d"),
    }

    if device.device_model:
        m = device.device_model
        ctx["model.display_name"] = m.display_name
        ctx["model.chassis"] = (m.hardware_details or {}).get("chassis", m.name)
        if m.platform:
            ctx["platform.name"] = m.platform.name
            ctx["platform.display_name"] = m.platform.display_name

    if device.snmp_profile:
        sp = device.snmp_profile
        ctx["snmp.community"] = sp.v2_community or ""
        ctx["snmp.sys_contact"] = sp.sys_contact or ""
        ctx["snmp.sys_location"] = sp.sys_location or ""

    for iface in device.interfaces:
        prefix = f"interface.{iface.name}"
        ctx[f"{prefix}.name"] = iface.name
        ctx[f"{prefix}.short_name"] = iface.short_name
        ctx[f"{prefix}.ip_address"] = str(iface.ip_address) if iface.ip_address else ""
        ctx[f"{prefix}.mac_address"] = iface.mac_address
        ctx[f"{prefix}.admin_status"] = iface.admin_status
        ctx[f"{prefix}.oper_status"] = iface.oper_status
        ctx[f"{prefix}.speed_mbps"] = str(iface.speed_mbps)
        ctx[f"{prefix}.mtu"] = str(iface.mtu)
        ctx[f"{prefix}.description"] = iface.description or ""

        if iface.counter:
            cp = f"counter.{iface.name}"
            ctx[f"{cp}.in_octets"] = str(iface.counter.in_octets)
            ctx[f"{cp}.out_octets"] = str(iface.counter.out_octets)
            ctx[f"{cp}.in_errors"] = str(iface.counter.in_errors)
            ctx[f"{cp}.crc_errors"] = str(iface.counter.crc_errors)
            ctx[f"{cp}.rate_in_bps"] = str(iface.counter.rate_in_bps)

    return ctx


def _resolve_path(context: dict, path: str):
    """Look up a variable path in the context dict."""
    return context.get(path)


async def get_device_variables(session: AsyncSession, device_id: str) -> list[dict]:
    """Get all resolved variables for a device (for the variable picker UI)."""
    result = await session.execute(
        select(Device)
        .options(
            selectinload(Device.interfaces).selectinload(Interface.counter),
            selectinload(Device.device_model).selectinload(DeviceModel.platform),
            selectinload(Device.snmp_profile),
        )
        .where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        return []

    ctx = _build_context(device)

    variables = []
    for path, value in sorted(ctx.items()):
        # Determine category from path prefix
        category = path.split(".")[0].title()
        if category == "Now":
            category = "Time"

        variables.append({
            "path": path,
            "value": str(value),
            "template": "{{ " + path + " }}",
            "category": category,
        })

    return variables

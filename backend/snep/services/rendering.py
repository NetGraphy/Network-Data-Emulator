"""Rendering engine — resolves commands to templates and renders output from state."""

import re
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from snep.models import CLIOutputMapping, CommandTemplate, Device, Interface
from snep.services.counter import compute_current_counter, compute_current_packets, compute_txload, uptime_to_ios_string
from snep.services.state import compute_interface_counters, get_neighbors

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Jinja2 environment with custom filters
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape([]),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


# Register custom filters
def _ljust(value, width):
    return str(value).ljust(width)

def _rjust(value, width):
    return str(value).rjust(width)

def _mac_cisco(value):
    """Format MAC as Cisco style: aabb.ccdd.eeff"""
    clean = str(value).replace(":", "").replace("-", "").replace(".", "").lower()
    if len(clean) == 12:
        return f"{clean[0:4]}.{clean[4:8]}.{clean[8:12]}"
    return value

def _mac_colon(value):
    clean = str(value).replace(":", "").replace("-", "").replace(".", "").lower()
    if len(clean) == 12:
        return ":".join(clean[i:i+2] for i in range(0, 12, 2))
    return value

def _uptime_ios(seconds):
    if isinstance(seconds, (int, float)):
        return uptime_to_ios_string(int(seconds))
    return str(seconds)

def _speed_human(mbps):
    mbps = int(mbps)
    if mbps >= 100000:
        return f"{mbps // 1000} Gbit"
    elif mbps >= 1000:
        return f"{mbps // 1000} Gbit"
    elif mbps > 0:
        return f"{mbps} Mbit"
    return "0 Kbit"

def _ip_only(value):
    """Strip prefix length from CIDR notation."""
    if value and "/" in str(value):
        return str(value).split("/")[0]
    return str(value) if value else "unassigned"

def _admin_status_display(status):
    if status == "down":
        return "administratively down"
    return status

def _admin_status_brief(status):
    return status

def _oper_status_brief(status):
    return status

def _short_name(name):
    """Convert full interface name to abbreviated form."""
    abbrevs = [
        ("GigabitEthernet", "Gig "),
        ("TenGigabitEthernet", "Ten "),
        ("FastEthernet", "Fas "),
        ("Ethernet", "Eth "),
        ("Loopback", "Loo "),
        ("Vlan", "Vla "),
        ("Port-channel", "Po "),
    ]
    for long, short in abbrevs:
        if str(name).startswith(long):
            return str(name).replace(long, short, 1)
    return str(name)

def _truncate(value, length=10):
    s = str(value)
    return s[:length] if len(s) > length else s


_env.filters["ljust"] = _ljust
_env.filters["rjust"] = _rjust
_env.filters["mac_cisco"] = _mac_cisco
_env.filters["mac_colon"] = _mac_colon
_env.filters["uptime_ios"] = _uptime_ios
_env.filters["speed_human"] = _speed_human
_env.filters["ip_only"] = _ip_only
_env.filters["admin_status_display"] = _admin_status_display
_env.filters["admin_status_display_brief"] = _admin_status_brief
_env.filters["oper_status_display_brief"] = _oper_status_brief
_env.filters["short_name"] = _short_name
_env.filters["truncate"] = _truncate


# Command-to-template mapping for file-based templates
FILE_TEMPLATES = {
    "cisco_ios": {
        "show version": "cisco_ios/show_version.j2",
        "show interfaces": "cisco_ios/show_interfaces.j2",
        "show ip interface brief": "cisco_ios/show_ip_interface_brief.j2",
        "show cdp neighbors": "cisco_ios/show_cdp_neighbors.j2",
        "show cdp neighbors detail": "cisco_ios/show_cdp_neighbors_detail.j2",
        "show lldp neighbors": "cisco_ios/show_lldp_neighbors.j2",
        "show inventory": "cisco_ios/show_inventory.j2",
    },
    "arista_eos": {
        "show version": "arista_eos/show_version.j2",
        "show interfaces": "arista_eos/show_interfaces.j2",
        "show ip interface brief": "arista_eos/show_ip_interface_brief.j2",
        "show lldp neighbors": "arista_eos/show_lldp_neighbors.j2",
    },
}

# Regex patterns for interface-specific commands
INTERFACE_CMD_PATTERN = re.compile(r"^show interfaces?\s+(\S+.*)$", re.IGNORECASE)


async def render_command(session: AsyncSession, device: Device, command: str) -> dict:
    """Render a command for a device. Returns {"output": str, "mode": str}."""
    command = command.strip()
    platform_name = device.device_model.platform.name if device.device_model and device.device_model.platform else "cisco_ios"

    # 1. Check for interface-specific show command
    iface_match = INTERFACE_CMD_PATTERN.match(command)

    # 2. Normalize command for lookup
    canonical = _normalize_command(command)

    # 3. Check for show running-config / show startup-config → DeviceConfig
    if canonical in ("show running-config", "show startup-config"):
        from snep.models.config_source import DeviceConfig
        config_type = "running" if "running" in canonical else "startup"
        config_result = await session.execute(
            select(DeviceConfig)
            .where(DeviceConfig.device_id == device.id, DeviceConfig.config_type == config_type)
        )
        dc = config_result.scalar_one_or_none()
        if dc:
            return {"output": dc.config_text, "mode": "config"}

    # 4. Check CLIOutputMapping (static replay) — device-specific
    result = await session.execute(
        select(CLIOutputMapping)
        .where(CLIOutputMapping.device_id == device.id)
        .where(CLIOutputMapping.command == canonical)
        .where(CLIOutputMapping.is_active == True)
    )
    mapping = result.scalar_one_or_none()
    if mapping and mapping.mode == "static":
        return {"output": mapping.raw_output, "mode": "static"}

    # 4. Try file-based template
    template_path = FILE_TEMPLATES.get(platform_name, {}).get(canonical)

    # 5. For interface-specific commands, try single interface template
    if iface_match and not template_path:
        template_path = FILE_TEMPLATES.get(platform_name, {}).get("show interfaces")
        if template_path:
            template_path = template_path.replace(".j2", "_single.j2")
            if not (TEMPLATES_DIR / template_path).exists():
                template_path = None

    if template_path and (TEMPLATES_DIR / template_path).exists():
        context = await _build_context(session, device, iface_match)
        template = _env.get_template(template_path)
        output = template.render(**context)
        return {"output": output, "mode": "structured"}

    # 6. Unknown command
    platform = device.device_model.platform if device.device_model else None
    if platform:
        error = platform.error_template.format(
            hostname=device.hostname,
            mode_char="#",
        )
    else:
        error = f"% Unknown command: {command}"

    return {"output": error, "mode": "error"}


async def _build_context(session: AsyncSession, device: Device, iface_match=None) -> dict:
    """Build template rendering context from device state."""
    now = datetime.now(timezone.utc)
    uptime_seconds = device.uptime_seconds + int((now - device.uptime_reference).total_seconds())

    # Load interfaces with counters
    result = await session.execute(
        select(Interface)
        .options(selectinload(Interface.counter))
        .where(Interface.device_id == device.id)
        .order_by(Interface.sort_order)
    )
    interfaces = result.scalars().all()

    # Enrich interfaces with computed counters
    enriched_interfaces = []
    for iface in interfaces:
        iface_dict = {
            "name": iface.name,
            "short_name": iface.short_name,
            "if_index": iface.if_index,
            "interface_type": iface.interface_type,
            "admin_status": iface.admin_status,
            "oper_status": iface.oper_status,
            "speed_mbps": iface.speed_mbps,
            "duplex": iface.duplex or "full",
            "mtu": iface.mtu,
            "mac_address": iface.mac_address,
            "ip_address": str(iface.ip_address) if iface.ip_address else None,
            "description": iface.description,
            "vlan_id": iface.vlan_id,
            "last_input": iface.last_input or "never",
            "last_output": iface.last_output or "never",
            "sort_order": iface.sort_order,
        }
        if iface.counter:
            counters = compute_interface_counters(iface.counter, now)
            iface_dict["counters"] = counters
            iface_dict["txload"] = compute_txload(counters["rate_out_bps"], iface.speed_mbps)
            iface_dict["rxload"] = compute_txload(counters["rate_in_bps"], iface.speed_mbps)
        else:
            iface_dict["counters"] = {}
            iface_dict["txload"] = 0
            iface_dict["rxload"] = 0
        enriched_interfaces.append(iface_dict)

    # Single interface filter
    single_interface = None
    if iface_match:
        target_name = iface_match.group(1).strip()
        for iface in enriched_interfaces:
            if iface["name"].lower() == target_name.lower() or iface["short_name"].lower() == target_name.lower():
                single_interface = iface
                break

    # Neighbors
    neighbors = await get_neighbors(session, str(device.id))

    model = device.device_model
    hardware = model.hardware_details or {} if model else {}

    return {
        "device": {
            "hostname": device.hostname,
            "serial_number": device.serial_number,
            "software_version": device.software_version or (model.software_version if model else ""),
            "management_ip": str(device.management_ip) if device.management_ip else "",
            "admin_state": device.admin_state,
        },
        "model": {
            "name": model.name if model else "",
            "display_name": model.display_name if model else "",
            "software_version": model.software_version if model else "",
            "hardware_details": hardware,
        },
        "platform": {
            "name": model.platform.name if model and model.platform else "cisco_ios",
            "display_name": model.platform.display_name if model and model.platform else "Cisco IOS",
        },
        "interfaces": enriched_interfaces,
        "interface": single_interface,
        "neighbors": neighbors,
        "uptime": uptime_seconds,
        "uptime_string": uptime_to_ios_string(uptime_seconds),
        "timestamp": now,
        "hardware": hardware,
    }


def _normalize_command(command: str) -> str:
    """Expand abbreviated commands to canonical form."""
    command = command.strip().lower()

    # Common abbreviation expansions
    expansions = [
        (r"^sh(?:ow)?\s+ver(?:sion)?$", "show version"),
        (r"^sh(?:ow)?\s+int(?:erfaces?)?$", "show interfaces"),
        (r"^sh(?:ow)?\s+ip\s+int(?:erface)?\s+br(?:ief)?$", "show ip interface brief"),
        (r"^sh(?:ow)?\s+cdp\s+neigh(?:bors?)?\s+det(?:ail)?$", "show cdp neighbors detail"),
        (r"^sh(?:ow)?\s+cdp\s+neigh(?:bors?)?$", "show cdp neighbors"),
        (r"^sh(?:ow)?\s+lldp\s+neigh(?:bors?)?$", "show lldp neighbors"),
        (r"^sh(?:ow)?\s+inv(?:entory)?$", "show inventory"),
        (r"^sh(?:ow)?\s+run(?:ning-config)?$", "show running-config"),
        (r"^sh(?:ow)?\s+log(?:ging)?$", "show logging"),
    ]

    for pattern, canonical in expansions:
        if re.match(pattern, command):
            return canonical

    # Interface-specific: normalize to just "show interfaces" for lookup
    iface_match = re.match(r"^sh(?:ow)?\s+int(?:erfaces?)?\s+\S+", command)
    if iface_match:
        return "show interfaces"

    return command

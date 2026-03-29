"""SNMP Walk renderer — produces net-snmp-formatted output from device state.

Renders snmpwalk-style output for the UI preview, matching the exact format
that net-snmp tools (snmpwalk, snmpget, snmpbulkwalk) produce.
"""

from datetime import datetime, timezone

from snep.snmp.oid_tree import (
    IF_TYPE_MAP,
    ADMIN_STATUS_MAP,
    OPER_STATUS_MAP,
    build_oid_tree,
    find_exact_oid,
    find_next_oid,
)

# Reverse maps for named enumerations
IF_TYPE_NAMES = {6: "ethernetCsmacd", 24: "softwareLoopback", 136: "l3ipvlan",
                 161: "ieee8023adLag", 131: "tunnel", 53: "propVirtual", 1: "other"}
ADMIN_STATUS_NAMES = {1: "up", 2: "down", 3: "testing"}
OPER_STATUS_NAMES = {1: "up", 2: "down", 3: "testing", 5: "dormant", 6: "notPresent", 7: "lowerLayerDown"}

# OID to MIB name mapping
OID_NAMES = {
    "1.3.6.1.2.1.1.1": "SNMPv2-MIB::sysDescr",
    "1.3.6.1.2.1.1.2": "SNMPv2-MIB::sysObjectID",
    "1.3.6.1.2.1.1.3": "DISMAN-EVENT-MIB::sysUpTimeInstance",
    "1.3.6.1.2.1.1.4": "SNMPv2-MIB::sysContact",
    "1.3.6.1.2.1.1.5": "SNMPv2-MIB::sysName",
    "1.3.6.1.2.1.1.6": "SNMPv2-MIB::sysLocation",
    "1.3.6.1.2.1.1.7": "SNMPv2-MIB::sysServices",
    "1.3.6.1.2.1.2.1": "IF-MIB::ifNumber",
    "1.3.6.1.2.1.2.2.1.1": "IF-MIB::ifIndex",
    "1.3.6.1.2.1.2.2.1.2": "IF-MIB::ifDescr",
    "1.3.6.1.2.1.2.2.1.3": "IF-MIB::ifType",
    "1.3.6.1.2.1.2.2.1.4": "IF-MIB::ifMtu",
    "1.3.6.1.2.1.2.2.1.5": "IF-MIB::ifSpeed",
    "1.3.6.1.2.1.2.2.1.6": "IF-MIB::ifPhysAddress",
    "1.3.6.1.2.1.2.2.1.7": "IF-MIB::ifAdminStatus",
    "1.3.6.1.2.1.2.2.1.8": "IF-MIB::ifOperStatus",
    "1.3.6.1.2.1.2.2.1.9": "IF-MIB::ifLastChange",
    "1.3.6.1.2.1.2.2.1.10": "IF-MIB::ifInOctets",
    "1.3.6.1.2.1.2.2.1.11": "IF-MIB::ifInUcastPkts",
    "1.3.6.1.2.1.2.2.1.13": "IF-MIB::ifInDiscards",
    "1.3.6.1.2.1.2.2.1.14": "IF-MIB::ifInErrors",
    "1.3.6.1.2.1.2.2.1.16": "IF-MIB::ifOutOctets",
    "1.3.6.1.2.1.2.2.1.17": "IF-MIB::ifOutUcastPkts",
    "1.3.6.1.2.1.2.2.1.19": "IF-MIB::ifOutDiscards",
    "1.3.6.1.2.1.2.2.1.20": "IF-MIB::ifOutErrors",
    "1.3.6.1.2.1.31.1.1.1.1": "IF-MIB::ifName",
    "1.3.6.1.2.1.31.1.1.1.6": "IF-MIB::ifHCInOctets",
    "1.3.6.1.2.1.31.1.1.1.10": "IF-MIB::ifHCOutOctets",
    "1.3.6.1.2.1.31.1.1.1.15": "IF-MIB::ifHighSpeed",
    "1.3.6.1.2.1.31.1.1.1.18": "IF-MIB::ifAlias",
}

# Well-known walk subtrees
WALK_SUBTREES = {
    "system": "1.3.6.1.2.1.1",
    "interfaces": "1.3.6.1.2.1.2",
    "ifTable": "1.3.6.1.2.1.2.2",
    "ifXTable": "1.3.6.1.2.1.31.1.1",
    "all": "1.3.6.1.2.1",
}


def render_snmp_walk(
    device: dict,
    interfaces: list[dict],
    snmp_profile: dict | None,
    subtree: str = "all",
    output_format: str = "named",
) -> str:
    """Render snmpwalk-style output from device state.

    Args:
        device: device state dict
        interfaces: list of interface state dicts
        snmp_profile: SNMP profile dict
        subtree: "system", "interfaces", "ifTable", "ifXTable", or "all"
        output_format: "named" (MIB names) or "numeric" (raw OIDs)

    Returns:
        Formatted text matching net-snmp snmpwalk output
    """
    tree = build_oid_tree(device, interfaces, snmp_profile)

    # Resolve subtree OID
    start_oid = WALK_SUBTREES.get(subtree, subtree)

    # Walk the tree from start_oid
    lines = []
    current_oid = start_oid

    # Find first OID at or after start
    for oid, typ, val in tree:
        if oid.startswith(start_oid):
            line = _format_oid_line(oid, typ, val, output_format)
            lines.append(line)

    if not lines:
        return f"No SNMP data available for subtree {subtree}"

    return "\n".join(lines)


def render_snmp_get(
    device: dict,
    interfaces: list[dict],
    snmp_profile: dict | None,
    oid: str,
    output_format: str = "named",
) -> str:
    """Render snmpget-style output for a single OID."""
    tree = build_oid_tree(device, interfaces, snmp_profile)
    result = find_exact_oid(tree, oid)

    if result:
        return _format_oid_line(result[0], result[1], result[2], output_format)
    else:
        name = _resolve_name(oid, output_format)
        return f"{name} = No Such Instance currently exists at this OID"


def _format_oid_line(oid: str, asn1_type: str, value, output_format: str) -> str:
    """Format a single OID-value pair in net-snmp style."""
    name = _resolve_name(oid, output_format)
    formatted_value = _format_value(oid, asn1_type, value)
    return f"{name} = {formatted_value}"


def _resolve_name(oid: str, output_format: str) -> str:
    """Convert numeric OID to MIB-qualified name."""
    if output_format == "numeric":
        return f".{oid}"

    # Try to match the longest prefix
    parts = oid.split(".")
    for length in range(len(parts), 0, -1):
        prefix = ".".join(parts[:length])
        if prefix in OID_NAMES:
            suffix = ".".join(parts[length:])
            name = OID_NAMES[prefix]
            # Special case: sysUpTime instance
            if name == "DISMAN-EVENT-MIB::sysUpTimeInstance":
                return name  # no suffix needed
            if suffix:
                return f"{name}.{suffix}"
            return f"{name}.0"  # scalar

    return oid


def _format_value(oid: str, asn1_type: str, value) -> str:
    """Format a value with its type annotation in net-snmp style."""
    if asn1_type == "OctetString":
        # MAC addresses
        if _is_mac_oid(oid) and value and len(str(value).replace(".", "").replace(":", "")) == 12:
            mac = str(value).replace(".", "").replace(":", "").lower()
            formatted = ":".join(mac[i:i+2] for i in range(0, 12, 2))
            return f"STRING: {formatted}"
        return f"STRING: {value}"

    elif asn1_type == "Integer32":
        # Check for enumerated types
        enum_val = _get_enum_name(oid, int(value))
        if enum_val:
            return f"INTEGER: {enum_val}({int(value)})"
        return f"INTEGER: {int(value)}"

    elif asn1_type == "Counter32":
        return f"Counter32: {int(value)}"

    elif asn1_type == "Counter64":
        return f"Counter64: {int(value)}"

    elif asn1_type == "Gauge32":
        return f"Gauge32: {int(value)}"

    elif asn1_type == "TimeTicks":
        ticks = int(value)
        readable = _format_timeticks(ticks)
        return f"Timeticks: ({ticks}) {readable}"

    elif asn1_type == "ObjectIdentifier":
        return f"OID: SNMPv2-SMI::enterprises{str(value)[len('1.3.6.1.4.1'):]}" if str(value).startswith("1.3.6.1.4.1") else f"OID: {value}"

    return f"STRING: {value}"


def _is_mac_oid(oid: str) -> bool:
    """Check if this OID is ifPhysAddress."""
    return ".2.2.1.6." in oid


def _get_enum_name(oid: str, value: int) -> str | None:
    """Get enumeration name for known integer-valued OIDs."""
    # ifType
    if ".2.2.1.3." in oid:
        return IF_TYPE_NAMES.get(value)
    # ifAdminStatus
    if ".2.2.1.7." in oid:
        return ADMIN_STATUS_NAMES.get(value)
    # ifOperStatus
    if ".2.2.1.8." in oid:
        return OPER_STATUS_NAMES.get(value)
    return None


def _format_timeticks(centiseconds: int) -> str:
    """Format timeticks as human-readable string: 'X days, HH:MM:SS.CC'"""
    cs = centiseconds % 100
    total_seconds = centiseconds // 100
    days = total_seconds // 86400
    rem = total_seconds % 86400
    hours = rem // 3600
    rem = rem % 3600
    minutes = rem // 60
    seconds = rem % 60

    if days > 0:
        return f"{days} days, {hours}:{minutes:02d}:{seconds:02d}.{cs:02d}"
    else:
        return f"{hours}:{minutes:02d}:{seconds:02d}.{cs:02d}"

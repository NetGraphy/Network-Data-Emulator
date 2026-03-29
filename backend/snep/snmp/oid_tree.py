"""OID tree builder — constructs a sorted OID tree from device state for SNMP walks."""

from datetime import datetime, timezone

from snep.services.counter import compute_current_counter, compute_current_packets, wrap_counter32, wrap_counter64

# IF-MIB ifType mappings
IF_TYPE_MAP = {
    "ethernet": 6,       # ethernetCsmacd
    "loopback": 24,      # softwareLoopback
    "vlan": 136,         # l3ipvlan
    "port_channel": 161, # ieee8023adLag
    "tunnel": 131,       # tunnel
    "management": 6,     # ethernetCsmacd
}

ADMIN_STATUS_MAP = {"up": 1, "down": 2}
OPER_STATUS_MAP = {"up": 1, "down": 2, "dormant": 5, "notPresent": 6, "lowerLayerDown": 7}


def build_oid_tree(device: dict, interfaces: list[dict], snmp_profile: dict | None) -> list[tuple[str, str, any]]:
    """Build a sorted list of (oid_string, asn1_type, value) tuples.

    Args:
        device: {"hostname", "serial_number", "software_version", "uptime_seconds", "uptime_reference", ...}
        interfaces: list of dicts with interface state + counter data
        snmp_profile: SNMPProfile fields or None
    """
    now = datetime.now(timezone.utc)
    tree = []

    # -- system MIB (1.3.6.1.2.1.1) --
    sys_descr = snmp_profile.get("sys_descr") if snmp_profile else None
    if not sys_descr:
        sys_descr = f"Cisco IOS Software, Version {device.get('software_version', '17.06.05')}"

    uptime_ref = device.get("uptime_reference", now)
    if isinstance(uptime_ref, str):
        uptime_ref = datetime.fromisoformat(uptime_ref)
    uptime_seconds = device.get("uptime_seconds", 0) + int((now - uptime_ref).total_seconds())
    sys_uptime_ticks = uptime_seconds * 100  # centiseconds

    tree.append(("1.3.6.1.2.1.1.1.0", "OctetString", sys_descr))
    tree.append(("1.3.6.1.2.1.1.2.0", "ObjectIdentifier", "1.3.6.1.4.1.9.1.1"))  # Cisco
    tree.append(("1.3.6.1.2.1.1.3.0", "TimeTicks", sys_uptime_ticks))
    tree.append(("1.3.6.1.2.1.1.4.0", "OctetString", (snmp_profile or {}).get("sys_contact", "")))
    tree.append(("1.3.6.1.2.1.1.5.0", "OctetString", (snmp_profile or {}).get("sys_name", device.get("hostname", ""))))
    tree.append(("1.3.6.1.2.1.1.6.0", "OctetString", (snmp_profile or {}).get("sys_location", "")))
    tree.append(("1.3.6.1.2.1.1.7.0", "Integer32", 72))  # sysServices: layers 3+4

    # -- ifNumber (1.3.6.1.2.1.2.1.0) --
    tree.append(("1.3.6.1.2.1.2.1.0", "Integer32", len(interfaces)))

    # -- ifTable (1.3.6.1.2.1.2.2.1) --
    for iface in interfaces:
        idx = iface["if_index"]
        counter = iface.get("counter", {})
        rate_ref = counter.get("rate_reference", now)
        if isinstance(rate_ref, str):
            rate_ref = datetime.fromisoformat(rate_ref)

        # Compute current counters
        in_octets = compute_current_counter(
            counter.get("in_octets", 0), counter.get("rate_in_bps", 0), rate_ref, now
        )
        out_octets = compute_current_counter(
            counter.get("out_octets", 0), counter.get("rate_out_bps", 0), rate_ref, now
        )
        in_pkts = compute_current_packets(
            counter.get("in_octets", 0), counter.get("rate_in_bps", 0), rate_ref,
            counter.get("in_unicast_pkts", 0), now
        )
        out_pkts = compute_current_packets(
            counter.get("out_octets", 0), counter.get("rate_out_bps", 0), rate_ref,
            counter.get("out_unicast_pkts", 0), now
        )

        # ifTable entries
        tree.append((f"1.3.6.1.2.1.2.2.1.1.{idx}", "Integer32", idx))
        tree.append((f"1.3.6.1.2.1.2.2.1.2.{idx}", "OctetString", iface["name"]))
        tree.append((f"1.3.6.1.2.1.2.2.1.3.{idx}", "Integer32", IF_TYPE_MAP.get(iface.get("interface_type", "ethernet"), 6)))
        tree.append((f"1.3.6.1.2.1.2.2.1.4.{idx}", "Integer32", iface.get("mtu", 1500)))
        tree.append((f"1.3.6.1.2.1.2.2.1.5.{idx}", "Gauge32", iface.get("speed_mbps", 0) * 1_000_000))
        tree.append((f"1.3.6.1.2.1.2.2.1.6.{idx}", "OctetString", iface.get("mac_address", "")))
        tree.append((f"1.3.6.1.2.1.2.2.1.7.{idx}", "Integer32", ADMIN_STATUS_MAP.get(iface.get("admin_status", "up"), 1)))
        tree.append((f"1.3.6.1.2.1.2.2.1.8.{idx}", "Integer32", OPER_STATUS_MAP.get(iface.get("oper_status", "up"), 1)))
        tree.append((f"1.3.6.1.2.1.2.2.1.9.{idx}", "TimeTicks", 0))  # ifLastChange
        tree.append((f"1.3.6.1.2.1.2.2.1.10.{idx}", "Counter32", wrap_counter32(in_octets)))
        tree.append((f"1.3.6.1.2.1.2.2.1.11.{idx}", "Counter32", wrap_counter32(in_pkts)))
        tree.append((f"1.3.6.1.2.1.2.2.1.13.{idx}", "Counter32", counter.get("in_discards", 0)))
        tree.append((f"1.3.6.1.2.1.2.2.1.14.{idx}", "Counter32", counter.get("in_errors", 0)))
        tree.append((f"1.3.6.1.2.1.2.2.1.16.{idx}", "Counter32", wrap_counter32(out_octets)))
        tree.append((f"1.3.6.1.2.1.2.2.1.17.{idx}", "Counter32", wrap_counter32(out_pkts)))
        tree.append((f"1.3.6.1.2.1.2.2.1.19.{idx}", "Counter32", counter.get("out_discards", 0)))
        tree.append((f"1.3.6.1.2.1.2.2.1.20.{idx}", "Counter32", counter.get("out_errors", 0)))

        # ifXTable entries (1.3.6.1.2.1.31.1.1.1)
        tree.append((f"1.3.6.1.2.1.31.1.1.1.1.{idx}", "OctetString", iface.get("short_name", iface["name"])))
        tree.append((f"1.3.6.1.2.1.31.1.1.1.6.{idx}", "Counter64", wrap_counter64(in_octets)))
        tree.append((f"1.3.6.1.2.1.31.1.1.1.10.{idx}", "Counter64", wrap_counter64(out_octets)))
        tree.append((f"1.3.6.1.2.1.31.1.1.1.15.{idx}", "Gauge32", iface.get("speed_mbps", 0)))
        tree.append((f"1.3.6.1.2.1.31.1.1.1.18.{idx}", "OctetString", iface.get("description", "") or ""))

    # Sort by OID (lexicographic on numeric tuples)
    tree.sort(key=lambda x: _oid_sort_key(x[0]))
    return tree


def _oid_sort_key(oid: str) -> tuple[int, ...]:
    """Convert OID string to tuple of ints for proper sorting."""
    return tuple(int(x) for x in oid.split(".") if x)


def find_next_oid(tree: list[tuple], requested_oid: str) -> tuple | None:
    """Find the next OID after the requested one (for GETNEXT/WALK)."""
    req_key = _oid_sort_key(requested_oid)

    for oid, typ, val in tree:
        if _oid_sort_key(oid) > req_key:
            return (oid, typ, val)

    return None


def find_exact_oid(tree: list[tuple], requested_oid: str) -> tuple | None:
    """Find exact OID match (for GET)."""
    for oid, typ, val in tree:
        if oid == requested_oid:
            return (oid, typ, val)
    return None

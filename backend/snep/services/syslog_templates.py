"""Syslog message template library — real Cisco IOS and Arista EOS syslog formats.

Each template produces exact syslog messages matching what real devices generate.
Templates are keyed by event_type and produce one or more log lines per event.

Sources: Cisco IOS System Message Guide, Arista EOS documentation, production device captures.
"""

from datetime import datetime, timezone

# Severity levels (RFC 5424)
SEVERITY_NAMES = {0: "emergencies", 1: "alerts", 2: "critical", 3: "errors",
                  4: "warnings", 5: "notifications", 6: "informational", 7: "debugging"}

# --- Message Templates ---
# Each entry: list of messages generated for this event type.
# Variables in {braces} are substituted from the event context.

TEMPLATES: dict[str, list[dict]] = {
    # === Interface Events ===
    "interface_down": [
        {"facility": "LINK", "severity": 3, "mnemonic": "UPDOWN",
         "template": "Interface {interface_name}, changed state to down",
         "arista_agent": "Ebra"},
        {"facility": "LINEPROTO", "severity": 5, "mnemonic": "UPDOWN",
         "template": "Line protocol on Interface {interface_name}, changed state to down",
         "arista_agent": "Ebra", "delay_ms": 1000},
    ],
    "interface_up": [
        {"facility": "LINK", "severity": 3, "mnemonic": "UPDOWN",
         "template": "Interface {interface_name}, changed state to up",
         "arista_agent": "Ebra"},
        {"facility": "LINEPROTO", "severity": 5, "mnemonic": "UPDOWN",
         "template": "Line protocol on Interface {interface_name}, changed state to up (connected)",
         "arista_agent": "Ebra", "delay_ms": 1000},
    ],
    "interface_admin_down": [
        {"facility": "LINK", "severity": 5, "mnemonic": "CHANGED",
         "template": "Interface {interface_name}, changed state to administratively down",
         "arista_agent": "Ebra"},
        {"facility": "LINEPROTO", "severity": 5, "mnemonic": "UPDOWN",
         "template": "Line protocol on Interface {interface_name}, changed state to down",
         "arista_agent": "Ebra", "delay_ms": 500},
    ],

    # === BGP Events ===
    "bgp_neighbor_down": [
        {"facility": "BGP", "severity": 5, "mnemonic": "ADJCHANGE",
         "template": "neighbor {neighbor_ip} Down {reason}",
         "arista_agent": "Bgp"},
    ],
    "bgp_neighbor_up": [
        {"facility": "BGP", "severity": 5, "mnemonic": "ADJCHANGE",
         "template": "neighbor {neighbor_ip} Up",
         "arista_agent": "Bgp"},
    ],

    # === OSPF Events ===
    "ospf_neighbor_down": [
        {"facility": "OSPF", "severity": 5, "mnemonic": "ADJCHG",
         "template": "Process {process_id}, Nbr {neighbor_id} on {interface_name} from FULL to DOWN, Neighbor Down: Interface down or detached",
         "arista_agent": "Ospf"},
    ],
    "ospf_neighbor_up": [
        {"facility": "OSPF", "severity": 5, "mnemonic": "ADJCHG",
         "template": "Process {process_id}, Nbr {neighbor_id} on {interface_name} from LOADING to FULL, Loading Done",
         "arista_agent": "Ospf"},
    ],

    # === System Events ===
    "device_reload": [
        {"facility": "SYS", "severity": 5, "mnemonic": "RELOAD",
         "template": "Reload requested by {source}. Reload Reason: {reason}.",
         "arista_agent": "Launcher"},
    ],
    "config_change": [
        {"facility": "SYS", "severity": 5, "mnemonic": "CONFIG_I",
         "template": "Configured from {source} by {user} on vty0 ({source_ip})",
         "arista_agent": "ConfigAgent"},
    ],
    "warmstart": [
        {"facility": "SYS", "severity": 6, "mnemonic": "RESTART",
         "template": "System restarted --\nCisco IOS Software, Version {software_version}",
         "arista_agent": "Launcher"},
    ],

    # === CDP/LLDP Events ===
    "cdp_duplex_mismatch": [
        {"facility": "CDP", "severity": 4, "mnemonic": "DUPLEX_MISMATCH",
         "template": "duplex mismatch discovered on {interface_name} ({local_duplex}), with {remote_device} {remote_interface} ({remote_duplex}).",
         "arista_agent": "Lldp"},
    ],
    "cdp_neighbor_added": [
        {"facility": "CDP", "severity": 6, "mnemonic": "NATIVE_VLAN_MISMATCH",
         "template": "Native VLAN mismatch detected on {interface_name} ({local_vlan}), with {remote_device} {remote_interface} ({remote_vlan}).",
         "arista_agent": "Lldp"},
    ],

    # === HSRP/VRRP Events ===
    "hsrp_state_change": [
        {"facility": "HSRP", "severity": 5, "mnemonic": "STATECHANGE",
         "template": "{interface_name} Grp {group} state {old_state} -> {new_state}",
         "arista_agent": "Vrrp"},
    ],

    # === Spanning Tree Events ===
    "stp_topology_change": [
        {"facility": "SPANTREE", "severity": 5, "mnemonic": "TOPOTRAP",
         "template": "Topology Change Trap for vlan {vlan_id}",
         "arista_agent": "Stp"},
    ],
    "stp_block": [
        {"facility": "SPANTREE", "severity": 2, "mnemonic": "BLOCK_PVID_LOCAL",
         "template": "Blocking {interface_name} on VLAN{vlan_id}. Inconsistent local vlan.",
         "arista_agent": "Stp"},
    ],

    # === Hardware Events ===
    "psu_failure": [
        {"facility": "PLATFORM_ENV", "severity": 1, "mnemonic": "PSU",
         "template": "Power supply {psu_id} is not operational",
         "arista_agent": "Focalpoint"},
    ],
    "fan_failure": [
        {"facility": "PLATFORM_ENV", "severity": 1, "mnemonic": "FAN",
         "template": "Faulty fan detected on fan tray {fan_id}",
         "arista_agent": "Focalpoint"},
    ],

    # === Performance Events ===
    "cpu_hog": [
        {"facility": "SYS", "severity": 3, "mnemonic": "CPUHOG",
         "template": "Task ran for {duration_ms} msec (0/0), process = {process_name}, PC = 0x{pc_hex}",
         "arista_agent": "ProcMgr"},
    ],
    "memory_failure": [
        {"facility": "SYS", "severity": 2, "mnemonic": "MALLOCFAIL",
         "template": "Memory allocation of {bytes} bytes failed from 0x{addr_hex}, alignment {alignment}",
         "arista_agent": "ProcMgr"},
    ],

    # === Security Events ===
    "acl_deny": [
        {"facility": "SEC", "severity": 6, "mnemonic": "IPACCESSLOGP",
         "template": "list {acl_name} denied {protocol} {source_ip}({source_port}) -> {dest_ip}({dest_port}), 1 packet",
         "arista_agent": "Acl"},
    ],

    # === CRC / Error Events ===
    "input_errors": [
        {"facility": "LINK", "severity": 4, "mnemonic": "ERROR",
         "template": "Interface {interface_name}, input error counter incrementing: CRC={crc_count}, frame={frame_count}",
         "arista_agent": "Ebra"},
    ],
}


def render_syslog(
    event_type: str,
    context: dict,
    platform: str = "cisco_ios",
    hostname: str = "",
    timestamp: datetime | None = None,
) -> list[dict]:
    """Render syslog messages for an event.

    Args:
        event_type: Key into TEMPLATES (e.g., "interface_down")
        context: Variable substitution dict (interface_name, neighbor_ip, etc.)
        platform: "cisco_ios" or "arista_eos"
        hostname: Device hostname for Arista format
        timestamp: Message timestamp (defaults to now)

    Returns:
        List of {"severity": int, "facility": str, "mnemonic": str,
                 "formatted": str, "raw_message": str}
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    templates = TEMPLATES.get(event_type, [])
    results = []

    for tmpl in templates:
        try:
            raw_msg = tmpl["template"].format(**context)
        except KeyError as e:
            raw_msg = tmpl["template"] + f" [missing field: {e}]"

        facility = tmpl["facility"]
        severity = tmpl["severity"]
        mnemonic = tmpl["mnemonic"]

        if platform == "arista_eos":
            agent = tmpl.get("arista_agent", "")
            ts = timestamp.strftime("%b %d %H:%M:%S")
            formatted = f"{ts} {hostname} {agent}: %{facility}-{severity}-{mnemonic}: {raw_msg}"
        else:
            # Cisco IOS format
            ts = timestamp.strftime("*%b %d %H:%M:%S.") + f"{timestamp.microsecond // 1000:03d}"
            formatted = f"{ts}: %{facility}-{severity}-{mnemonic}: {raw_msg}"

        results.append({
            "severity": severity,
            "facility": facility,
            "mnemonic": mnemonic,
            "formatted": formatted,
            "raw_message": raw_msg,
            "event_type": event_type,
            "delay_ms": tmpl.get("delay_ms", 0),
        })

    return results


def get_available_event_types() -> list[dict]:
    """Return all available event types with descriptions."""
    return [
        {"type": key, "message_count": len(msgs),
         "facilities": list(set(m["facility"] for m in msgs)),
         "severities": list(set(m["severity"] for m in msgs))}
        for key, msgs in TEMPLATES.items()
    ]

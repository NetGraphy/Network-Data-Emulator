"""Parser validation service — tests CLI output against known parsers.

Validates pasted output against TextFSM (NTC-Templates) and detects
structural changes between versions of the same command output.
"""

import difflib
import re
import io
import logging
from typing import Any

logger = logging.getLogger(__name__)

# NTC-Templates platform mapping
NTC_PLATFORM_MAP = {
    "cisco_ios": "cisco_ios",
    "arista_eos": "arista_eos",
    "juniper_junos": "juniper_junos",
    "cisco_nxos": "cisco_nxos",
    "cisco_iosxe": "cisco_ios",  # NTC uses cisco_ios for IOS-XE too
}

# Command to NTC-Template name mapping
NTC_COMMAND_MAP = {
    "show version": "show_version",
    "show interfaces": "show_interfaces",
    "show ip interface brief": "show_ip_interface_brief",
    "show cdp neighbors": "show_cdp_neighbors",
    "show cdp neighbors detail": "show_cdp_neighbors_detail",
    "show lldp neighbors": "show_lldp_neighbors",
    "show lldp neighbors detail": "show_lldp_neighbors_detail",
    "show running-config": "show_running-config",
    "show inventory": "show_inventory",
    "show ip route": "show_ip_route",
    "show ip bgp summary": "show_ip_bgp_summary",
    "show ip ospf neighbor": "show_ip_ospf_neighbor",
    "show mac address-table": "show_mac-address-table",
    "show vlan brief": "show_vlan",
    "show spanning-tree": "show_spanning-tree",
    "show logging": "show_logging",
    "show environment": "show_environment",
    "show processes cpu": "show_processes_cpu",
}


def validate_against_parsers(
    raw_output: str,
    platform_name: str,
    command: str,
) -> dict[str, Any]:
    """Test raw CLI output against available parsers.

    Returns: {
        "textfsm": {"status": "pass"|"fail"|"no_template", "template": str, "parsed_fields": list, "parsed_data": list, "error": str|None},
        "regex_extract": {"status": "pass", "detected_fields": dict},
    }
    """
    results = {}

    # TextFSM validation
    results["textfsm"] = _validate_textfsm(raw_output, platform_name, command)

    # Regex-based field extraction (always works, no external deps)
    results["regex_extract"] = _extract_fields_regex(raw_output, platform_name, command)

    return results


def _validate_textfsm(raw_output: str, platform_name: str, command: str) -> dict:
    """Try to parse output with TextFSM/NTC-Templates."""
    try:
        import textfsm
    except ImportError:
        return {"status": "no_library", "template": None, "parsed_fields": [], "parsed_data": [], "error": "textfsm not installed"}

    ntc_platform = NTC_PLATFORM_MAP.get(platform_name, platform_name)
    cmd_slug = NTC_COMMAND_MAP.get(command)

    if not cmd_slug:
        # Try to generate slug from command
        cmd_slug = command.replace(" ", "_")

    template_name = f"{ntc_platform}_{cmd_slug}.textfsm"

    # Try to find the template
    try:
        import ntc_templates
        from ntc_templates.parse import parse_output

        parsed = parse_output(platform=ntc_platform, command=command, data=raw_output)
        if parsed:
            fields = list(parsed[0].keys()) if parsed else []
            return {
                "status": "pass",
                "template": template_name,
                "parsed_fields": fields,
                "parsed_data": parsed,
                "error": None,
                "row_count": len(parsed),
            }
        else:
            return {
                "status": "fail",
                "template": template_name,
                "parsed_fields": [],
                "parsed_data": [],
                "error": "Parser returned empty result — output may not match expected format",
            }

    except ImportError:
        return {"status": "no_library", "template": template_name, "parsed_fields": [], "parsed_data": [], "error": "ntc-templates not installed — install with: pip install ntc-templates"}
    except Exception as e:
        return {"status": "fail", "template": template_name, "parsed_fields": [], "parsed_data": [], "error": str(e)}


def _extract_fields_regex(raw_output: str, platform_name: str, command: str) -> dict:
    """Extract structured fields from CLI output using regex patterns.

    This always works regardless of external parser availability.
    """
    detected = {}

    if command == "show version":
        detected = _extract_show_version(raw_output, platform_name)
    elif command == "show ip interface brief":
        detected = _extract_show_ip_int_brief(raw_output)
    elif command in ("show cdp neighbors", "show lldp neighbors"):
        detected = _extract_show_neighbors(raw_output)
    elif command in ("show interfaces", "show interface"):
        detected = _extract_show_interfaces(raw_output)
    else:
        detected = _generic_extract(raw_output)

    return {"status": "pass", "detected_fields": detected}


def _extract_show_version(output: str, platform: str) -> dict:
    fields = {}

    # Cisco IOS/IOS-XE
    if platform in ("cisco_ios", "cisco_iosxe"):
        m = re.search(r"Version\s+([\d.()A-Za-z]+)", output)
        if m:
            fields["software_version"] = m.group(1)

        m = re.search(r"(\S+)\s+uptime is\s+(.+)", output)
        if m:
            fields["hostname"] = m.group(1)
            fields["uptime"] = m.group(2).strip()

        m = re.search(r"System serial number\s*:\s*(\S+)", output, re.IGNORECASE)
        if not m:
            m = re.search(r"Processor board ID\s+(\S+)", output)
        if m:
            fields["serial_number"] = m.group(1)

        m = re.search(r"cisco\s+(\S+)", output, re.IGNORECASE)
        if m:
            fields["hardware_model"] = m.group(1)

        m = re.search(r"(\d+)K/(\d+)K bytes of memory", output)
        if m:
            fields["memory_total_kb"] = m.group(1)
            fields["memory_free_kb"] = m.group(2)

        m = re.search(r"(\d+)K bytes of flash", output)
        if m:
            fields["flash_kb"] = m.group(1)

        m = re.search(r"Configuration register is\s+(0x\w+)", output)
        if m:
            fields["config_register"] = m.group(1)

    # Arista EOS
    elif platform == "arista_eos":
        m = re.search(r"Software image version:\s+(.+)", output)
        if m:
            fields["software_version"] = m.group(1).strip()

        m = re.search(r"Serial number:\s+(\S+)", output)
        if m:
            fields["serial_number"] = m.group(1)

        m = re.search(r"Arista\s+(\S+)", output)
        if m:
            fields["hardware_model"] = m.group(1)

        m = re.search(r"Uptime:\s+(.+)", output)
        if m:
            fields["uptime"] = m.group(1).strip()

    return fields


def _extract_show_ip_int_brief(output: str) -> dict:
    """Extract interfaces from show ip interface brief output."""
    interfaces = []
    lines = output.strip().split("\n")

    for line in lines[1:]:  # Skip header
        parts = line.split()
        if len(parts) >= 6:
            interfaces.append({
                "interface": parts[0],
                "ip_address": parts[1],
                "status": parts[4] if len(parts) > 4 else "",
                "protocol": parts[5] if len(parts) > 5 else "",
            })

    return {"interfaces": interfaces, "interface_count": len(interfaces)}


def _extract_show_neighbors(output: str) -> dict:
    """Extract neighbor entries from CDP/LLDP output."""
    neighbors = []
    lines = output.strip().split("\n")

    # Find data lines (skip headers, capability codes, blank lines)
    in_data = False
    for line in lines:
        if "Device ID" in line and ("Local" in line or "Port" in line):
            in_data = True
            continue
        if in_data and line.strip() and not line.startswith("Total"):
            parts = line.split()
            if len(parts) >= 2:
                neighbors.append({
                    "device_id": parts[0],
                    "local_interface": parts[1] if len(parts) > 1 else "",
                    "remote_port": parts[-1] if len(parts) > 2 else "",
                })

    return {"neighbors": neighbors, "neighbor_count": len(neighbors)}


def _extract_show_interfaces(output: str) -> dict:
    """Extract interface blocks from show interfaces output."""
    interfaces = []
    current_iface = None

    for line in output.split("\n"):
        # Interface header line
        m = re.match(r"^(\S+)\s+is\s+(.*),\s*line protocol is\s+(\S+)", line)
        if m:
            if current_iface:
                interfaces.append(current_iface)
            current_iface = {
                "name": m.group(1),
                "admin_status": m.group(2).strip(),
                "oper_status": m.group(3),
            }
            continue

        if current_iface:
            # IP address
            m = re.search(r"Internet address is\s+(\S+)", line)
            if m:
                current_iface["ip_address"] = m.group(1)

            # MAC
            m = re.search(r"address is\s+([0-9a-f.]+)", line)
            if m:
                current_iface["mac_address"] = m.group(1)

            # MTU
            m = re.search(r"MTU\s+(\d+)\s+bytes", line)
            if m:
                current_iface["mtu"] = int(m.group(1))

    if current_iface:
        interfaces.append(current_iface)

    return {"interfaces": interfaces, "interface_count": len(interfaces)}


def _generic_extract(output: str) -> dict:
    """Generic field extraction for unknown commands."""
    return {
        "line_count": len(output.strip().split("\n")),
        "char_count": len(output),
    }


def diff_outputs(old_output: str, new_output: str, command: str, platform_name: str) -> dict:
    """Compare two versions of the same command output and detect structural changes.

    Returns diff analysis including whether a new parser is needed.
    """
    old_lines = old_output.strip().splitlines()
    new_lines = new_output.strip().splitlines()

    # Line-level diff
    differ = difflib.unified_diff(old_lines, new_lines, lineterm="", n=2)
    diff_lines = list(differ)

    added_lines = [l[1:] for l in diff_lines if l.startswith("+") and not l.startswith("+++")]
    removed_lines = [l[1:] for l in diff_lines if l.startswith("-") and not l.startswith("---")]

    # Extract fields from both versions
    old_fields = _extract_fields_regex(old_output, platform_name, command)["detected_fields"]
    new_fields = _extract_fields_regex(new_output, platform_name, command)["detected_fields"]

    # Determine structural change level
    old_keys = set(_flatten_keys(old_fields))
    new_keys = set(_flatten_keys(new_fields))
    added_keys = new_keys - old_keys
    removed_keys = old_keys - new_keys

    # Field value changes
    field_changes = []
    for key in old_keys & new_keys:
        old_val = _get_nested(old_fields, key)
        new_val = _get_nested(new_fields, key)
        if old_val != new_val:
            field_changes.append({
                "field": key,
                "old_value": str(old_val)[:100],
                "new_value": str(new_val)[:100],
            })

    # Determine parser compatibility
    structural_change = bool(added_keys or removed_keys)
    if structural_change and len(added_keys) > 2:
        parser_compat = "new_parser_needed"
    elif structural_change:
        parser_compat = "minor_change"
    elif field_changes:
        parser_compat = "compatible"
    else:
        parser_compat = "identical"

    # Generate diff summary
    summary_parts = []
    if added_keys:
        summary_parts.append(f"New fields: {', '.join(sorted(added_keys))}")
    if removed_keys:
        summary_parts.append(f"Removed fields: {', '.join(sorted(removed_keys))}")
    if field_changes:
        summary_parts.append(f"{len(field_changes)} field value(s) changed")
    if not summary_parts:
        summary_parts.append("Outputs are structurally identical")

    return {
        "structural_change": structural_change,
        "parser_compatibility": parser_compat,
        "added_fields": sorted(added_keys),
        "removed_fields": sorted(removed_keys),
        "field_changes": field_changes,
        "diff_summary": "; ".join(summary_parts),
        "added_lines_count": len(added_lines),
        "removed_lines_count": len(removed_lines),
        "diff_lines": diff_lines[:50],  # First 50 lines of unified diff
    }


def find_matching_versions(
    platform_name: str,
    command: str,
    raw_output: str,
    existing_entries: list[dict],
) -> list[dict]:
    """Find existing library entries that match the given output.

    Returns entries sorted by similarity, with match metadata.
    """
    matches = []
    new_fields = _extract_fields_regex(raw_output, platform_name, command)["detected_fields"]
    new_keys = set(_flatten_keys(new_fields))

    for entry in existing_entries:
        old_fields = {}
        if entry.get("parser_results", {}).get("regex_extract", {}).get("detected_fields"):
            old_fields = entry["parser_results"]["regex_extract"]["detected_fields"]
        old_keys = set(_flatten_keys(old_fields))

        # Calculate similarity
        if old_keys and new_keys:
            common = old_keys & new_keys
            similarity = len(common) / max(len(old_keys), len(new_keys))
        else:
            # Fall back to text similarity
            similarity = difflib.SequenceMatcher(None, entry.get("raw_output", ""), raw_output).ratio()

        matches.append({
            "entry_id": entry["id"],
            "version": entry["software_version"],
            "model": entry.get("device_model_name", ""),
            "similarity": round(similarity, 3),
            "fields_match": old_keys == new_keys,
            "recommendation": "use_existing_parser" if similarity > 0.8 else "review_parser" if similarity > 0.5 else "new_parser_likely",
        })

    matches.sort(key=lambda m: m["similarity"], reverse=True)
    return matches


def _flatten_keys(d: dict, prefix: str = "") -> list[str]:
    """Flatten nested dict keys into dot-notation strings."""
    keys = []
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys.extend(_flatten_keys(v, full_key))
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            # For lists of dicts, use the keys from the first element
            keys.extend(_flatten_keys(v[0], f"{full_key}[]"))
        else:
            keys.append(full_key)
    return keys


def _get_nested(d: dict, key: str) -> Any:
    """Get a value from a nested dict using dot notation."""
    parts = key.replace("[]", "").split(".")
    current = d
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and current:
            current = current[0].get(part) if isinstance(current[0], dict) else None
        else:
            return None
    return current

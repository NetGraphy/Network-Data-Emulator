"""Tests for SNMP OID tree building."""

from datetime import datetime, timezone

from snep.snmp.oid_tree import build_oid_tree, find_exact_oid, find_next_oid


def _make_test_state():
    now = datetime.now(timezone.utc)
    device = {
        "hostname": "test-router",
        "software_version": "17.06.05",
        "uptime_seconds": 86400,
        "uptime_reference": now,
    }
    interfaces = [
        {
            "name": "GigabitEthernet1/0/1",
            "short_name": "Gi1/0/1",
            "if_index": 1,
            "interface_type": "ethernet",
            "admin_status": "up",
            "oper_status": "up",
            "speed_mbps": 1000,
            "mtu": 1500,
            "mac_address": "aabb.cc01.0001",
            "description": "Uplink",
            "counter": {
                "in_octets": 1000000,
                "out_octets": 500000,
                "in_unicast_pkts": 10000,
                "out_unicast_pkts": 5000,
                "in_errors": 0,
                "out_errors": 0,
                "in_discards": 0,
                "out_discards": 0,
                "rate_in_bps": 100000000,
                "rate_out_bps": 50000000,
                "rate_reference": now,
            },
        }
    ]
    snmp_profile = {
        "sys_contact": "noc@example.com",
        "sys_name": "test-router",
        "sys_location": "Lab",
    }
    return device, interfaces, snmp_profile


def test_build_oid_tree():
    device, interfaces, snmp = _make_test_state()
    tree = build_oid_tree(device, interfaces, snmp)
    assert len(tree) > 0

    # Check sysName
    result = find_exact_oid(tree, "1.3.6.1.2.1.1.5.0")
    assert result is not None
    assert result[2] == "test-router"


def test_find_exact_oid():
    device, interfaces, snmp = _make_test_state()
    tree = build_oid_tree(device, interfaces, snmp)

    # ifDescr.1
    result = find_exact_oid(tree, "1.3.6.1.2.1.2.2.1.2.1")
    assert result is not None
    assert result[2] == "GigabitEthernet1/0/1"


def test_find_next_oid():
    device, interfaces, snmp = _make_test_state()
    tree = build_oid_tree(device, interfaces, snmp)

    # Next after sysDescr should be sysObjectID
    result = find_next_oid(tree, "1.3.6.1.2.1.1.1.0")
    assert result is not None
    assert result[0] == "1.3.6.1.2.1.1.2.0"


def test_find_next_oid_end():
    device, interfaces, snmp = _make_test_state()
    tree = build_oid_tree(device, interfaces, snmp)

    # Past the end of the tree
    result = find_next_oid(tree, "99.99.99.99")
    assert result is None


def test_oper_status_mapping():
    device, interfaces, snmp = _make_test_state()
    tree = build_oid_tree(device, interfaces, snmp)

    # ifOperStatus.1 should be 1 (up)
    result = find_exact_oid(tree, "1.3.6.1.2.1.2.2.1.8.1")
    assert result is not None
    assert result[2] == 1


def test_if_type_mapping():
    device, interfaces, snmp = _make_test_state()
    tree = build_oid_tree(device, interfaces, snmp)

    # ifType.1 should be 6 (ethernetCsmacd)
    result = find_exact_oid(tree, "1.3.6.1.2.1.2.2.1.3.1")
    assert result is not None
    assert result[2] == 6

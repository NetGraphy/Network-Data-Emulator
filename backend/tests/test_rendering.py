"""Tests for the rendering engine's command normalization and template filters."""

from snep.services.rendering import _normalize_command, _ip_only, _mac_cisco, _short_name


def test_normalize_show_version():
    assert _normalize_command("show version") == "show version"
    assert _normalize_command("sh ver") == "show version"
    assert _normalize_command("sh version") == "show version"


def test_normalize_show_ip_int_brief():
    assert _normalize_command("show ip interface brief") == "show ip interface brief"
    assert _normalize_command("sh ip int br") == "show ip interface brief"
    assert _normalize_command("sh ip int brief") == "show ip interface brief"


def test_normalize_cdp():
    assert _normalize_command("show cdp neighbors") == "show cdp neighbors"
    assert _normalize_command("sh cdp neigh") == "show cdp neighbors"
    assert _normalize_command("sh cdp neighbors detail") == "show cdp neighbors detail"


def test_normalize_interface_specific():
    assert _normalize_command("show interfaces GigabitEthernet1/0/1") == "show interfaces"
    assert _normalize_command("sh int Gi1/0/1") == "show interfaces"


def test_ip_only_filter():
    assert _ip_only("10.0.1.1/30") == "10.0.1.1"
    assert _ip_only("10.0.1.1") == "10.0.1.1"
    assert _ip_only(None) == "unassigned"


def test_mac_cisco_filter():
    assert _mac_cisco("aa:bb:cc:dd:ee:ff") == "aabb.ccdd.eeff"
    assert _mac_cisco("aabb.ccdd.eeff") == "aabb.ccdd.eeff"


def test_short_name_filter():
    assert _short_name("GigabitEthernet1/0/1") == "Gig 1/0/1"
    assert _short_name("Loopback0") == "Loo 0"
    assert _short_name("Vlan1") == "Vla 1"

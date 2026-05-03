"""Tests for cloud gateway routing helpers."""

import pytest

from snep.services.gateway import (
    build_ssh_gateway_info,
    is_cloud_gateway_mode,
    parse_gateway_username,
    resolve_route_key,
)
from snep.ssh import server as ssh_server


def test_parse_gateway_username():
    principal = parse_gateway_username("admin%core-rtr-01")

    assert principal is not None
    assert principal.credential_username == "admin"
    assert principal.route_key == "core-rtr-01"


@pytest.mark.parametrize("username", ["admin", "%core-rtr-01", "admin%", "admin%core%rtr"])
def test_parse_gateway_username_rejects_invalid_values(username):
    assert parse_gateway_username(username) is None


def test_parse_gateway_username_custom_delimiter():
    principal = parse_gateway_username("admin@core-rtr-01", delimiter="@")

    assert principal is not None
    assert principal.credential_username == "admin"
    assert principal.route_key == "core-rtr-01"


def test_parse_gateway_username_rejects_invalid_delimiter():
    with pytest.raises(ValueError):
        parse_gateway_username("admin%%core-rtr-01", delimiter="%%")


def test_resolve_route_key_exact_and_case_insensitive():
    devices = {"core-rtr-01": {"hostname": "core-rtr-01"}}

    assert resolve_route_key("core-rtr-01", devices) == {"hostname": "core-rtr-01"}
    assert resolve_route_key("CORE-RTR-01", devices) == {"hostname": "core-rtr-01"}
    assert resolve_route_key("missing", devices) is None


def test_build_ssh_gateway_info_uses_railway_tcp_proxy_port():
    info = build_ssh_gateway_info(
        "core-rtr-01",
        credential_username="admin",
        env={"connect_address": "ssh.proxy.rlwy.net", "tcp_proxy_port": "15140", "ssh_reachable": True},
    )

    assert info["host"] == "ssh.proxy.rlwy.net"
    assert info["port"] == 15140
    assert info["username"] == "admin%core-rtr-01"
    assert info["command"] == "ssh admin%core-rtr-01@ssh.proxy.rlwy.net -p 15140"
    assert info["available"] is True


def test_build_ssh_gateway_info_marks_unreachable():
    info = build_ssh_gateway_info(
        "core-rtr-01",
        env={"connect_address": "app.up.railway.app", "ssh_reachable": False},
    )

    assert info["host"] == "NOT_REACHABLE"
    assert info["command"] is None
    assert info["available"] is False


def test_is_cloud_gateway_mode_detects_railway():
    assert is_cloud_gateway_mode({"type": "cloud_railway_tcp"}) is True
    assert is_cloud_gateway_mode({"type": "docker"}) is False


class FakeSSHConnection:
    def __init__(self):
        self.extra_info = {}

    def set_extra_info(self, **kwargs):
        self.extra_info.update(kwargs)


def test_ssh_server_requires_password_auth_and_stashes_resolved_device():
    device = {
        "hostname": "core-rtr-01",
        "credentials": [{"username": "admin", "password": "cisco123"}],
        "default_credentials": {},
    }
    conn = FakeSSHConnection()
    server = ssh_server.SNEPSSHServer(device_info=device)
    server.connection_made(conn)

    assert server.begin_auth("admin") is True
    assert server.validate_password("admin", "cisco123") is True
    assert conn.extra_info["snep_device_info"] == device
    assert conn.extra_info["snep_username"] == "admin"


def test_gateway_ssh_server_resolves_device_from_username(monkeypatch):
    device = {
        "hostname": "core-rtr-01",
        "credentials": [{"username": "admin", "password": "cisco123"}],
        "default_credentials": {},
    }
    monkeypatch.setattr(ssh_server, "_device_by_hostname", {"core-rtr-01": device})
    conn = FakeSSHConnection()
    server = ssh_server.SNEPSSHServer(gateway_mode=True)
    server.connection_made(conn)

    assert server.begin_auth("admin%CORE-RTR-01") is True
    assert server.validate_password("admin%CORE-RTR-01", "cisco123") is True
    assert conn.extra_info["snep_device_info"] == device
    assert conn.extra_info["snep_username"] == "admin"

"""Environment detection — determines runtime context and connectivity parameters.

Detects whether SNEP is running in Docker, on Railway, natively, etc.
and resolves the correct address that external tools should use to connect.
"""

import os
import socket
from pathlib import Path

from snep.config import settings


def detect_environment() -> dict:
    """Detect runtime environment and return connectivity parameters.

    Returns:
        {
            "type": "docker" | "cloud_railway" | "native",
            "connect_address": str,  # what external tools use
            "listen_address": str,   # what servers bind to
            "note": str,
        }
    """
    # 1. Explicit override — highest priority
    if settings.networking.connect_address:
        return {
            "type": "configured",
            "connect_address": settings.networking.connect_address,
            "listen_address": settings.networking.bind_address,
            "note": f"Explicitly configured via SNEP_CONNECT_ADDRESS",
        }

    # 2. Railway cloud
    railway_domain = os.environ.get("RAILWAY_TCP_PROXY_DOMAIN") or os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    if railway_domain:
        return {
            "type": "cloud_railway",
            "connect_address": railway_domain,
            "listen_address": "0.0.0.0",
            "note": "Railway detected. SSH/SNMP require TCP proxy configuration in Railway.",
        }

    # 3. Docker container
    if _is_docker():
        connect = _resolve_docker_host()
        return {
            "type": "docker",
            "connect_address": connect,
            "listen_address": "0.0.0.0",
            "note": f"Docker container detected. Tools on the host connect to {connect}:<port>.",
        }

    # 4. Native — detect primary network interface IP
    primary_ip = _get_primary_ip()
    if settings.networking.mode == "loopback":
        return {
            "type": "native_loopback",
            "connect_address": "127.0.0.0/8",  # each device has its own IP
            "listen_address": "127.0.0.0/8",
            "note": "Native with loopback aliases. Each device has its own 127.x.x.x IP with standard ports.",
        }

    return {
        "type": "native",
        "connect_address": primary_ip,
        "listen_address": settings.networking.bind_address,
        "note": f"Native mode. Tools connect to {primary_ip}:<port>.",
    }


def get_connect_address() -> str:
    """Get the resolved connect address for external tool connectivity.

    This is the IP/hostname that should appear in Nornir inventories,
    Ansible inventories, and the UI connection info.
    """
    env = detect_environment()
    addr = env["connect_address"]

    # Never return 0.0.0.0 — it's not connectable
    if addr == "0.0.0.0":
        return "127.0.0.1"

    return addr


def _is_docker() -> bool:
    """Check if running inside a Docker container."""
    return (
        Path("/.dockerenv").exists()
        or os.environ.get("DOCKER_CONTAINER") == "true"
        or _check_cgroup_docker()
    )


def _check_cgroup_docker() -> bool:
    """Check /proc/1/cgroup for docker indicators."""
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read() or "containerd" in f.read()
    except (FileNotFoundError, PermissionError):
        return False


def _resolve_docker_host() -> str:
    """Resolve the Docker host address that containers can reach.

    Priority:
    1. host.docker.internal (Docker Desktop on Mac/Windows)
    2. Default gateway (Linux Docker)
    3. 127.0.0.1 fallback (tools on host use localhost + Docker port mapping)
    """
    # Try host.docker.internal (Docker Desktop)
    try:
        addr = socket.gethostbyname("host.docker.internal")
        if addr:
            # But external tools on the host use 127.0.0.1 via Docker port mapping
            # host.docker.internal resolves to the host IP from INSIDE the container
            # Tools OUTSIDE the container use 127.0.0.1 (or the host's real IP)
            pass
    except socket.gaierror:
        pass

    # For Docker: tools on the HOST connect via 127.0.0.1 + port mapping
    # The Docker port mapping (-p 10000:10000) makes container ports available on localhost
    return "127.0.0.1"


def _get_primary_ip() -> str:
    """Get the primary non-loopback IP address of this machine."""
    try:
        # Connect to a public DNS to find which interface is used for outbound traffic
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except (OSError, socket.error):
        pass

    # Fallback: enumerate interfaces
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip and not ip.startswith("127."):
            return ip
    except socket.gaierror:
        pass

    return "127.0.0.1"

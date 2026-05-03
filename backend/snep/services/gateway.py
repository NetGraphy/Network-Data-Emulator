"""Gateway routing helpers for cloud-friendly protocol endpoints."""

from dataclasses import dataclass

from snep.config import settings


@dataclass(frozen=True)
class GatewayPrincipal:
    """Parsed protocol credential containing both auth user and target route."""

    credential_username: str
    route_key: str


def parse_gateway_username(username: str, delimiter: str | None = None) -> GatewayPrincipal | None:
    """Parse SSH gateway usernames in the form ``user%device``.

    Returns ``None`` when the username is not a valid gateway principal.
    """
    delimiter = delimiter or settings.networking.ssh_gateway_delimiter
    if not delimiter or len(delimiter) != 1:
        raise ValueError("Gateway username delimiter must be a single character")

    if delimiter not in username:
        return None

    credential_username, route_key = username.split(delimiter, 1)
    if not credential_username or not route_key or delimiter in route_key:
        return None

    return GatewayPrincipal(credential_username=credential_username, route_key=route_key)


def resolve_route_key(route_key: str, devices_by_hostname: dict[str, dict]) -> dict | None:
    """Resolve a gateway route key to device info.

    Hostnames are unique in SNEP. Exact match wins; case-insensitive match is a
    convenience for operators typing gateway usernames by hand.
    """
    if route_key in devices_by_hostname:
        return devices_by_hostname[route_key]

    route_key_lower = route_key.lower()
    for hostname, device_info in devices_by_hostname.items():
        if hostname.lower() == route_key_lower:
            return device_info

    return None


def is_cloud_gateway_mode(env: dict | None = None) -> bool:
    """Return whether connection examples should prefer shared gateway routing."""
    if settings.networking.mode == "cloud_gateway":
        return True
    if env and str(env.get("type", "")).startswith("cloud_railway"):
        return True
    return False


def build_ssh_gateway_info(
    hostname: str,
    credential_username: str = "admin",
    env: dict | None = None,
    fallback_host: str = "127.0.0.1",
) -> dict:
    """Build client-facing SSH gateway connection details for one device."""
    host = (
        settings.networking.connect_hostname
        or (env or {}).get("connect_address")
        or settings.networking.connect_address
        or fallback_host
    )
    port = int((env or {}).get("tcp_proxy_port") or settings.networking.ssh_gateway_port)
    username = f"{credential_username}{settings.networking.ssh_gateway_delimiter}{hostname}"

    reachable = (env or {}).get("ssh_reachable", True) and host != "NOT_REACHABLE"
    command = f"ssh {username}@{host} -p {port}" if reachable else None

    return {
        "mode": "gateway",
        "host": host if reachable else "NOT_REACHABLE",
        "port": port,
        "username": username,
        "route_key": hostname,
        "command": command,
        "available": bool(reachable),
    }

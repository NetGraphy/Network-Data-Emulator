"""SSH emulation server — supports two modes:

1. Port-per-device: Each device binds its own port (local Docker, native)
2. Gateway mode: Single port, device selected via username prefix (cloud/Railway)
   Format: ssh admin%core-rtr-01@host -p PORT
   The % separates the credential username from the target device hostname.

Both modes run simultaneously when a gateway port is configured.
"""

import asyncio
import logging
import os
from pathlib import Path

import asyncssh
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from snep.config import settings
from snep.db import async_session_factory
from snep.models import ConnectionMapping, Device, DeviceModel
from snep.services.gateway import parse_gateway_username, resolve_route_key
from snep.ssh.session import CLISession

logger = logging.getLogger(__name__)

# All devices indexed by hostname for gateway routing
_device_by_hostname: dict[str, dict] = {}
# All devices indexed by (address, port) for port-per-device routing
_device_by_endpoint: dict[tuple, dict] = {}


class SNEPSSHServer(asyncssh.SSHServer):
    """SSH server that authenticates against device credentials.

    Supports two username formats:
    - "admin" — standard, device determined by port binding
    - "admin%core-rtr-01" — gateway mode, device encoded in username
    """

    def __init__(self, device_info: dict | None = None, gateway_mode: bool = False):
        self._device_info = device_info
        self._gateway_mode = gateway_mode
        self._resolved_device = None
        self._resolved_username = None

    def connection_made(self, conn):
        self._conn = conn

    def begin_auth(self, username):
        if self._gateway_mode:
            principal = parse_gateway_username(username)
            if principal:
                self._resolved_device = resolve_route_key(principal.route_key, _device_by_hostname)
                self._resolved_username = principal.credential_username
                if not self._resolved_device:
                    logger.warning("Gateway: unknown device route key '%s'", principal.route_key)
            else:
                self._resolved_username = username
                self._resolved_device = None
        else:
            self._resolved_username = username
            self._resolved_device = self._device_info
        return True

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        device = self._resolved_device
        if not device:
            return False

        actual_user = self._resolved_username or username

        authenticated = False
        for cred in device.get("credentials", []):
            if cred["username"] == actual_user and cred["password"] == password:
                authenticated = True
                break
        defaults = device.get("default_credentials", {})
        if not authenticated and defaults.get("username") == actual_user and defaults.get("password") == password:
            authenticated = True

        if authenticated:
            self._conn.set_extra_info(snep_device_info=device, snep_username=actual_user)

        return authenticated


async def _load_device_map() -> None:
    """Load all connection mappings and device info from database into memory."""
    global _device_by_hostname, _device_by_endpoint

    async with async_session_factory() as session:
        result = await session.execute(
            select(ConnectionMapping)
            .options(
                selectinload(ConnectionMapping.device).selectinload(Device.credentials),
                selectinload(ConnectionMapping.device)
                .selectinload(Device.device_model)
                .selectinload(DeviceModel.platform),
            )
            .where(ConnectionMapping.protocol == "ssh")
        )
        mappings = result.scalars().all()

        for mapping in mappings:
            device = mapping.device
            if not device or device.admin_state == "decommissioned":
                continue

            platform = device.device_model.platform if device.device_model else None
            info = {
                "device_id": str(device.id),
                "hostname": device.hostname,
                "platform_name": platform.name if platform else "cisco_ios",
                "credentials": [{"username": c.username, "password": c.password} for c in device.credentials],
                "enable_password": next((c.enable_password for c in device.credentials if c.enable_password), None),
                "privilege_level": max((c.privilege_level for c in device.credentials), default=1),
                "default_credentials": platform.default_credentials
                if platform
                else {"username": "admin", "password": "admin"},
                "listen_address": mapping.listen_address,
                "listen_port": mapping.listen_port,
            }

            _device_by_hostname[device.hostname] = info
            _device_by_endpoint[(mapping.listen_address, mapping.listen_port)] = info

    logger.info(f"Loaded {len(_device_by_hostname)} devices for SSH")


async def _start_per_device_servers(host_key_path: str):
    """Start one SSH listener per device (port-per-device mode)."""
    for key, device_info in _device_by_endpoint.items():
        addr = device_info["listen_address"]
        port = device_info["listen_port"]

        def make_factory(di):
            def factory():
                return SNEPSSHServer(device_info=di, gateway_mode=False)

            return factory

        async def make_handler(di):
            async def handler(process):
                cli = CLISession(di, async_session_factory)
                await cli.handle_session(process)

            return handler

        try:
            handler = await make_handler(device_info)
            await asyncssh.create_server(
                make_factory(device_info),
                host=addr if addr != "0.0.0.0" else "",
                port=port,
                server_host_keys=[host_key_path],
                process_factory=handler,
            )
            logger.info(f"SSH [{device_info['hostname']}] on {addr}:{port}")
        except OSError as e:
            logger.error(f"Failed to bind SSH on {addr}:{port} for {device_info['hostname']}: {e}")


async def _start_gateway_server(host_key_path: str, port: int):
    """Start a single SSH gateway that routes by username prefix.

    Usage: ssh admin%core-rtr-01@host -p PORT
    """

    def gateway_factory():
        return SNEPSSHServer(device_info=None, gateway_mode=True)

    async def gateway_handler(process):
        device_info = process.get_extra_info("snep_device_info")

        if not device_info:
            # List available devices
            hostnames = sorted(_device_by_hostname.keys())
            process.stdout.write("\n*** SNEP SSH Gateway ***\n\n")
            process.stdout.write("No device specified. Use: ssh <user>%<hostname>@<host> -p <port>\n\n")
            process.stdout.write("Available devices:\n")
            for h in hostnames:
                process.stdout.write(f"  ssh admin%{h}@<host> -p {port}\n")
            process.stdout.write("\n")
            process.exit(1)
            return

        cli = CLISession(device_info, async_session_factory)
        await cli.handle_session(process)

    try:
        await asyncssh.create_server(
            gateway_factory,
            host="",
            port=port,
            server_host_keys=[host_key_path],
            process_factory=gateway_handler,
        )
        logger.info(f"SSH Gateway listening on port {port} ({len(_device_by_hostname)} devices)")
        logger.info(f"  Usage: ssh admin%<hostname>@<host> -p {port}")
    except OSError as e:
        logger.error(f"Failed to bind SSH gateway on port {port}: {e}")


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logger.info("Starting SNEP SSH Emulation Service")

    # Generate host key
    host_key_path = settings.ssh_host_key_path
    if not Path(host_key_path).exists():
        logger.info(f"Generating SSH host key at {host_key_path}")
        os.makedirs(Path(host_key_path).parent, exist_ok=True)
        key = asyncssh.generate_private_key("ssh-rsa", 2048)
        key.write_private_key(host_key_path)

    # Wait for DB
    for attempt in range(30):
        try:
            await _load_device_map()
            break
        except Exception as e:
            if attempt < 29:
                logger.warning(f"Waiting for database... ({e})")
                await asyncio.sleep(2)
            else:
                raise

    if not _device_by_hostname:
        logger.warning("No SSH connection mappings found. Run 'make seed' first.")
        await asyncio.Event().wait()
        return

    # Start per-device servers (always, for local/Docker use)
    await _start_per_device_servers(host_key_path)

    if settings.networking.ssh_gateway_enabled:
        await _start_gateway_server(host_key_path, settings.networking.ssh_gateway_port)

    logger.info("All SSH servers started. Waiting for connections...")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

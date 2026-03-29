"""SSH emulation server — binds to configured addresses and dispatches connections to devices."""

import asyncio
import logging
import os
from pathlib import Path

import asyncssh
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from snep.config import settings
from snep.db import async_session_factory
from snep.models import ConnectionMapping, Device, DeviceCredential, DeviceModel
from snep.ssh.session import CLISession

logger = logging.getLogger(__name__)


class SNEPSSHServer(asyncssh.SSHServer):
    """SSH server that authenticates against device credentials."""

    def __init__(self, device_info: dict):
        self._device_info = device_info
        self._credentials = device_info.get("credentials", [])

    def connection_made(self, conn):
        self._conn = conn

    def begin_auth(self, username):
        # Return False to indicate auth is required
        return False

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        for cred in self._credentials:
            if cred["username"] == username and cred["password"] == password:
                return True
        # Fall back to platform defaults
        defaults = self._device_info.get("default_credentials", {})
        if defaults.get("username") == username and defaults.get("password") == password:
            return True
        return False


async def _load_device_map() -> dict:
    """Load all connection mappings and device info from database."""
    device_map = {}

    async with async_session_factory() as session:
        result = await session.execute(
            select(ConnectionMapping)
            .options(
                selectinload(ConnectionMapping.device)
                .selectinload(Device.credentials),
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

            key = (mapping.listen_address, mapping.listen_port)
            platform = device.device_model.platform if device.device_model else None

            device_map[key] = {
                "device_id": str(device.id),
                "hostname": device.hostname,
                "platform_name": platform.name if platform else "cisco_ios",
                "credentials": [
                    {"username": c.username, "password": c.password}
                    for c in device.credentials
                ],
                "enable_password": next(
                    (c.enable_password for c in device.credentials if c.enable_password), None
                ),
                "privilege_level": max(
                    (c.privilege_level for c in device.credentials), default=1
                ),
                "default_credentials": platform.default_credentials if platform else {"username": "admin", "password": "admin"},
                "listen_address": mapping.listen_address,
                "listen_port": mapping.listen_port,
            }

    return device_map


async def _start_ssh_server(device_info: dict, host_key_path: str):
    """Start an SSH server for a single device binding."""
    addr = device_info["listen_address"]
    port = device_info["listen_port"]

    def server_factory():
        return SNEPSSHServer(device_info)

    async def session_handler(process):
        cli = CLISession(device_info, async_session_factory)
        await cli.handle_session(process)

    try:
        await asyncssh.create_server(
            server_factory,
            host=addr if addr != "0.0.0.0" else "",
            port=port,
            server_host_keys=[host_key_path],
            process_factory=session_handler,
        )
        logger.info(f"SSH server for {device_info['hostname']} listening on {addr}:{port}")
    except OSError as e:
        logger.error(f"Failed to bind SSH on {addr}:{port} for {device_info['hostname']}: {e}")


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logger.info("Starting SNEP SSH Emulation Service")

    # Generate host key if it doesn't exist
    host_key_path = settings.ssh_host_key_path
    if not Path(host_key_path).exists():
        logger.info(f"Generating SSH host key at {host_key_path}")
        os.makedirs(Path(host_key_path).parent, exist_ok=True)
        key = asyncssh.generate_private_key("ssh-rsa", 2048)
        key.write_private_key(host_key_path)

    # Wait for DB to be ready
    for attempt in range(30):
        try:
            device_map = await _load_device_map()
            break
        except Exception as e:
            if attempt < 29:
                logger.warning(f"Waiting for database... ({e})")
                await asyncio.sleep(2)
            else:
                logger.error("Failed to connect to database after 30 attempts")
                raise

    if not device_map:
        logger.warning("No SSH connection mappings found. Run 'make seed' first.")
        # Keep running so container doesn't exit
        await asyncio.Event().wait()
        return

    logger.info(f"Loaded {len(device_map)} device SSH mappings")

    # Start SSH servers
    tasks = []
    for key, device_info in device_map.items():
        tasks.append(_start_ssh_server(device_info, host_key_path))

    await asyncio.gather(*tasks)
    logger.info(f"All {len(tasks)} SSH servers started")

    # Keep running
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

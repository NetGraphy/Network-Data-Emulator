"""SNMP emulation server — async UDP listener for SNMPv2c/v3 requests."""

import asyncio
import logging
import struct

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from snep.config import settings
from snep.db import async_session_factory
from snep.models import ConnectionMapping, Device, DeviceModel, Interface, InterfaceCounter, SNMPProfile
from snep.snmp.handler import handle_snmp_packet

logger = logging.getLogger(__name__)


class SNMPProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for SNMP requests."""

    def __init__(self, device_map: dict):
        self._device_map = device_map

    def connection_made(self, transport):
        self._transport = transport

    def datagram_received(self, data: bytes, addr: tuple):
        """Handle incoming SNMP packet."""
        # Determine which device this is for based on the socket's local address
        local_addr = self._transport.get_extra_info("sockname")
        device_key = (local_addr[0], local_addr[1]) if local_addr else None

        # Try to find device by local port
        device_info = None
        for key, info in self._device_map.items():
            if key[1] == local_addr[1]:
                device_info = info
                break

        if not device_info:
            return  # No device mapped to this port

        # Process SNMP request
        response = handle_snmp_packet(data, device_info)
        if response:
            self._transport.sendto(response, addr)


async def _load_device_map() -> dict:
    """Load SNMP connection mappings and build device state for OID trees."""
    device_map = {}

    async with async_session_factory() as session:
        result = await session.execute(
            select(ConnectionMapping)
            .options(
                selectinload(ConnectionMapping.device)
                .selectinload(Device.interfaces)
                .selectinload(Interface.counter),
                selectinload(ConnectionMapping.device)
                .selectinload(Device.snmp_profile),
                selectinload(ConnectionMapping.device)
                .selectinload(Device.device_model)
                .selectinload(DeviceModel.platform),
            )
            .where(ConnectionMapping.protocol == "snmp")
        )
        mappings = result.scalars().all()

        for mapping in mappings:
            device = mapping.device
            if not device or device.admin_state == "decommissioned":
                continue

            key = (mapping.listen_address, mapping.listen_port)

            # Build interface data for OID tree
            interfaces_data = []
            for iface in sorted(device.interfaces, key=lambda i: i.sort_order):
                iface_dict = {
                    "name": iface.name,
                    "short_name": iface.short_name,
                    "if_index": iface.if_index,
                    "interface_type": iface.interface_type,
                    "admin_status": iface.admin_status,
                    "oper_status": iface.oper_status,
                    "speed_mbps": iface.speed_mbps,
                    "mtu": iface.mtu,
                    "mac_address": iface.mac_address,
                    "description": iface.description,
                }
                if iface.counter:
                    iface_dict["counter"] = {
                        "in_octets": iface.counter.in_octets,
                        "out_octets": iface.counter.out_octets,
                        "in_unicast_pkts": iface.counter.in_unicast_pkts,
                        "out_unicast_pkts": iface.counter.out_unicast_pkts,
                        "in_errors": iface.counter.in_errors,
                        "out_errors": iface.counter.out_errors,
                        "in_discards": iface.counter.in_discards,
                        "out_discards": iface.counter.out_discards,
                        "rate_in_bps": iface.counter.rate_in_bps,
                        "rate_out_bps": iface.counter.rate_out_bps,
                        "rate_reference": iface.counter.rate_reference,
                    }
                interfaces_data.append(iface_dict)

            snmp_data = None
            if device.snmp_profile:
                sp = device.snmp_profile
                snmp_data = {
                    "v2_community": sp.v2_community,
                    "v3_username": sp.v3_username,
                    "sys_descr": sp.sys_descr,
                    "sys_contact": sp.sys_contact,
                    "sys_name": sp.sys_name or device.hostname,
                    "sys_location": sp.sys_location,
                }

            device_map[key] = {
                "device_id": str(device.id),
                "hostname": device.hostname,
                "software_version": device.software_version or (
                    device.device_model.software_version if device.device_model else "17.06.05"
                ),
                "uptime_seconds": device.uptime_seconds,
                "uptime_reference": device.uptime_reference,
                "interfaces": interfaces_data,
                "snmp_profile": snmp_data,
                "listen_address": mapping.listen_address,
                "listen_port": mapping.listen_port,
            }

    return device_map


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logger.info("Starting SNEP SNMP Emulation Service")

    # Wait for DB
    for attempt in range(30):
        try:
            device_map = await _load_device_map()
            break
        except Exception as e:
            if attempt < 29:
                logger.warning(f"Waiting for database... ({e})")
                await asyncio.sleep(2)
            else:
                raise

    if not device_map:
        logger.warning("No SNMP connection mappings found. Run 'make seed' first.")
        await asyncio.Event().wait()
        return

    logger.info(f"Loaded {len(device_map)} device SNMP mappings")

    # Create UDP listeners
    loop = asyncio.get_event_loop()
    transports = []

    for key, device_info in device_map.items():
        addr = device_info["listen_address"]
        port = device_info["listen_port"]
        try:
            transport, protocol = await loop.create_datagram_endpoint(
                lambda di=device_info: SNMPProtocol({(di["listen_address"], di["listen_port"]): di}),
                local_addr=(addr if addr != "0.0.0.0" else "0.0.0.0", port),
            )
            transports.append(transport)
            logger.info(f"SNMP listener for {device_info['hostname']} on {addr}:{port}")
        except OSError as e:
            logger.error(f"Failed to bind SNMP on {addr}:{port}: {e}")

    logger.info(f"All {len(transports)} SNMP listeners started")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

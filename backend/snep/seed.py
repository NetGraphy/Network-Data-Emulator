"""Seed data — creates platforms, models, devices, interfaces, links, and connection mappings."""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snep.db import async_session_factory, engine
from snep.models import (
    Base,
    ConnectionMapping,
    Device,
    DeviceCredential,
    DeviceModel,
    Interface,
    InterfaceCounter,
    Link,
    Platform,
    SNMPProfile,
)

NOW = datetime.now(timezone.utc)

# Fixed UUIDs for deterministic seeding
PLATFORM_IOS_ID = uuid.UUID("a1b2c3d4-0001-0001-0001-000000000001")
PLATFORM_EOS_ID = uuid.UUID("a1b2c3d4-0001-0001-0001-000000000002")
MODEL_C9300_ID = uuid.UUID("b2c3d4e5-0002-0002-0002-000000000001")
MODEL_7050_ID = uuid.UUID("b2c3d4e5-0002-0002-0002-000000000002")

DEVICE_IDS = [uuid.UUID(f"c3d4e5f6-0003-0003-0003-00000000000{i}") for i in range(1, 6)]

IOS_CLI_MODES = {
    "user_exec": {"prompt_char": ">", "transitions": {"enable": "privileged_exec"}},
    "privileged_exec": {
        "prompt_char": "#",
        "transitions": {"configure terminal": "global_config", "disable": "user_exec"},
    },
    "global_config": {
        "prompt_char": "(config)#",
        "transitions": {"exit": "privileged_exec", "end": "privileged_exec", "interface": "interface_config"},
    },
    "interface_config": {
        "prompt_char": "(config-if)#",
        "transitions": {"exit": "global_config", "end": "privileged_exec"},
    },
}

EOS_CLI_MODES = {
    "user_exec": {"prompt_char": ">", "transitions": {"enable": "privileged_exec"}},
    "privileged_exec": {
        "prompt_char": "#",
        "transitions": {"configure terminal": "global_config", "configure": "global_config", "disable": "user_exec"},
    },
    "global_config": {
        "prompt_char": "(config)#",
        "transitions": {"exit": "privileged_exec", "end": "privileged_exec", "interface": "interface_config"},
    },
    "interface_config": {
        "prompt_char": "(config-if-%iface%)#",
        "transitions": {"exit": "global_config", "end": "privileged_exec"},
    },
}

DEVICES_DATA = [
    {"hostname": "core-rtr-01", "mgmt_ip": "10.1.1.1", "serial": "FCW2145L0RN", "role": "core", "site": "dc-east", "model_id": MODEL_C9300_ID},
    {"hostname": "core-rtr-02", "mgmt_ip": "10.1.1.2", "serial": "FCW2145L0RP", "role": "core", "site": "dc-east", "model_id": MODEL_C9300_ID},
    {"hostname": "dist-sw-01", "mgmt_ip": "10.1.2.1", "serial": "FCW2251M1AB", "role": "distribution", "site": "dc-east", "model_id": MODEL_C9300_ID},
    {"hostname": "dist-sw-02", "mgmt_ip": "10.1.2.2", "serial": "FCW2251M1AC", "role": "distribution", "site": "dc-east", "model_id": MODEL_C9300_ID},
    {"hostname": "access-sw-01", "mgmt_ip": "10.1.3.1", "serial": "FCW2367N2XY", "role": "access", "site": "dc-east", "model_id": MODEL_C9300_ID},
]


def _mac(device_idx: int, iface_idx: int) -> str:
    return f"aabb.cc{device_idx:02x}.{iface_idx:04x}"


def _create_interfaces(device_id: uuid.UUID, device_idx: int) -> tuple[list[Interface], list[InterfaceCounter]]:
    interfaces = []
    counters = []
    idx = 1

    # 4 GigabitEthernet uplink ports
    for port in range(1, 5):
        iface = Interface(
            id=uuid.uuid5(device_id, f"Gi1/0/{port}"),
            device_id=device_id,
            name=f"GigabitEthernet1/0/{port}",
            short_name=f"Gi1/0/{port}",
            if_index=idx,
            interface_type="ethernet",
            admin_status="up",
            oper_status="up",
            speed_mbps=1000,
            duplex="full",
            mtu=1500,
            mac_address=_mac(device_idx, idx),
            ip_address=f"10.0.{device_idx}.{port * 4 - 3}/30" if port <= 2 else None,
            description=f"Uplink port {port}",
            last_input="00:00:03",
            last_output="00:00:01",
            last_state_change=NOW,
            sort_order=idx,
        )
        interfaces.append(iface)
        counters.append(InterfaceCounter(
            id=uuid.uuid5(iface.id, "counter"),
            interface_id=iface.id,
            in_octets=584_792_031_847 + idx * 1_000_000,
            out_octets=291_034_958_271 + idx * 500_000,
            in_unicast_pkts=4_839_201_748,
            out_unicast_pkts=2_419_384_751,
            in_multicast_pkts=12_847,
            out_multicast_pkts=8_471,
            in_broadcast_pkts=847,
            out_broadcast_pkts=423,
            rate_in_bps=450_000_000,
            rate_out_bps=225_000_000,
            rate_reference=NOW,
            updated_at=NOW,
        ))
        idx += 1

    # Loopback0
    lo_iface = Interface(
        id=uuid.uuid5(device_id, "Loopback0"),
        device_id=device_id,
        name="Loopback0",
        short_name="Lo0",
        if_index=idx,
        interface_type="loopback",
        admin_status="up",
        oper_status="up",
        speed_mbps=0,
        mtu=65535,
        mac_address="0000.0000.0000",
        ip_address=f"10.255.{device_idx}.1/32",
        last_state_change=NOW,
        sort_order=idx,
    )
    interfaces.append(lo_iface)
    counters.append(InterfaceCounter(
        id=uuid.uuid5(lo_iface.id, "counter"),
        interface_id=lo_iface.id,
        rate_in_bps=0,
        rate_out_bps=0,
        rate_reference=NOW,
        updated_at=NOW,
    ))
    idx += 1

    # Vlan1
    vlan_iface = Interface(
        id=uuid.uuid5(device_id, "Vlan1"),
        device_id=device_id,
        name="Vlan1",
        short_name="Vl1",
        if_index=idx,
        interface_type="vlan",
        admin_status="up",
        oper_status="up",
        speed_mbps=1000,
        mtu=1500,
        mac_address=_mac(device_idx, 99),
        ip_address=DEVICES_DATA[device_idx - 1]["mgmt_ip"] + "/24",
        last_state_change=NOW,
        sort_order=idx,
    )
    interfaces.append(vlan_iface)
    counters.append(InterfaceCounter(
        id=uuid.uuid5(vlan_iface.id, "counter"),
        interface_id=vlan_iface.id,
        rate_in_bps=100_000_000,
        rate_out_bps=50_000_000,
        rate_reference=NOW,
        updated_at=NOW,
    ))

    return interfaces, counters


async def seed(session: AsyncSession) -> None:
    # Check if already seeded
    result = await session.execute(select(Platform).limit(1))
    if result.scalar_one_or_none():
        print("Database already seeded, skipping.")
        return

    # Platforms
    ios = Platform(
        id=PLATFORM_IOS_ID,
        name="cisco_ios",
        display_name="Cisco IOS",
        vendor="Cisco",
        prompt_template="{hostname}{mode_char}",
        error_template="% Invalid input detected at '^' marker.\n\n{hostname}{mode_char}",
        cli_modes=IOS_CLI_MODES,
        default_credentials={"username": "admin", "password": "admin"},
    )
    eos = Platform(
        id=PLATFORM_EOS_ID,
        name="arista_eos",
        display_name="Arista EOS",
        vendor="Arista",
        prompt_template="{hostname}{mode_char}",
        error_template="% Invalid input\n{hostname}{mode_char}",
        cli_modes=EOS_CLI_MODES,
        default_credentials={"username": "admin", "password": "admin"},
    )
    session.add_all([ios, eos])

    # Device Models
    c9300 = DeviceModel(
        id=MODEL_C9300_ID,
        platform_id=PLATFORM_IOS_ID,
        name="catalyst_9300_48t",
        display_name="Cisco Catalyst 9300-48T",
        software_version="17.06.05",
        default_interface_pattern=[
            {"prefix": "GigabitEthernet1/0/", "range": [1, 48], "type": "ethernet", "speed": 1000},
            {"prefix": "Loopback", "range": [0, 0], "type": "loopback", "speed": 0},
            {"prefix": "Vlan", "range": [1, 1], "type": "vlan", "speed": 0},
        ],
        hardware_details={
            "chassis": "C9300-48T",
            "serial_prefix": "FCW",
            "memory_mb": 8192,
            "flash_mb": 16384,
        },
    )
    a7050 = DeviceModel(
        id=MODEL_7050_ID,
        platform_id=PLATFORM_EOS_ID,
        name="7050x3_48yc8",
        display_name="Arista 7050X3-48YC8",
        software_version="4.32.2F",
        default_interface_pattern=[
            {"prefix": "Ethernet", "range": [1, 48], "type": "ethernet", "speed": 25000},
            {"prefix": "Loopback", "range": [0, 0], "type": "loopback", "speed": 0},
            {"prefix": "Management", "range": [1, 1], "type": "management", "speed": 1000},
        ],
        hardware_details={
            "chassis": "DCS-7050CX3-32S",
            "serial_prefix": "JPE",
            "memory_mb": 16384,
            "flash_mb": 32768,
        },
    )
    session.add_all([c9300, a7050])

    # Devices, Interfaces, Counters, Credentials, SNMP Profiles, Connection Mappings
    all_interfaces = {}
    port_offset = 0

    for i, dev_data in enumerate(DEVICES_DATA):
        device = Device(
            id=DEVICE_IDS[i],
            device_model_id=dev_data["model_id"],
            hostname=dev_data["hostname"],
            management_ip=dev_data["mgmt_ip"],
            serial_number=dev_data["serial"],
            uptime_seconds=7_776_000 + i * 86400,
            uptime_reference=NOW,
            admin_state="active",
            tags={"site": dev_data["site"], "role": dev_data["role"]},
        )
        session.add(device)

        # Credential
        session.add(DeviceCredential(
            device_id=DEVICE_IDS[i],
            username="admin",
            password="cisco123",
            enable_password="enable456",
            privilege_level=1,
        ))

        # SNMP Profile
        session.add(SNMPProfile(
            device_id=DEVICE_IDS[i],
            v2_enabled=True,
            v2_community="public",
            v3_enabled=True,
            v3_username="snmpuser",
            v3_auth_protocol="sha256",
            v3_auth_password="authpass123",
            v3_priv_protocol="aes128",
            v3_priv_password="privpass456",
            sys_contact="noc@example.com",
            sys_location=f"DC-East Rack A{14 + i}",
        ))

        # Interfaces + Counters
        interfaces, counters = _create_interfaces(DEVICE_IDS[i], i + 1)
        session.add_all(interfaces)
        session.add_all(counters)
        all_interfaces[dev_data["hostname"]] = interfaces

        # Connection Mappings (port-multiplex model)
        session.add(ConnectionMapping(
            device_id=DEVICE_IDS[i],
            protocol="ssh",
            listen_address="0.0.0.0",
            listen_port=10000 + port_offset,
        ))
        session.add(ConnectionMapping(
            device_id=DEVICE_IDS[i],
            protocol="snmp",
            listen_address="0.0.0.0",
            listen_port=20000 + port_offset,
        ))
        port_offset += 1

    await session.flush()

    # Links — core-rtr-01 Gi1/0/1 <-> dist-sw-01 Gi1/0/1
    session.add(Link(
        interface_a_id=all_interfaces["core-rtr-01"][0].id,  # Gi1/0/1
        interface_b_id=all_interfaces["dist-sw-01"][0].id,
        link_type="physical",
        discovery_protocol="cdp",
        admin_state="up",
    ))
    # core-rtr-01 Gi1/0/2 <-> dist-sw-02 Gi1/0/1
    session.add(Link(
        interface_a_id=all_interfaces["core-rtr-01"][1].id,  # Gi1/0/2
        interface_b_id=all_interfaces["dist-sw-02"][0].id,
        link_type="physical",
        discovery_protocol="cdp",
        admin_state="up",
    ))
    # core-rtr-02 Gi1/0/1 <-> dist-sw-01 Gi1/0/2
    session.add(Link(
        interface_a_id=all_interfaces["core-rtr-02"][0].id,
        interface_b_id=all_interfaces["dist-sw-01"][1].id,
        link_type="physical",
        discovery_protocol="cdp",
        admin_state="up",
    ))
    # core-rtr-02 Gi1/0/2 <-> dist-sw-02 Gi1/0/2
    session.add(Link(
        interface_a_id=all_interfaces["core-rtr-02"][1].id,
        interface_b_id=all_interfaces["dist-sw-02"][1].id,
        link_type="physical",
        discovery_protocol="cdp",
        admin_state="up",
    ))
    # dist-sw-01 Gi1/0/3 <-> access-sw-01 Gi1/0/1
    session.add(Link(
        interface_a_id=all_interfaces["dist-sw-01"][2].id,  # Gi1/0/3
        interface_b_id=all_interfaces["access-sw-01"][0].id,
        link_type="physical",
        discovery_protocol="cdp",
        admin_state="up",
    ))

    await session.commit()
    print(f"Seeded {len(DEVICES_DATA)} devices with interfaces, links, and connection mappings.")


async def main():
    async with async_session_factory() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())

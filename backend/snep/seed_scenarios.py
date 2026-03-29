"""Seed pre-built scenarios — ready-to-run fault simulations."""

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snep.db import async_session_factory
from snep.models import Device, Interface, Link, Scenario, ScenarioEvent


async def seed_scenarios(session: AsyncSession) -> None:
    # Check if already seeded
    result = await session.execute(select(Scenario).limit(1))
    if result.scalar_one_or_none():
        print("Scenarios already seeded, skipping.")
        return

    # Load devices and interfaces by hostname
    devices = {}
    for row in (await session.execute(select(Device))).scalars().all():
        devices[row.hostname] = row

    interfaces = {}
    for row in (await session.execute(select(Interface))).scalars().all():
        interfaces[(str(row.device_id), row.name)] = row

    links = (await session.execute(select(Link))).scalars().all()

    core1 = devices.get("core-rtr-01")
    core2 = devices.get("core-rtr-02")
    dist1 = devices.get("dist-sw-01")
    access1 = devices.get("access-sw-01")

    if not core1 or not dist1:
        print("Seed devices not found, skipping scenario seed.")
        return

    core1_gi1 = interfaces.get((str(core1.id), "GigabitEthernet1/0/1"))
    core1_gi2 = interfaces.get((str(core1.id), "GigabitEthernet1/0/2"))

    # Find the link between core1 Gi1/0/1 and dist-sw-01
    core1_dist1_link = None
    for lk in links:
        if core1_gi1 and (str(lk.interface_a_id) == str(core1_gi1.id) or str(lk.interface_b_id) == str(core1_gi1.id)):
            core1_dist1_link = lk
            break

    # === Scenario 1: Uplink Failure ===
    s1 = Scenario(
        name="Uplink Failure — Core to Distribution",
        description="Simulates a fiber cut on the core-rtr-01 uplink to dist-sw-01. "
                    "Interface goes down, counters freeze, neighbor lost on both sides. "
                    "After 30 seconds, the link is restored.",
        status="ready", is_repeatable=True,
    )
    session.add(s1)
    await session.flush()

    if core1_gi1:
        # Event 1: Interface goes down (immediate)
        session.add(ScenarioEvent(
            scenario_id=s1.id, sequence_order=1,
            trigger_type="immediate", trigger_config={},
            action_type="interface_state_change",
            action_config={"interface_id": str(core1_gi1.id), "oper_status": "down"},
            rollback_action={"action_type": "interface_state_change",
                             "action_config": {"interface_id": str(core1_gi1.id), "oper_status": "up"}},
        ))

        # Event 2: CRC errors spike (5s delay)
        session.add(ScenarioEvent(
            scenario_id=s1.id, sequence_order=2,
            trigger_type="delay", trigger_config={"delay_seconds": 5},
            action_type="counter_set",
            action_config={"interface_id": str(core1_gi1.id), "counter_name": "crc_errors", "value": 4271},
            rollback_action={"action_type": "counter_set",
                             "action_config": {"interface_id": str(core1_gi1.id), "counter_name": "crc_errors", "value": 0}},
        ))

        # Event 3: Restore (30s delay)
        session.add(ScenarioEvent(
            scenario_id=s1.id, sequence_order=3,
            trigger_type="delay", trigger_config={"delay_seconds": 30},
            action_type="interface_state_change",
            action_config={"interface_id": str(core1_gi1.id), "oper_status": "up"},
        ))

    # === Scenario 2: Device Reload ===
    s2 = Scenario(
        name="Device Reload — Core Router 02",
        description="Simulates core-rtr-02 going down for maintenance. "
                    "All interfaces drop, all neighbors see loss. "
                    "Device comes back after 60 seconds.",
        status="ready", is_repeatable=True,
    )
    session.add(s2)
    await session.flush()

    if core2:
        # Event 1: Device goes to maintenance
        session.add(ScenarioEvent(
            scenario_id=s2.id, sequence_order=1,
            trigger_type="immediate", trigger_config={},
            action_type="device_state_change",
            action_config={"device_id": str(core2.id), "admin_state": "maintenance"},
            rollback_action={"action_type": "device_state_change",
                             "action_config": {"device_id": str(core2.id), "admin_state": "active"}},
        ))

        # Event 2: Device comes back (60s delay)
        session.add(ScenarioEvent(
            scenario_id=s2.id, sequence_order=2,
            trigger_type="delay", trigger_config={"delay_seconds": 60},
            action_type="device_state_change",
            action_config={"device_id": str(core2.id), "admin_state": "active"},
        ))

    # === Scenario 3: Error Storm ===
    s3 = Scenario(
        name="Error Storm — Access Switch",
        description="Simulates degrading link quality on access-sw-01 Gi1/0/1. "
                    "CRC errors spike, then input errors, then interface goes down.",
        status="ready", is_repeatable=True,
    )
    session.add(s3)
    await session.flush()

    access1_gi1 = interfaces.get((str(access1.id), "GigabitEthernet1/0/1")) if access1 else None

    if access1_gi1:
        # Event 1: CRC errors start (immediate)
        session.add(ScenarioEvent(
            scenario_id=s3.id, sequence_order=1,
            trigger_type="immediate", trigger_config={},
            action_type="counter_set",
            action_config={"interface_id": str(access1_gi1.id), "counter_name": "crc_errors", "value": 150},
            rollback_action={"action_type": "counter_set",
                             "action_config": {"interface_id": str(access1_gi1.id), "counter_name": "crc_errors", "value": 0}},
        ))

        # Event 2: Errors escalate (10s)
        session.add(ScenarioEvent(
            scenario_id=s3.id, sequence_order=2,
            trigger_type="delay", trigger_config={"delay_seconds": 10},
            action_type="counter_set",
            action_config={"interface_id": str(access1_gi1.id), "counter_name": "in_errors", "value": 5000},
            rollback_action={"action_type": "counter_set",
                             "action_config": {"interface_id": str(access1_gi1.id), "counter_name": "in_errors", "value": 0}},
        ))

        # Event 3: Interface goes down (15s)
        session.add(ScenarioEvent(
            scenario_id=s3.id, sequence_order=3,
            trigger_type="delay", trigger_config={"delay_seconds": 15},
            action_type="interface_state_change",
            action_config={"interface_id": str(access1_gi1.id), "oper_status": "down"},
            rollback_action={"action_type": "interface_state_change",
                             "action_config": {"interface_id": str(access1_gi1.id), "oper_status": "up"}},
        ))

    await session.commit()
    print(f"Seeded 3 scenarios.")


async def main():
    async with async_session_factory() as session:
        await seed_scenarios(session)


if __name__ == "__main__":
    asyncio.run(main())

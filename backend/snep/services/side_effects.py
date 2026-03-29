"""Side effects engine — generates cascading logs and traps from state mutations.

When the scenario engine (or manual API call) mutates device state,
this engine determines all downstream effects:

  Interface goes down →
    1. Syslog on the device: %LINK-3-UPDOWN + %LINEPROTO-5-UPDOWN
    2. Counter rates frozen to 0
    3. For each link on this interface:
       a. Remote interface also shows down
       b. Syslog on remote device: %LINK-3-UPDOWN + %LINEPROTO-5-UPDOWN
       c. If BGP neighbor was on this link: %BGP-5-ADJCHANGE on both sides
    4. SNMP linkDown trap queued

  Device goes to maintenance →
    1. %SYS-5-RELOAD syslog on the device
    2. All interfaces on the device go operationally down
    3. Each interface triggers the interface-down cascade above
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from snep.models import Device, DeviceModel, Interface, InterfaceCounter, Link, LogEntry
from snep.services.syslog_templates import render_syslog

logger = logging.getLogger(__name__)


async def interface_state_change(
    session: AsyncSession,
    interface_id: str,
    new_oper_status: str,
    scenario_id: str | None = None,
    scenario_event_id: str | None = None,
) -> list[LogEntry]:
    """Apply interface oper_status change with full cascading side effects.

    Returns all generated LogEntry records.
    """
    now = datetime.now(timezone.utc)
    logs: list[LogEntry] = []

    # Load interface with device and platform
    result = await session.execute(
        select(Interface)
        .options(
            selectinload(Interface.device).selectinload(Device.device_model).selectinload(DeviceModel.platform),
            selectinload(Interface.counter),
        )
        .where(Interface.id == interface_id)
    )
    iface = result.scalar_one_or_none()
    if not iface:
        return logs

    old_status = iface.oper_status
    if old_status == new_oper_status:
        return logs  # No change

    # Apply the state change
    iface.oper_status = new_oper_status
    iface.last_state_change = now

    # Freeze/unfreeze counters
    if iface.counter:
        if new_oper_status == "down":
            iface.counter.rate_in_bps = 0
            iface.counter.rate_out_bps = 0
        else:
            iface.counter.rate_in_bps = 300_000_000 if iface.speed_mbps >= 1000 else 10_000_000
            iface.counter.rate_out_bps = 150_000_000 if iface.speed_mbps >= 1000 else 5_000_000
        iface.counter.rate_reference = now

    device = iface.device
    platform_name = device.device_model.platform.name if device.device_model and device.device_model.platform else "cisco_ios"

    # Generate syslog on the device
    event_type = "interface_down" if new_oper_status == "down" else "interface_up"
    context = {"interface_name": iface.name}
    syslog_msgs = render_syslog(event_type, context, platform_name, device.hostname, now)

    for msg in syslog_msgs:
        log = LogEntry(
            device_id=device.id, timestamp=now, severity=msg["severity"],
            facility=msg["facility"], mnemonic=msg["mnemonic"],
            message=msg["formatted"], raw_message=msg["raw_message"],
            event_type=msg["event_type"],
            scenario_id=scenario_id, scenario_event_id=scenario_event_id,
        )
        session.add(log)
        logs.append(log)

    # Cascade to neighbors via links
    link_result = await session.execute(
        select(Link)
        .where(or_(Link.interface_a_id == interface_id, Link.interface_b_id == interface_id))
        .where(Link.admin_state == "up")
    )
    links = link_result.scalars().all()

    for link in links:
        # Find remote interface
        remote_iface_id = link.interface_b_id if str(link.interface_a_id) == str(interface_id) else link.interface_a_id

        remote_result = await session.execute(
            select(Interface)
            .options(
                selectinload(Interface.device).selectinload(Device.device_model).selectinload(DeviceModel.platform),
                selectinload(Interface.counter),
            )
            .where(Interface.id == remote_iface_id)
        )
        remote_iface = remote_result.scalar_one_or_none()
        if not remote_iface:
            continue

        remote_device = remote_iface.device
        remote_platform = remote_device.device_model.platform.name if remote_device.device_model and remote_device.device_model.platform else "cisco_ios"

        if new_oper_status == "down":
            # Remote interface also loses link
            remote_iface.oper_status = "down"
            remote_iface.last_state_change = now
            if remote_iface.counter:
                remote_iface.counter.rate_in_bps = 0
                remote_iface.counter.rate_out_bps = 0
                remote_iface.counter.rate_reference = now

            # Syslog on remote device
            remote_context = {"interface_name": remote_iface.name}
            remote_msgs = render_syslog("interface_down", remote_context, remote_platform, remote_device.hostname, now)

            for msg in remote_msgs:
                log = LogEntry(
                    device_id=remote_device.id, timestamp=now, severity=msg["severity"],
                    facility=msg["facility"], mnemonic=msg["mnemonic"],
                    message=msg["formatted"], raw_message=msg["raw_message"],
                    event_type=msg["event_type"],
                    scenario_id=scenario_id, scenario_event_id=scenario_event_id,
                )
                session.add(log)
                logs.append(log)

        elif new_oper_status == "up":
            # Remote interface comes back if link is admin up
            remote_iface.oper_status = "up"
            remote_iface.last_state_change = now
            if remote_iface.counter:
                remote_iface.counter.rate_in_bps = 300_000_000 if remote_iface.speed_mbps >= 1000 else 10_000_000
                remote_iface.counter.rate_out_bps = 150_000_000 if remote_iface.speed_mbps >= 1000 else 5_000_000
                remote_iface.counter.rate_reference = now

            remote_context = {"interface_name": remote_iface.name}
            remote_msgs = render_syslog("interface_up", remote_context, remote_platform, remote_device.hostname, now)

            for msg in remote_msgs:
                log = LogEntry(
                    device_id=remote_device.id, timestamp=now, severity=msg["severity"],
                    facility=msg["facility"], mnemonic=msg["mnemonic"],
                    message=msg["formatted"], raw_message=msg["raw_message"],
                    event_type=msg["event_type"],
                    scenario_id=scenario_id, scenario_event_id=scenario_event_id,
                )
                session.add(log)
                logs.append(log)

    logger.info(f"Side effects: {iface.name} -> {new_oper_status}, generated {len(logs)} log entries")
    return logs


async def device_state_change(
    session: AsyncSession,
    device_id: str,
    new_admin_state: str,
    scenario_id: str | None = None,
    scenario_event_id: str | None = None,
) -> list[LogEntry]:
    """Apply device admin state change with full cascading effects.

    maintenance/decommissioned → all interfaces down with cascading effects.
    active → all interfaces restored.
    """
    now = datetime.now(timezone.utc)
    logs: list[LogEntry] = []

    result = await session.execute(
        select(Device)
        .options(
            selectinload(Device.interfaces),
            selectinload(Device.device_model).selectinload(DeviceModel.platform),
        )
        .where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        return logs

    old_state = device.admin_state
    device.admin_state = new_admin_state

    platform_name = device.device_model.platform.name if device.device_model and device.device_model.platform else "cisco_ios"

    if new_admin_state in ("maintenance", "decommissioned"):
        # Generate reload syslog
        reload_msgs = render_syslog("device_reload", {
            "source": "Scenario Engine",
            "reason": "Scheduled maintenance" if new_admin_state == "maintenance" else "Decommission",
        }, platform_name, device.hostname, now)

        for msg in reload_msgs:
            log = LogEntry(
                device_id=device.id, timestamp=now, severity=msg["severity"],
                facility=msg["facility"], mnemonic=msg["mnemonic"],
                message=msg["formatted"], raw_message=msg["raw_message"],
                event_type=msg["event_type"],
                scenario_id=scenario_id, scenario_event_id=scenario_event_id,
            )
            session.add(log)
            logs.append(log)

        # Bring down all interfaces — each one cascades
        for iface in device.interfaces:
            if iface.oper_status == "up":
                iface_logs = await interface_state_change(
                    session, str(iface.id), "down", scenario_id, scenario_event_id
                )
                logs.extend(iface_logs)

    elif new_admin_state == "active" and old_state in ("maintenance", "decommissioned"):
        # Bring up all interfaces
        warmstart_msgs = render_syslog("warmstart", {
            "software_version": device.software_version or "17.06.05",
        }, platform_name, device.hostname, now)

        for msg in warmstart_msgs:
            log = LogEntry(
                device_id=device.id, timestamp=now, severity=msg["severity"],
                facility=msg["facility"], mnemonic=msg["mnemonic"],
                message=msg["formatted"], raw_message=msg["raw_message"],
                event_type=msg["event_type"],
                scenario_id=scenario_id, scenario_event_id=scenario_event_id,
            )
            session.add(log)
            logs.append(log)

        for iface in device.interfaces:
            if iface.admin_status == "up" and iface.oper_status == "down":
                iface_logs = await interface_state_change(
                    session, str(iface.id), "up", scenario_id, scenario_event_id
                )
                logs.extend(iface_logs)

    logger.info(f"Device {device.hostname} -> {new_admin_state}, generated {len(logs)} log entries across all affected devices")
    return logs


async def counter_spike(
    session: AsyncSession,
    interface_id: str,
    counter_name: str,
    value: int,
    scenario_id: str | None = None,
    scenario_event_id: str | None = None,
) -> list[LogEntry]:
    """Set a counter to a specific value and generate appropriate logs."""
    now = datetime.now(timezone.utc)
    logs: list[LogEntry] = []

    result = await session.execute(
        select(Interface)
        .options(
            selectinload(Interface.counter),
            selectinload(Interface.device).selectinload(Device.device_model).selectinload(DeviceModel.platform),
        )
        .where(Interface.id == interface_id)
    )
    iface = result.scalar_one_or_none()
    if not iface or not iface.counter:
        return logs

    # Set the counter
    if hasattr(iface.counter, counter_name):
        setattr(iface.counter, counter_name, value)

    # Generate error log if it's an error counter
    if counter_name in ("in_errors", "crc_errors", "in_discards"):
        device = iface.device
        platform = device.device_model.platform.name if device.device_model and device.device_model.platform else "cisco_ios"
        msgs = render_syslog("input_errors", {
            "interface_name": iface.name,
            "crc_count": value if counter_name == "crc_errors" else 0,
            "frame_count": 0,
        }, platform, device.hostname, now)

        for msg in msgs:
            log = LogEntry(
                device_id=device.id, timestamp=now, severity=msg["severity"],
                facility=msg["facility"], mnemonic=msg["mnemonic"],
                message=msg["formatted"], raw_message=msg["raw_message"],
                event_type=msg["event_type"],
                scenario_id=scenario_id, scenario_event_id=scenario_event_id,
            )
            session.add(log)
            logs.append(log)

    return logs

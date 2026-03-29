"""Scenario execution engine — orchestrates event playback with side effects.

Processes scenario events in sequence:
1. Evaluate trigger (immediate, delay, manual, conditional)
2. Apply action via the side effects engine
3. Track progress and generate audit trail
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from snep.models import Device, Interface, InterfaceCounter, Link, Scenario, ScenarioEvent, LogEntry
from snep.services.side_effects import interface_state_change, device_state_change, counter_spike

logger = logging.getLogger(__name__)

# Track running scenarios (in-memory for simplicity)
_running_scenarios: dict[str, asyncio.Task] = {}
_scenario_progress: dict[str, dict] = {}


async def start_scenario(session: AsyncSession, scenario_id: str) -> dict:
    """Start executing a scenario."""
    result = await session.execute(
        select(Scenario).options(selectinload(Scenario.events)).where(Scenario.id == scenario_id)
    )
    scenario = result.scalar_one_or_none()
    if not scenario:
        return {"error": "Scenario not found"}
    if scenario.status == "running":
        return {"error": "Scenario is already running"}

    scenario.status = "running"
    await session.commit()

    _scenario_progress[scenario_id] = {
        "status": "running",
        "current_event": 0,
        "total_events": len(scenario.events),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_events": [],
        "logs_generated": 0,
    }

    # Run in background
    from snep.db import async_session_factory
    task = asyncio.create_task(_execute_scenario(scenario_id, async_session_factory))
    _running_scenarios[scenario_id] = task

    return {"status": "started", "total_events": len(scenario.events)}


async def _execute_scenario(scenario_id: str, session_factory):
    """Execute all events in a scenario sequentially."""
    try:
        async with session_factory() as session:
            result = await session.execute(
                select(Scenario).options(selectinload(Scenario.events)).where(Scenario.id == scenario_id)
            )
            scenario = result.scalar_one_or_none()
            if not scenario:
                return

            for i, event in enumerate(scenario.events):
                progress = _scenario_progress.get(scenario_id, {})
                if progress.get("status") == "paused":
                    # Wait for resume
                    while progress.get("status") == "paused":
                        await asyncio.sleep(0.5)
                        progress = _scenario_progress.get(scenario_id, {})
                    if progress.get("status") == "cancelled":
                        break

                progress["current_event"] = i + 1

                # Evaluate trigger
                await _evaluate_trigger(event, scenario_id)

                # Apply action
                logs = await _apply_action(session, event, scenario_id)
                await session.commit()

                progress["completed_events"].append({
                    "event_id": str(event.id),
                    "sequence": event.sequence_order,
                    "action_type": event.action_type,
                    "logs_generated": len(logs),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                })
                progress["logs_generated"] += len(logs)

            # Mark complete
            async with session_factory() as session2:
                await session2.execute(
                    update(Scenario).where(Scenario.id == scenario_id).values(status="completed")
                )
                await session2.commit()

            progress = _scenario_progress.get(scenario_id, {})
            progress["status"] = "completed"
            progress["completed_at"] = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        logger.error(f"Scenario {scenario_id} failed: {e}")
        progress = _scenario_progress.get(scenario_id, {})
        progress["status"] = "failed"
        progress["error"] = str(e)

    finally:
        _running_scenarios.pop(scenario_id, None)


async def _evaluate_trigger(event: ScenarioEvent, scenario_id: str):
    """Wait for the trigger condition to be met."""
    if event.trigger_type == "immediate":
        return

    elif event.trigger_type == "delay":
        delay = event.trigger_config.get("delay_seconds", 0)
        logger.info(f"Scenario {scenario_id}: waiting {delay}s before event {event.sequence_order}")
        await asyncio.sleep(delay)

    elif event.trigger_type == "manual":
        # Wait for manual trigger flag
        progress = _scenario_progress.get(scenario_id, {})
        progress["waiting_for_manual"] = str(event.id)
        while progress.get("waiting_for_manual") == str(event.id):
            await asyncio.sleep(0.5)

    elif event.trigger_type == "conditional":
        # Poll condition (future: full expression evaluation)
        timeout = event.trigger_config.get("timeout_seconds", 300)
        interval = event.trigger_config.get("check_interval_seconds", 5)
        elapsed = 0
        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval
            # For now, conditions auto-pass after first check
            break


async def _apply_action(session: AsyncSession, event: ScenarioEvent, scenario_id: str) -> list[LogEntry]:
    """Apply a scenario event action via the side effects engine."""
    action = event.action_type
    config = event.action_config
    sid = scenario_id
    eid = str(event.id)

    if action == "interface_state_change":
        return await interface_state_change(session, config["interface_id"], config["oper_status"], sid, eid)

    elif action == "interface_admin_change":
        iface = await session.get(Interface, config["interface_id"])
        if iface:
            iface.admin_status = config["admin_status"]
            if config["admin_status"] == "down":
                return await interface_state_change(session, config["interface_id"], "down", sid, eid)
        return []

    elif action == "counter_set":
        return await counter_spike(session, config["interface_id"], config["counter_name"], config["value"], sid, eid)

    elif action == "counter_rate_change":
        result = await session.execute(
            select(InterfaceCounter).where(InterfaceCounter.interface_id == config["interface_id"])
        )
        counter = result.scalar_one_or_none()
        if counter:
            if "rate_in_bps" in config:
                counter.rate_in_bps = config["rate_in_bps"]
            if "rate_out_bps" in config:
                counter.rate_out_bps = config["rate_out_bps"]
            counter.rate_reference = datetime.now(timezone.utc)
        return []

    elif action == "link_state_change":
        link = await session.get(Link, config["link_id"])
        if link:
            link.admin_state = config["admin_state"]
            logs = []
            if config["admin_state"] == "down":
                logs.extend(await interface_state_change(session, str(link.interface_a_id), "down", sid, eid))
                logs.extend(await interface_state_change(session, str(link.interface_b_id), "down", sid, eid))
            return logs
        return []

    elif action == "device_state_change":
        return await device_state_change(session, config["device_id"], config["admin_state"], sid, eid)

    elif action == "log_event":
        now = datetime.now(timezone.utc)
        device_id = config.get("device_id")

        # Custom free-form message with {{ variable }} template support
        if config.get("custom_message"):
            from snep.services.template_variables import resolve_variables
            raw_msg = config["custom_message"]
            if device_id:
                raw_msg = await resolve_variables(session, raw_msg, device_id)

            severity = config.get("severity", 5)
            facility = config.get("facility", "SYS")
            mnemonic = config.get("mnemonic", "CONFIG_I")

            ts = now.strftime("*%b %d %H:%M:%S.") + f"{now.microsecond // 1000:03d}"
            formatted = f"{ts}: %{facility}-{severity}-{mnemonic}: {raw_msg}"

            log = LogEntry(
                device_id=device_id, timestamp=now, severity=severity,
                facility=facility, mnemonic=mnemonic,
                message=formatted, raw_message=raw_msg, event_type="custom_log",
                scenario_id=sid, scenario_event_id=eid,
            )
            session.add(log)
            return [log]

        # Template-based log (predefined syslog formats)
        from snep.services.syslog_templates import render_syslog
        event_context = config.get("context", {})

        # Resolve {{ variables }} in context values
        if device_id:
            from snep.services.template_variables import resolve_variables
            for key, val in list(event_context.items()):
                if isinstance(val, str) and "{{" in val:
                    event_context[key] = await resolve_variables(session, val, device_id)

        msgs = render_syslog(
            config.get("event_type", "config_change"), event_context,
            config.get("platform", "cisco_ios"), config.get("hostname", ""), now,
        )
        logs = []
        for msg in msgs:
            log = LogEntry(
                device_id=device_id, timestamp=now,
                severity=msg["severity"], facility=msg["facility"],
                mnemonic=msg["mnemonic"], message=msg["formatted"],
                raw_message=msg["raw_message"], event_type=msg["event_type"],
                scenario_id=sid, scenario_event_id=eid,
            )
            session.add(log)
            logs.append(log)
        return logs

    elif action == "bulk_update":
        logs = []
        for sub_action in config.get("updates", []):
            sub_event = ScenarioEvent(
                action_type=sub_action["action_type"],
                action_config=sub_action["action_config"],
                trigger_type="immediate", trigger_config={},
                sequence_order=0, scenario_id=scenario_id,
            )
            sub_logs = await _apply_action(session, sub_event, scenario_id)
            logs.extend(sub_logs)
        return logs

    return []


def pause_scenario(scenario_id: str) -> dict:
    progress = _scenario_progress.get(scenario_id)
    if progress and progress["status"] == "running":
        progress["status"] = "paused"
        return {"status": "paused"}
    return {"error": "Scenario not running"}


def resume_scenario(scenario_id: str) -> dict:
    progress = _scenario_progress.get(scenario_id)
    if progress and progress["status"] == "paused":
        progress["status"] = "running"
        return {"status": "resumed"}
    return {"error": "Scenario not paused"}


def trigger_manual_event(scenario_id: str, event_id: str) -> dict:
    progress = _scenario_progress.get(scenario_id)
    if progress and progress.get("waiting_for_manual") == event_id:
        progress["waiting_for_manual"] = None
        return {"status": "triggered"}
    return {"error": "No manual trigger waiting for this event"}


def get_scenario_progress(scenario_id: str) -> dict:
    return _scenario_progress.get(scenario_id, {"status": "not_started"})


async def reset_scenario(session: AsyncSession, scenario_id: str) -> dict:
    """Reset a scenario — apply rollback actions in reverse order."""
    result = await session.execute(
        select(Scenario).options(selectinload(Scenario.events)).where(Scenario.id == scenario_id)
    )
    scenario = result.scalar_one_or_none()
    if not scenario:
        return {"error": "Scenario not found"}

    # Apply rollback actions in reverse
    rollback_count = 0
    for event in reversed(scenario.events):
        if event.rollback_action:
            rollback_event = ScenarioEvent(
                action_type=event.rollback_action.get("action_type", event.action_type),
                action_config=event.rollback_action.get("action_config", {}),
                trigger_type="immediate", trigger_config={},
                sequence_order=0, scenario_id=scenario_id,
            )
            await _apply_action(session, rollback_event, scenario_id)
            rollback_count += 1

    scenario.status = "ready"
    await session.commit()

    _scenario_progress.pop(scenario_id, None)
    return {"status": "reset", "rollbacks_applied": rollback_count}

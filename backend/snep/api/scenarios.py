"""Scenario CRUD + execution endpoints."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from snep.api.deps import DBSession, PaginationDep
from snep.models.scenario import Scenario, ScenarioEvent
from snep.models.log_entry import LogEntry

router = APIRouter()


class ScenarioEventCreate(BaseModel):
    sequence_order: int
    trigger_type: str
    trigger_config: dict = {}
    action_type: str
    action_config: dict = {}
    rollback_action: dict | None = None


class ScenarioCreate(BaseModel):
    name: str
    description: str | None = None
    is_repeatable: bool = True
    events: list[ScenarioEventCreate] = []


# --- CRUD ---

@router.get("")
async def list_scenarios(db: DBSession, pg: PaginationDep):
    from snep.services.scenario_engine import get_scenario_progress
    result = await db.execute(
        select(Scenario).options(selectinload(Scenario.events)).offset(pg.offset).limit(pg.limit)
    )
    scenarios = result.scalars().all()
    out = []
    for s in scenarios:
        # Sync status from in-memory execution state
        progress = get_scenario_progress(str(s.id))
        effective_status = s.status
        if progress.get("status") == "completed" and s.status == "running":
            s.status = "completed"
            effective_status = "completed"
        elif progress.get("status") == "failed" and s.status == "running":
            s.status = "failed"
            effective_status = "failed"

        # Count logs for this scenario
        log_count = await db.scalar(
            select(func.count()).select_from(LogEntry).where(LogEntry.scenario_id == s.id)
        )

        out.append({
            "id": str(s.id), "name": s.name, "description": s.description,
            "status": effective_status, "is_repeatable": s.is_repeatable,
            "event_count": len(s.events), "log_count": log_count or 0,
        })
    await db.commit()
    return out


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: uuid.UUID, db: DBSession):
    result = await db.execute(
        select(Scenario).options(selectinload(Scenario.events)).where(Scenario.id == scenario_id)
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Scenario not found")
    return {
        "id": str(s.id), "name": s.name, "description": s.description,
        "status": s.status, "is_repeatable": s.is_repeatable,
        "events": [
            {
                "id": str(e.id), "sequence_order": e.sequence_order,
                "trigger_type": e.trigger_type, "trigger_config": e.trigger_config,
                "action_type": e.action_type, "action_config": e.action_config,
                "rollback_action": e.rollback_action,
            }
            for e in s.events
        ],
    }


@router.post("", status_code=201)
async def create_scenario(body: ScenarioCreate, db: DBSession):
    s = Scenario(name=body.name, description=body.description, is_repeatable=body.is_repeatable, status="ready")
    db.add(s)
    await db.flush()
    for ev in body.events:
        db.add(ScenarioEvent(scenario_id=s.id, **ev.model_dump()))
    await db.commit()
    return {"id": str(s.id), "name": s.name}


@router.delete("/{scenario_id}", status_code=204)
async def delete_scenario(scenario_id: uuid.UUID, db: DBSession):
    s = await db.get(Scenario, scenario_id)
    if not s:
        raise HTTPException(404, "Scenario not found")
    await db.delete(s)
    await db.commit()


# --- Execution ---

@router.post("/{scenario_id}/start")
async def start_scenario_endpoint(scenario_id: uuid.UUID, db: DBSession):
    """Start executing a scenario."""
    from snep.services.scenario_engine import start_scenario
    result = await start_scenario(db, str(scenario_id))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/{scenario_id}/pause")
async def pause_scenario_endpoint(scenario_id: uuid.UUID):
    from snep.services.scenario_engine import pause_scenario
    return pause_scenario(str(scenario_id))


@router.post("/{scenario_id}/resume")
async def resume_scenario_endpoint(scenario_id: uuid.UUID):
    from snep.services.scenario_engine import resume_scenario
    return resume_scenario(str(scenario_id))


@router.post("/{scenario_id}/reset")
async def reset_scenario_endpoint(scenario_id: uuid.UUID, db: DBSession):
    from snep.services.scenario_engine import reset_scenario
    result = await reset_scenario(db, str(scenario_id))
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/{scenario_id}/events/{event_id}/trigger")
async def manual_trigger_endpoint(scenario_id: uuid.UUID, event_id: uuid.UUID):
    from snep.services.scenario_engine import trigger_manual_event
    return trigger_manual_event(str(scenario_id), str(event_id))


@router.get("/{scenario_id}/execution")
async def get_execution_status(scenario_id: uuid.UUID, db: DBSession):
    from snep.services.scenario_engine import get_scenario_progress
    progress = get_scenario_progress(str(scenario_id))

    # Get logs generated by this scenario
    log_count = await db.scalar(
        select(func.count()).select_from(LogEntry).where(LogEntry.scenario_id == scenario_id)
    )

    # Get recent logs
    recent_logs = await db.execute(
        select(LogEntry)
        .where(LogEntry.scenario_id == scenario_id)
        .order_by(LogEntry.timestamp.desc())
        .limit(20)
    )
    logs = [
        {
            "timestamp": l.timestamp.isoformat(),
            "severity": l.severity,
            "facility": l.facility,
            "mnemonic": l.mnemonic,
            "message": l.message,
            "device_id": str(l.device_id),
        }
        for l in recent_logs.scalars().all()
    ]

    return {
        "progress": progress,
        "total_logs": log_count or 0,
        "recent_logs": logs,
    }


# --- Device Logs ---

@router.get("/logs/{device_id}")
async def get_device_logs(device_id: uuid.UUID, db: DBSession, pg: PaginationDep, severity: int | None = None):
    """Get log entries for a device (for show logging)."""
    q = select(LogEntry).where(LogEntry.device_id == device_id)
    if severity is not None:
        q = q.where(LogEntry.severity <= severity)
    q = q.order_by(LogEntry.timestamp.desc()).offset(pg.offset).limit(pg.limit)

    result = await db.execute(q)
    return [
        {
            "id": str(l.id),
            "timestamp": l.timestamp.isoformat(),
            "severity": l.severity,
            "facility": l.facility,
            "mnemonic": l.mnemonic,
            "message": l.message,
            "event_type": l.event_type,
            "scenario_id": str(l.scenario_id) if l.scenario_id else None,
        }
        for l in result.scalars().all()
    ]

"""Scenario CRUD endpoints."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from snep.api.deps import DBSession, PaginationDep
from snep.models.scenario import Scenario, ScenarioEvent

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


class ScenarioOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    status: str
    is_repeatable: bool
    event_count: int = 0

    model_config = {"from_attributes": True}


@router.get("", response_model=list[ScenarioOut])
async def list_scenarios(db: DBSession, pg: PaginationDep):
    result = await db.execute(
        select(Scenario).options(selectinload(Scenario.events)).offset(pg.offset).limit(pg.limit)
    )
    scenarios = result.scalars().all()
    return [
        ScenarioOut(
            id=s.id, name=s.name, description=s.description,
            status=s.status, is_repeatable=s.is_repeatable,
            event_count=len(s.events),
        )
        for s in scenarios
    ]


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: uuid.UUID, db: DBSession):
    result = await db.execute(
        select(Scenario).options(selectinload(Scenario.events)).where(Scenario.id == scenario_id)
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Scenario not found")
    return {
        "id": str(s.id),
        "name": s.name,
        "description": s.description,
        "status": s.status,
        "is_repeatable": s.is_repeatable,
        "events": [
            {
                "id": str(e.id),
                "sequence_order": e.sequence_order,
                "trigger_type": e.trigger_type,
                "trigger_config": e.trigger_config,
                "action_type": e.action_type,
                "action_config": e.action_config,
                "rollback_action": e.rollback_action,
            }
            for e in s.events
        ],
    }


@router.post("", status_code=201)
async def create_scenario(body: ScenarioCreate, db: DBSession):
    s = Scenario(name=body.name, description=body.description, is_repeatable=body.is_repeatable)
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

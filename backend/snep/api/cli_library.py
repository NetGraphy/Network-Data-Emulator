"""CLI Output Library endpoints — versioned, platform/model-based CLI output management with parser validation."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from snep.api.deps import DBSession, PaginationDep
from snep.models.cli_library import CommandOutputLibrary, ParserTemplate
from snep.models.device import DeviceModel
from snep.models.platform import Platform
from snep.services.parser_validation import (
    diff_outputs,
    find_matching_versions,
    validate_against_parsers,
)

router = APIRouter()


class LibraryEntryCreate(BaseModel):
    platform_id: uuid.UUID
    device_model_id: uuid.UUID | None = None
    software_version: str
    command: str
    raw_output: str
    source_description: str | None = None
    auto_validate: bool = True


class LibraryEntryOut(BaseModel):
    id: uuid.UUID
    platform_id: uuid.UUID
    platform_name: str | None = None
    device_model_id: uuid.UUID | None
    device_model_name: str | None = None
    software_version: str
    command: str
    raw_output: str
    parser_results: dict | None
    parent_version_id: uuid.UUID | None
    diff_from_parent: dict | None
    is_reference: bool
    source_description: str | None

    model_config = {"from_attributes": True}


# --- Library Entry CRUD ---

@router.get("")
async def list_library_entries(
    db: DBSession,
    pg: PaginationDep,
    platform_id: uuid.UUID | None = None,
    software_version: str | None = None,
    command: str | None = None,
    device_model_id: uuid.UUID | None = None,
):
    """List CLI output library entries with optional filters."""
    q = select(CommandOutputLibrary).options(
        selectinload(CommandOutputLibrary.platform),
        selectinload(CommandOutputLibrary.device_model),
    )
    if platform_id:
        q = q.where(CommandOutputLibrary.platform_id == platform_id)
    if software_version:
        q = q.where(CommandOutputLibrary.software_version == software_version)
    if command:
        q = q.where(CommandOutputLibrary.command == command)
    if device_model_id:
        q = q.where(CommandOutputLibrary.device_model_id == device_model_id)

    q = q.order_by(CommandOutputLibrary.command, CommandOutputLibrary.software_version)
    q = q.offset(pg.offset).limit(pg.limit)

    result = await db.execute(q)
    entries = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "platform_id": str(e.platform_id),
            "platform_name": e.platform.name if e.platform else None,
            "device_model_id": str(e.device_model_id) if e.device_model_id else None,
            "device_model_name": e.device_model.display_name if e.device_model else None,
            "software_version": e.software_version,
            "command": e.command,
            "raw_output": e.raw_output[:200] + "..." if len(e.raw_output) > 200 else e.raw_output,
            "parser_results": e.parser_results,
            "diff_from_parent": e.diff_from_parent,
            "is_reference": e.is_reference,
            "source_description": e.source_description,
        }
        for e in entries
    ]


@router.get("/commands")
async def list_known_commands(db: DBSession):
    """List all unique commands in the library, grouped by platform."""
    result = await db.execute(
        select(CommandOutputLibrary.command, Platform.name)
        .join(Platform, CommandOutputLibrary.platform_id == Platform.id)
        .distinct()
        .order_by(Platform.name, CommandOutputLibrary.command)
    )
    rows = result.all()

    grouped = {}
    for cmd, platform in rows:
        grouped.setdefault(platform, []).append(cmd)
    return grouped


@router.get("/versions")
async def list_versions(db: DBSession, platform_id: uuid.UUID, command: str):
    """List all software versions that have entries for a given platform+command."""
    result = await db.execute(
        select(
            CommandOutputLibrary.software_version,
            CommandOutputLibrary.id,
            CommandOutputLibrary.is_reference,
            CommandOutputLibrary.parser_results,
        )
        .where(CommandOutputLibrary.platform_id == platform_id)
        .where(CommandOutputLibrary.command == command)
        .order_by(CommandOutputLibrary.software_version)
    )
    rows = result.all()

    return [
        {
            "version": row.software_version,
            "entry_id": str(row.id),
            "is_reference": row.is_reference,
            "parser_status": _summarize_parser_status(row.parser_results),
        }
        for row in rows
    ]


@router.get("/{entry_id}")
async def get_library_entry(entry_id: uuid.UUID, db: DBSession):
    """Get a single library entry with full details."""
    result = await db.execute(
        select(CommandOutputLibrary)
        .options(
            selectinload(CommandOutputLibrary.platform),
            selectinload(CommandOutputLibrary.device_model),
        )
        .where(CommandOutputLibrary.id == entry_id)
    )
    e = result.scalar_one_or_none()
    if not e:
        raise HTTPException(404, "Library entry not found")

    return {
        "id": str(e.id),
        "platform_id": str(e.platform_id),
        "platform_name": e.platform.name if e.platform else None,
        "device_model_id": str(e.device_model_id) if e.device_model_id else None,
        "device_model_name": e.device_model.display_name if e.device_model else None,
        "software_version": e.software_version,
        "command": e.command,
        "raw_output": e.raw_output,
        "parser_results": e.parser_results,
        "parent_version_id": str(e.parent_version_id) if e.parent_version_id else None,
        "diff_from_parent": e.diff_from_parent,
        "is_reference": e.is_reference,
        "source_description": e.source_description,
        "field_annotations": e.field_annotations,
    }


@router.post("", status_code=201)
async def create_library_entry(body: LibraryEntryCreate, db: DBSession):
    """Create a new CLI output library entry.

    Automatically:
    1. Validates output against known parsers
    2. Finds matching versions in the library
    3. Diffs against the closest version
    4. Determines if a new parser is needed
    """
    # Verify platform exists
    platform = await db.get(Platform, body.platform_id)
    if not platform:
        raise HTTPException(404, "Platform not found")

    # Check for duplicate
    existing = await db.execute(
        select(CommandOutputLibrary).where(
            CommandOutputLibrary.platform_id == body.platform_id,
            CommandOutputLibrary.software_version == body.software_version,
            CommandOutputLibrary.device_model_id == body.device_model_id,
            CommandOutputLibrary.command == body.command,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Entry already exists for {platform.name}/{body.software_version}/{body.command}")

    # Validate against parsers
    parser_results = None
    if body.auto_validate:
        parser_results = validate_against_parsers(body.raw_output, platform.name, body.command)

    # Find matching versions and diff against closest
    existing_entries_q = await db.execute(
        select(CommandOutputLibrary)
        .options(selectinload(CommandOutputLibrary.device_model))
        .where(CommandOutputLibrary.platform_id == body.platform_id)
        .where(CommandOutputLibrary.command == body.command)
    )
    existing_entries = existing_entries_q.scalars().all()

    parent_version_id = None
    diff_from_parent = None
    version_matches = []

    if existing_entries:
        entries_data = [
            {
                "id": str(e.id),
                "software_version": e.software_version,
                "device_model_name": e.device_model.display_name if e.device_model else "",
                "raw_output": e.raw_output,
                "parser_results": e.parser_results,
            }
            for e in existing_entries
        ]
        version_matches = find_matching_versions(platform.name, body.command, body.raw_output, entries_data)

        # Diff against the most similar existing entry
        if version_matches:
            closest = version_matches[0]
            closest_entry = next((e for e in existing_entries if str(e.id) == closest["entry_id"]), None)
            if closest_entry:
                parent_version_id = closest_entry.id
                diff_from_parent = diff_outputs(
                    closest_entry.raw_output, body.raw_output, body.command, platform.name
                )

    # Create entry
    is_first = len(existing_entries) == 0
    entry = CommandOutputLibrary(
        platform_id=body.platform_id,
        device_model_id=body.device_model_id,
        software_version=body.software_version,
        command=body.command,
        raw_output=body.raw_output,
        parser_results=parser_results,
        parent_version_id=parent_version_id,
        diff_from_parent=diff_from_parent,
        is_reference=is_first,
        source_description=body.source_description,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return {
        "id": str(entry.id),
        "parser_results": parser_results,
        "diff_from_parent": diff_from_parent,
        "version_matches": version_matches,
        "is_first_entry": is_first,
        "recommendation": _generate_recommendation(parser_results, diff_from_parent, version_matches),
    }


@router.post("/{entry_id}/revalidate")
async def revalidate_entry(entry_id: uuid.UUID, db: DBSession):
    """Re-run parser validation on an existing entry."""
    entry = await db.get(CommandOutputLibrary, entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")

    result = await db.execute(select(Platform).where(Platform.id == entry.platform_id))
    platform = result.scalar_one_or_none()

    parser_results = validate_against_parsers(entry.raw_output, platform.name if platform else "cisco_ios", entry.command)
    entry.parser_results = parser_results
    await db.commit()

    return {"parser_results": parser_results}


@router.post("/{entry_id}/diff/{other_id}")
async def diff_entries(entry_id: uuid.UUID, other_id: uuid.UUID, db: DBSession):
    """Compare two library entries."""
    e1 = await db.get(CommandOutputLibrary, entry_id)
    e2 = await db.get(CommandOutputLibrary, other_id)
    if not e1 or not e2:
        raise HTTPException(404, "One or both entries not found")

    result = await db.execute(select(Platform).where(Platform.id == e1.platform_id))
    platform = result.scalar_one_or_none()

    diff = diff_outputs(e1.raw_output, e2.raw_output, e1.command, platform.name if platform else "cisco_ios")
    return {
        "entry_a": {"id": str(e1.id), "version": e1.software_version},
        "entry_b": {"id": str(e2.id), "version": e2.software_version},
        "diff": diff,
    }


@router.delete("/{entry_id}", status_code=204)
async def delete_library_entry(entry_id: uuid.UUID, db: DBSession):
    entry = await db.get(CommandOutputLibrary, entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    await db.delete(entry)
    await db.commit()


# --- Helpers ---

def _summarize_parser_status(parser_results: dict | None) -> str:
    if not parser_results:
        return "untested"
    textfsm = parser_results.get("textfsm", {})
    if textfsm.get("status") == "pass":
        return "pass"
    elif textfsm.get("status") == "fail":
        return "fail"
    elif textfsm.get("status") == "no_library":
        regex = parser_results.get("regex_extract", {})
        if regex.get("detected_fields"):
            return "regex_only"
        return "untested"
    return "untested"


def _generate_recommendation(parser_results: dict | None, diff: dict | None, matches: list[dict]) -> str:
    """Generate a human-readable recommendation based on validation results."""
    parts = []

    # Parser status
    if parser_results:
        textfsm = parser_results.get("textfsm", {})
        if textfsm.get("status") == "pass":
            parts.append(f"TextFSM parser '{textfsm.get('template')}' successfully parsed this output ({textfsm.get('row_count', 0)} rows)")
        elif textfsm.get("status") == "fail":
            parts.append(f"TextFSM parser failed: {textfsm.get('error', 'unknown error')} — a new or updated parser may be needed")
        elif textfsm.get("status") == "no_library":
            parts.append("NTC-Templates not installed — regex extraction used instead")

        regex = parser_results.get("regex_extract", {})
        fields = regex.get("detected_fields", {})
        if fields:
            field_count = len([k for k in fields.keys() if not k.startswith("_")])
            parts.append(f"Regex extraction found {field_count} structured field(s)")

    # Version comparison
    if diff:
        compat = diff.get("parser_compatibility", "")
        if compat == "identical":
            parts.append("Output is structurally identical to the closest existing version")
        elif compat == "compatible":
            parts.append("Minor value differences from closest version — existing parser should work")
        elif compat == "minor_change":
            parts.append("Small structural changes detected — existing parser may need minor updates")
        elif compat == "new_parser_needed":
            parts.append("Significant structural changes — a new parser version is recommended")

    if matches:
        top = matches[0]
        parts.append(f"Closest match: version {top['version']} (similarity: {top['similarity']:.0%})")

    if not parts:
        parts.append("This is the first entry for this platform/command combination")

    return " | ".join(parts)

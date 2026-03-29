"""Command execution and SNMP walk preview endpoints."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from snep.api.deps import DBSession
from snep.models import Device, DeviceModel, Interface, InterfaceCounter, SNMPProfile
from snep.services.state import get_device_full

router = APIRouter()


class ExecuteRequest(BaseModel):
    command: str


class SNMPWalkRequest(BaseModel):
    subtree: str = "all"  # system, interfaces, ifTable, ifXTable, all, or numeric OID
    output_format: str = "named"  # named or numeric


class SNMPGetRequest(BaseModel):
    oid: str
    output_format: str = "named"


@router.post("/devices/{device_id}/execute")
async def execute_command(device_id: uuid.UUID, body: ExecuteRequest, db: DBSession):
    """Execute a CLI command against a device and return rendered output."""
    device = await get_device_full(db, str(device_id))
    if not device:
        raise HTTPException(404, "Device not found")

    from snep.services.rendering import render_command
    result = await render_command(db, device, body.command)

    return {
        "command": body.command,
        "output": result["output"],
        "rendering_mode": result["mode"],
    }


@router.post("/devices/{device_id}/snmp-walk")
async def snmp_walk_preview(device_id: uuid.UUID, body: SNMPWalkRequest, db: DBSession):
    """Preview SNMP walk output for a device — renders net-snmp-formatted text."""
    device_data, interfaces_data, snmp_data = await _load_snmp_state(db, str(device_id))
    if not device_data:
        raise HTTPException(404, "Device not found")

    from snep.services.snmp_walk import render_snmp_walk
    output = render_snmp_walk(device_data, interfaces_data, snmp_data, body.subtree, body.output_format)

    return {
        "subtree": body.subtree,
        "output_format": body.output_format,
        "output": output,
        "line_count": len(output.strip().split("\n")),
    }


@router.post("/devices/{device_id}/snmp-get")
async def snmp_get_preview(device_id: uuid.UUID, body: SNMPGetRequest, db: DBSession):
    """Preview SNMP GET output for a single OID."""
    device_data, interfaces_data, snmp_data = await _load_snmp_state(db, str(device_id))
    if not device_data:
        raise HTTPException(404, "Device not found")

    from snep.services.snmp_walk import render_snmp_get
    output = render_snmp_get(device_data, interfaces_data, snmp_data, body.oid, body.output_format)

    return {"oid": body.oid, "output": output}


async def _load_snmp_state(db, device_id: str):
    """Load device state formatted for SNMP rendering."""
    result = await db.execute(
        select(Device)
        .options(
            selectinload(Device.interfaces).selectinload(Interface.counter),
            selectinload(Device.device_model).selectinload(DeviceModel.platform),
            selectinload(Device.snmp_profile),
        )
        .where(Device.id == device_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        return None, None, None

    device_data = {
        "hostname": device.hostname,
        "software_version": device.software_version or (device.device_model.software_version if device.device_model else "17.06.05"),
        "uptime_seconds": device.uptime_seconds,
        "uptime_reference": device.uptime_reference,
    }

    interfaces_data = []
    for iface in sorted(device.interfaces, key=lambda i: i.sort_order):
        iface_dict = {
            "name": iface.name, "short_name": iface.short_name, "if_index": iface.if_index,
            "interface_type": iface.interface_type, "admin_status": iface.admin_status,
            "oper_status": iface.oper_status, "speed_mbps": iface.speed_mbps,
            "mtu": iface.mtu, "mac_address": iface.mac_address, "description": iface.description,
        }
        if iface.counter:
            iface_dict["counter"] = {
                "in_octets": iface.counter.in_octets, "out_octets": iface.counter.out_octets,
                "in_unicast_pkts": iface.counter.in_unicast_pkts, "out_unicast_pkts": iface.counter.out_unicast_pkts,
                "in_errors": iface.counter.in_errors, "out_errors": iface.counter.out_errors,
                "in_discards": iface.counter.in_discards, "out_discards": iface.counter.out_discards,
                "rate_in_bps": iface.counter.rate_in_bps, "rate_out_bps": iface.counter.rate_out_bps,
                "rate_reference": iface.counter.rate_reference,
            }
        interfaces_data.append(iface_dict)

    snmp_data = None
    if device.snmp_profile:
        sp = device.snmp_profile
        snmp_data = {
            "v2_community": sp.v2_community, "sys_descr": sp.sys_descr,
            "sys_contact": sp.sys_contact, "sys_name": sp.sys_name or device.hostname,
            "sys_location": sp.sys_location,
        }

    return device_data, interfaces_data, snmp_data


# --- Template Variables ---

@router.get("/devices/{device_id}/variables")
async def get_device_variables_endpoint(device_id: uuid.UUID, db: DBSession):
    """Get all resolved template variables for a device.

    Returns the full list of available variables with their current values.
    Used by the variable picker in scenarios and CLI modeling.
    """
    from snep.services.template_variables import get_device_variables
    return await get_device_variables(db, str(device_id))


@router.get("/template-variables/catalog")
async def get_variable_catalog():
    """Get the template variable catalog — all available variable paths with descriptions."""
    from snep.services.template_variables import VARIABLE_CATALOG
    return VARIABLE_CATALOG


@router.post("/devices/{device_id}/resolve-template")
async def resolve_template_endpoint(device_id: uuid.UUID, body: dict, db: DBSession):
    """Resolve a template string with device state variables.

    Input: {"template": "Interface {{ interface.GigabitEthernet1/0/1.name }} is {{ interface.GigabitEthernet1/0/1.oper_status }}"}
    Output: {"resolved": "Interface GigabitEthernet1/0/1 is up", "original": "..."}
    """
    template = body.get("template", "")
    from snep.services.template_variables import resolve_variables
    resolved = await resolve_variables(db, template, str(device_id))
    return {"original": template, "resolved": resolved}

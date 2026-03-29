"""Export endpoints — Nornir and Ansible inventory generation."""

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from snep.api.deps import DBSession
from snep.models import ConnectionMapping, Device, DeviceCredential, DeviceModel, SNMPProfile

router = APIRouter()


@router.get("/nornir")
async def export_nornir(db: DBSession):
    """Export Nornir-compatible inventory (hosts.yaml format)."""
    result = await db.execute(
        select(Device)
        .options(
            selectinload(Device.device_model).selectinload(DeviceModel.platform),
            selectinload(Device.credentials),
            selectinload(Device.connection_mappings),
            selectinload(Device.snmp_profile),
        )
        .where(Device.admin_state == "active")
        .order_by(Device.hostname)
    )
    devices = result.scalars().all()

    hosts = {}
    for d in devices:
        ssh_mapping = next((cm for cm in d.connection_mappings if cm.protocol == "ssh"), None)
        snmp_mapping = next((cm for cm in d.connection_mappings if cm.protocol == "snmp"), None)
        cred = d.credentials[0] if d.credentials else None

        host_entry = {
            "hostname": ssh_mapping.listen_address if ssh_mapping else "127.0.0.1",
            "port": ssh_mapping.listen_port if ssh_mapping else 22,
            "username": cred.username if cred else "admin",
            "password": cred.password if cred else "admin",
            "platform": d.device_model.platform.name if d.device_model and d.device_model.platform else "cisco_ios",
            "data": {
                **(d.tags or {}),
                "serial_number": d.serial_number,
                "management_ip": str(d.management_ip) if d.management_ip else None,
            },
        }
        if snmp_mapping:
            host_entry["data"]["snmp_port"] = snmp_mapping.listen_port
        if d.snmp_profile and d.snmp_profile.v2_community:
            host_entry["data"]["snmp_community"] = d.snmp_profile.v2_community

        hosts[d.hostname] = host_entry

    return {
        "hosts": hosts,
        "groups": {},
        "defaults": {
            "username": "admin",
            "password": "cisco123",
        },
    }


@router.get("/ansible")
async def export_ansible(db: DBSession):
    """Export Ansible-compatible inventory."""
    result = await db.execute(
        select(Device)
        .options(
            selectinload(Device.device_model).selectinload(DeviceModel.platform),
            selectinload(Device.credentials),
            selectinload(Device.connection_mappings),
        )
        .where(Device.admin_state == "active")
        .order_by(Device.hostname)
    )
    devices = result.scalars().all()

    hosts = {}
    for d in devices:
        ssh_mapping = next((cm for cm in d.connection_mappings if cm.protocol == "ssh"), None)
        cred = d.credentials[0] if d.credentials else None
        platform = d.device_model.platform.name if d.device_model and d.device_model.platform else "cisco_ios"

        # Map SNEP platform to Ansible network_os
        ansible_platform_map = {
            "cisco_ios": "cisco.ios.ios",
            "arista_eos": "arista.eos.eos",
            "juniper_junos": "junipernetworks.junos.junos",
        }

        hosts[d.hostname] = {
            "ansible_host": ssh_mapping.listen_address if ssh_mapping else "127.0.0.1",
            "ansible_port": ssh_mapping.listen_port if ssh_mapping else 22,
            "ansible_user": cred.username if cred else "admin",
            "ansible_password": cred.password if cred else "admin",
            "ansible_network_os": ansible_platform_map.get(platform, platform),
            "ansible_connection": "ansible.netcommon.network_cli",
        }

    return {"all": {"hosts": hosts}}

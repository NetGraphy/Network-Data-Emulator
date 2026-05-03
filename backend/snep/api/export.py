"""Export endpoints — Nornir and Ansible inventory generation."""

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from snep.api.deps import DBSession
from snep.models import Device, DeviceModel
from snep.services.environment import detect_environment
from snep.services.gateway import build_ssh_gateway_info, is_cloud_gateway_mode

router = APIRouter()


@router.get("/nornir")
async def export_nornir(db: DBSession, connection_mode: str | None = None):
    """Export Nornir-compatible inventory (hosts.yaml format)."""
    env = detect_environment()
    use_gateway = connection_mode in {"gateway", "cloud_gateway"} or (
        connection_mode is None and is_cloud_gateway_mode(env)
    )

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
        gateway = build_ssh_gateway_info(
            d.hostname,
            credential_username=cred.username if cred else "admin",
            env=env,
            fallback_host=ssh_mapping.connect_address if ssh_mapping else "127.0.0.1",
        )

        host_entry = {
            "hostname": gateway["host"]
            if use_gateway
            else (ssh_mapping.connect_address if ssh_mapping else "127.0.0.1"),
            "port": gateway["port"] if use_gateway else (ssh_mapping.connect_port if ssh_mapping else 22),
            "username": gateway["username"] if use_gateway else (cred.username if cred else "admin"),
            "password": cred.password if cred else "admin",
            "platform": d.device_model.platform.name if d.device_model and d.device_model.platform else "cisco_ios",
            "data": {
                **(d.tags or {}),
                "serial_number": d.serial_number,
                "management_ip": str(d.management_ip) if d.management_ip else None,
            },
        }
        if snmp_mapping:
            host_entry["data"]["snmp_port"] = snmp_mapping.connect_port
            host_entry["data"]["snmp_host"] = snmp_mapping.connect_address
        if d.snmp_profile and d.snmp_profile.v2_community:
            host_entry["data"]["snmp_community"] = d.snmp_profile.v2_community
            if use_gateway:
                host_entry["data"]["snmp_v2_community_gateway"] = f"{d.snmp_profile.v2_community}@{d.hostname}"
                host_entry["data"]["snmp_public_udp_available"] = not str(env.get("type", "")).startswith(
                    "cloud_railway"
                )
        if use_gateway:
            host_entry["data"]["snep_route_key"] = d.hostname

        hosts[d.hostname] = host_entry

    # Check if SSH is reachable and add warning if not
    reachable = env.get("ssh_reachable", True)

    result_data = {
        "hosts": hosts,
        "groups": {},
        "defaults": {
            "username": "admin",
            "password": "cisco123",
        },
    }
    if not reachable:
        result_data["_warning"] = env.get("note", "SSH/SNMP may not be reachable in this environment.")
        result_data["_run_locally"] = "Run SNEP locally with 'docker compose up' for SSH/SNMP access."
        # Provide local gateway-style inventory as alternative
        result_data["_local_gateway_inventory"] = {
            name: {
                "hostname": "127.0.0.1",
                "port": 2222,
                "username": f"{host['username'].split('%', 1)[0]}%{name}",
                "password": host["password"],
                "platform": host["platform"],
            }
            for name, host in hosts.items()
        }

    return result_data


@router.get("/ansible")
async def export_ansible(db: DBSession, connection_mode: str | None = None):
    """Export Ansible-compatible inventory."""
    env = detect_environment()
    use_gateway = connection_mode in {"gateway", "cloud_gateway"} or (
        connection_mode is None and is_cloud_gateway_mode(env)
    )

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
        gateway = build_ssh_gateway_info(
            d.hostname,
            credential_username=cred.username if cred else "admin",
            env=env,
            fallback_host=ssh_mapping.connect_address if ssh_mapping else "127.0.0.1",
        )

        # Map SNEP platform to Ansible network_os
        ansible_platform_map = {
            "cisco_ios": "cisco.ios.ios",
            "arista_eos": "arista.eos.eos",
            "juniper_junos": "junipernetworks.junos.junos",
        }

        hosts[d.hostname] = {
            "ansible_host": gateway["host"]
            if use_gateway
            else (ssh_mapping.connect_address if ssh_mapping else "127.0.0.1"),
            "ansible_port": gateway["port"] if use_gateway else (ssh_mapping.connect_port if ssh_mapping else 22),
            "ansible_user": gateway["username"] if use_gateway else (cred.username if cred else "admin"),
            "ansible_password": cred.password if cred else "admin",
            "ansible_network_os": ansible_platform_map.get(platform, platform),
            "ansible_connection": "ansible.netcommon.network_cli",
        }

    return {"all": {"hosts": hosts}}

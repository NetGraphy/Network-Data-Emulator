"""Initial schema — all SNEP tables.

Revision ID: 001
Revises: None
Create Date: 2026-03-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platforms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("vendor", sa.String(64), nullable=False),
        sa.Column("prompt_template", sa.String(256), nullable=False),
        sa.Column("error_template", sa.String(512), nullable=False),
        sa.Column("cli_modes", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("default_credentials", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "device_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("platform_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(256), nullable=False),
        sa.Column("software_version", sa.String(64), nullable=False),
        sa.Column("default_interface_pattern", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("hardware_details", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("platform_id", "name", name="uq_device_model_platform_name"),
    )

    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("device_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("device_models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hostname", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("management_ip", postgresql.INET, nullable=True),
        sa.Column("serial_number", sa.String(32), unique=True, nullable=False),
        sa.Column("software_version", sa.String(64), nullable=True),
        sa.Column("uptime_seconds", sa.BigInteger, nullable=False, server_default="7776000"),
        sa.Column("uptime_reference", sa.DateTime(timezone=True), nullable=False),
        sa.Column("admin_state", sa.String(20), nullable=False, server_default="active"),
        sa.Column("tags", postgresql.JSONB, nullable=True),
        sa.Column("emulation_config", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "device_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password", sa.String(128), nullable=False),
        sa.Column("enable_password", sa.String(128), nullable=True),
        sa.Column("privilege_level", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("device_id", "username", name="uq_credential_device_username"),
    )

    op.create_table(
        "interfaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("short_name", sa.String(64), nullable=False),
        sa.Column("if_index", sa.Integer, nullable=False),
        sa.Column("interface_type", sa.String(20), nullable=False, server_default="ethernet"),
        sa.Column("admin_status", sa.String(10), nullable=False, server_default="up"),
        sa.Column("oper_status", sa.String(20), nullable=False, server_default="up"),
        sa.Column("speed_mbps", sa.Integer, nullable=False, server_default="1000"),
        sa.Column("duplex", sa.String(10), nullable=True),
        sa.Column("mtu", sa.Integer, nullable=False, server_default="1500"),
        sa.Column("mac_address", sa.String(17), nullable=False),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("ipv6_address", postgresql.INET, nullable=True),
        sa.Column("description", sa.String(256), nullable=True),
        sa.Column("vlan_id", sa.Integer, nullable=True),
        sa.Column("is_trunk", sa.Boolean, nullable=True),
        sa.Column("allowed_vlans", sa.String(512), nullable=True),
        sa.Column("last_input", sa.String(32), nullable=True),
        sa.Column("last_output", sa.String(32), nullable=True),
        sa.Column("last_state_change", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("device_id", "name", name="uq_interface_device_name"),
        sa.UniqueConstraint("device_id", "if_index", name="uq_interface_device_ifindex"),
    )

    op.create_table(
        "interface_counters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("interface_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interfaces.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("in_octets", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("out_octets", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("in_unicast_pkts", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("out_unicast_pkts", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("in_multicast_pkts", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("out_multicast_pkts", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("in_broadcast_pkts", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("out_broadcast_pkts", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("in_errors", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("out_errors", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("in_discards", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("out_discards", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("crc_errors", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("collisions", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("rate_in_bps", sa.BigInteger, nullable=False, server_default="300000000"),
        sa.Column("rate_out_bps", sa.BigInteger, nullable=False, server_default="150000000"),
        sa.Column("rate_reference", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("interface_a_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interfaces.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("interface_b_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interfaces.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("link_type", sa.String(20), nullable=False, server_default="physical"),
        sa.Column("discovery_protocol", sa.String(10), nullable=False, server_default="cdp"),
        sa.Column("admin_state", sa.String(10), nullable=False, server_default="up"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("interface_a_id", "interface_b_id", name="uq_link_interface_pair"),
    )

    op.create_table(
        "snmp_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("v2_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("v2_community", sa.String(64), nullable=True),
        sa.Column("v3_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("v3_username", sa.String(64), nullable=True),
        sa.Column("v3_auth_protocol", sa.String(10), nullable=True),
        sa.Column("v3_auth_password", sa.String(128), nullable=True),
        sa.Column("v3_priv_protocol", sa.String(10), nullable=True),
        sa.Column("v3_priv_password", sa.String(128), nullable=True),
        sa.Column("v3_context", sa.String(64), nullable=True),
        sa.Column("sys_descr", sa.String(512), nullable=True),
        sa.Column("sys_contact", sa.String(256), nullable=True),
        sa.Column("sys_name", sa.String(256), nullable=True),
        sa.Column("sys_location", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "command_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("platform_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platforms.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("device_model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("device_models.id", ondelete="CASCADE"), nullable=True),
        sa.Column("command_pattern", sa.String(256), nullable=False),
        sa.Column("command_canonical", sa.String(256), nullable=False),
        sa.Column("template_body", sa.Text, nullable=False),
        sa.Column("required_state", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("output_type", sa.String(20), nullable=False, server_default="freeform"),
        sa.Column("platform_version_min", sa.String(32), nullable=True),
        sa.Column("platform_version_max", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("platform_id", "device_model_id", "command_canonical", name="uq_template_platform_model_cmd"),
    )

    op.create_table(
        "cli_output_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("command", sa.String(256), nullable=False),
        sa.Column("raw_output", sa.Text, nullable=False),
        sa.Column("mode", sa.String(10), nullable=False, server_default="static"),
        sa.Column("field_annotations", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("source_description", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("is_repeatable", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scenario_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("sequence_order", sa.Integer, nullable=False),
        sa.Column("trigger_type", sa.String(20), nullable=False),
        sa.Column("trigger_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("action_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("rollback_action", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "connection_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("protocol", sa.String(10), nullable=False),
        sa.Column("listen_address", sa.String(45), nullable=False),
        sa.Column("listen_port", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("protocol", "listen_address", "listen_port", name="uq_connection_mapping_endpoint"),
    )


def downgrade() -> None:
    op.drop_table("connection_mappings")
    op.drop_table("scenario_events")
    op.drop_table("scenarios")
    op.drop_table("cli_output_mappings")
    op.drop_table("command_templates")
    op.drop_table("snmp_profiles")
    op.drop_table("links")
    op.drop_table("interface_counters")
    op.drop_table("interfaces")
    op.drop_table("device_credentials")
    op.drop_table("devices")
    op.drop_table("device_models")
    op.drop_table("platforms")
